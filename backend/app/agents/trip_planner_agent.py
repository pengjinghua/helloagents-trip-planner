"""多智能体旅行规划系统"""

import asyncio
import json
import os
import re
import threading
from typing import Dict, Any, List
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
from ..services.llm_service import get_llm
from ..services.rag_service import get_rag_service
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel, RagReference
from ..config import get_settings


def _run_coro_safely(coro):
    """Run an async coroutine from sync code.

    If we're already inside an event loop (FastAPI async route), asyncio.run() will fail.
    In that case, execute the coroutine in a dedicated thread with its own loop.
    """

    try:
        asyncio.get_running_loop()
        has_running_loop = True
    except RuntimeError:
        has_running_loop = False

    if not has_running_loop:
        return asyncio.run(coro)

    result_container = {"result": None, "error": None}

    def _worker():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result_container["result"] = loop.run_until_complete(coro)
        except Exception as e:
            result_container["error"] = e
        finally:
            try:
                loop.close()
            except Exception:
                pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=20)

    if result_container["error"] is not None:
        raise result_container["error"]
    return result_container["result"]


def _extract_rag_rules(text: str, *, max_rules: int = 8) -> List[str]:
    """Extract actionable rule-like sentences from RAG text.

    This is a lightweight heuristic so users can *see* what the planner should follow.
    """

    t = (text or "").strip()
    if not t:
        return []

    keywords = (
        "预约",
        "开放",
        "闭馆",
        "门票",
        "身份证",
        "限流",
        "排队",
        "地铁",
        "公交",
        "换乘",
        "提前",
        "购票",
        "入场",
        "取票",
        "安检",
    )

    # Split into sentences/lines
    parts = re.split(r"[\n。！？!?]+", t)
    out: List[str] = []
    seen = set()
    for raw in parts:
        s = (raw or "").strip(" -•\t")
        if not s:
            continue
        if len(s) < 6:
            continue
        if not any(k in s for k in keywords):
            continue
        # Deduplicate by normalized content
        key = re.sub(r"\s+", " ", s)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
        if len(out) >= max(1, int(max_rules)):
            break
    return out


def _get_rag_context_and_references(request: TripRequest):
    """Retrieve RAG context and references for this request.

    Returns:
        (rag_context_str, rag_references_list)
    """

    rag_context = ""
    references: List[RagReference] = []
    rag_rules: List[str] = []

    try:
        rag = get_rag_service()

        # Default threshold tuned for typical embedding cosine ranges in this project.
        # City-matched travel docs often land around ~0.5-0.6; too high a default causes false "no hit".
        min_score = float(os.getenv("RAG_MIN_SCORE", "0.50"))
        strict_city_for_file = os.getenv("RAG_STRICT_CITY_FOR_FILE", "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }
        max_rules = int(os.getenv("RAG_RULES_MAX", "8"))

        q_parts = [request.city]
        if request.preferences:
            q_parts.append(" ".join(request.preferences))
        if request.free_text_input:
            q_parts.append(request.free_text_input)
        # Focus on common, actionable constraints (these are most likely to be present in user docs).
        q_parts.append("预约 开放时间 闭馆 门票 交通 路线 建议 注意事项")
        rag_query = " ".join([p for p in q_parts if p])

        results = _run_coro_safely(rag.search(query=rag_query, top_k=8))
        if results:
            city = (request.city or "").strip()
            by_source: Dict[int, Dict[str, Any]] = {}

            for score, chunk, source in results:
                # Filter by minimum semantic similarity.
                if float(score) < min_score:
                    continue

                # For file uploads, users usually expect city-specific docs to only apply to that city.
                if strict_city_for_file and city and source.source_type == "file":
                    hay = f"{source.title} {source.uri} {chunk.content}"
                    if city not in hay:
                        continue

                prev = by_source.get(source.id)
                if prev is None or float(score) > float(prev["score"]):
                    by_source[source.id] = {
                        "score": float(score),
                        "source": source,
                        "chunk": chunk,
                    }

            if by_source:
                lines: List[str] = []
                all_snippets: List[str] = []
                for _, item in sorted(by_source.items(), key=lambda kv: float(kv[1]["score"]), reverse=True):
                    score = float(item["score"])
                    source = item["source"]
                    chunk = item["chunk"]
                    snippet = chunk.content
                    if len(snippet) > 900:
                        snippet = snippet[:900] + "..."
                    all_snippets.append(chunk.content)
                    lines.append(
                        f"- 来源: {source.title} ({source.source_type}) | {source.uri} | score={score:.3f}\n  内容: {snippet}"
                    )
                    references.append(
                        RagReference(
                            title=source.title,
                            source_type=source.source_type,
                            uri=source.uri,
                            score=float(score),
                        )
                    )
                rag_context = "\n".join(lines)
                rag_rules = _extract_rag_rules("\n".join(all_snippets), max_rules=max_rules)
    except Exception:
        rag_context = ""
        references = []
        rag_rules = []

    return rag_context, references, rag_rules

# ============ Agent提示词 ============

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:**
你必须使用工具来搜索景点!不要自己编造景点信息!

**工具调用格式:**
使用maps_text_search工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_text_search:keywords=景点关键词,city=城市名]`

**示例:**
用户: "搜索北京的历史文化景点"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=历史文化,city=北京]

用户: "搜索上海的公园"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=公园,city=上海]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 参数用逗号分隔
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
你必须使用工具来查询天气!不要自己编造天气信息!

**工具调用格式:**
使用maps_weather工具时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_weather:city=城市名]`

**示例:**
用户: "查询北京天气"
你的回复: [TOOL_CALL:amap_maps_weather:city=北京]

用户: "上海的天气怎么样"
你的回复: [TOOL_CALL:amap_maps_weather:city=上海]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
你必须使用工具来搜索酒店!不要自己编造酒店信息!

**工具调用格式:**
使用maps_text_search工具搜索酒店时,必须严格按照以下格式:
`[TOOL_CALL:amap_maps_text_search:keywords=酒店,city=城市名]`

**示例:**
用户: "搜索北京的酒店"
你的回复: [TOOL_CALL:amap_maps_text_search:keywords=酒店,city=北京]

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 关键词使用"酒店"或"宾馆"
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
"""


class MultiAgentTripPlanner:
    """多智能体旅行规划系统"""

    def __init__(self):
        """初始化多智能体系统"""
        print("🔄 开始初始化多智能体旅行规划系统...")

        try:
            settings = get_settings()
            self.llm = get_llm()

            # 创建共享的MCP工具(只创建一次)
            print("  - 创建共享MCP工具...")
            self.amap_tool = MCPTool(
                name="amap",
                description="高德地图服务",
                server_command=["uvx", "amap-mcp-server"],
                env={"AMAP_MAPS_API_KEY": settings.amap_api_key},
                auto_expand=True
            )

            # 创建景点搜索Agent
            print("  - 创建景点搜索Agent...")
            self.attraction_agent = SimpleAgent(
                name="景点搜索专家",
                llm=self.llm,
                system_prompt=ATTRACTION_AGENT_PROMPT
            )
            self.attraction_agent.add_tool(self.amap_tool)

            # 创建天气查询Agent
            print("  - 创建天气查询Agent...")
            self.weather_agent = SimpleAgent(
                name="天气查询专家",
                llm=self.llm,
                system_prompt=WEATHER_AGENT_PROMPT
            )
            self.weather_agent.add_tool(self.amap_tool)

            # 创建酒店推荐Agent
            print("  - 创建酒店推荐Agent...")
            self.hotel_agent = SimpleAgent(
                name="酒店推荐专家",
                llm=self.llm,
                system_prompt=HOTEL_AGENT_PROMPT
            )
            self.hotel_agent.add_tool(self.amap_tool)

            # 创建行程规划Agent(不需要工具)
            print("  - 创建行程规划Agent...")
            self.planner_agent = SimpleAgent(
                name="行程规划专家",
                llm=self.llm,
                system_prompt=PLANNER_AGENT_PROMPT
            )

            print(f"✅ 多智能体系统初始化成功")
            print(f"   景点搜索Agent: {len(self.attraction_agent.list_tools())} 个工具")
            print(f"   天气查询Agent: {len(self.weather_agent.list_tools())} 个工具")
            print(f"   酒店推荐Agent: {len(self.hotel_agent.list_tools())} 个工具")

        except Exception as e:
            print(f"❌ 多智能体系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 步骤1: 并发执行独立检索任务(景点/天气/酒店)
            print("⚡ 步骤1: 并发检索景点/天气/酒店...")
            attraction_response, weather_response, hotel_response = self._run_independent_retrievals(request)
            print(f"景点搜索结果: {attraction_response[:200]}...\n")
            print(f"天气查询结果: {weather_response[:200]}...\n")
            print(f"酒店搜索结果: {hotel_response[:200]}...\n")

            # 步骤2: 行程规划Agent整合信息生成计划
            print("📋 步骤2: 生成行程计划...")
            rag_context, rag_references, rag_rules = _get_rag_context_and_references(request)
            planner_query = self._build_planner_query(
                request,
                attraction_response,
                weather_response,
                hotel_response,
                rag_context,
                rag_rules,
            )
            planner_response = self.planner_agent.run(planner_query)
            print(f"行程规划结果: {planner_response[:300]}...\n")

            # 解析最终计划
            trip_plan = self._parse_response(planner_response, request)

            # Always attach references if we found any.
            if rag_references:
                trip_plan = trip_plan.model_copy(update={"rag_references": rag_references})

            # Make RAG usage visible even if the LLM doesn't strictly follow instructions.
            if rag_rules:
                suffix_lines = ["", "RAG要点(自动提取):"] + [f"- {r}" for r in rag_rules]
                trip_plan = trip_plan.model_copy(
                    update={"overall_suggestions": (trip_plan.overall_suggestions or "").rstrip() + "\n" + "\n".join(suffix_lines).rstrip()}
                )

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    def _run_independent_retrievals(self, request: TripRequest) -> tuple[str, str, str]:
        """并发执行景点、天气、酒店检索。"""
        attraction_query = self._build_attraction_query(request)
        weather_query = f"请查询{request.city}的天气信息"
        hotel_query = f"请搜索{request.city}的{request.accommodation}酒店"

        async def _run_all():
            return await asyncio.gather(
                asyncio.to_thread(self.attraction_agent.run, attraction_query),
                asyncio.to_thread(self.weather_agent.run, weather_query),
                asyncio.to_thread(self.hotel_agent.run, hotel_query),
                return_exceptions=True,
            )

        attraction_result, weather_result, hotel_result = _run_coro_safely(_run_all())

        def _safe_text(result: Any, name: str) -> str:
            if isinstance(result, Exception):
                print(f"⚠️  {name}检索失败: {result}")
                return ""
            if result is None:
                return ""
            return str(result)

        return (
            _safe_text(attraction_result, "景点"),
            _safe_text(weather_result, "天气"),
            _safe_text(hotel_result, "酒店"),
        )
    
    def _build_attraction_query(self, request: TripRequest) -> str:
        """构建景点搜索查询 - 直接包含工具调用"""
        keywords = []
        if request.preferences:
            # 只取第一个偏好作为关键词
            keywords = request.preferences[0]
        else:
            keywords = "景点"

        # 直接返回工具调用格式
        query = f"请使用amap_maps_text_search工具搜索{request.city}的{keywords}相关景点。\n[TOOL_CALL:amap_maps_text_search:keywords={keywords},city={request.city}]"
        return query

    def _build_planner_query(
        self,
        request: TripRequest,
        attractions: str,
        weather: str,
        hotels: str = "",
        rag_context: str = "",
        rag_rules: List[str] | None = None,
    ) -> str:
        """构建行程规划查询"""
        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**用户提供的知识库参考(RAG):**
{rag_context if rag_context else '（无）'}

**RAG中提取的硬性规则(若存在，必须遵守):**
{('- ' + '\n- '.join(rag_rules)) if rag_rules else '（无）'}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
3. 考虑景点之间的距离和交通方式
4. 返回完整的JSON格式数据
5. 景点的经纬度坐标要真实准确
6. 若RAG参考中包含明确的规则/开放时间/预约方式/路线建议，请优先采纳并在overall_suggestions中体现；若RAG参考非空，请在overall_suggestions末尾追加“参考来源：<来源标题1>; <来源标题2> ...”
"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query
    
    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应
        
        Args:
            response: Agent响应文本
            request: 原始请求
            
        Returns:
            旅行计划
        """
        try:
            # 尝试从响应中提取JSON
            # 查找JSON代码块
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                # 直接查找JSON对象
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 转换为TripPlan对象
            trip_plan = TripPlan(**data)
            
            return trip_plan
            
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)
    
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        from datetime import datetime, timedelta
        
        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        
        # 创建每日行程
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)
        
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )


# 全局多智能体系统实例
_multi_agent_planner = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)"""
    global _multi_agent_planner

    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()

    return _multi_agent_planner

