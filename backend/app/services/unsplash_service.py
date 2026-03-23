"""Unsplash图片服务"""

import os
import re
import requests
from typing import Dict, List, Optional, Tuple
from ..config import get_settings

class UnsplashService:
    """Unsplash图片服务类"""
    
    def __init__(self):
        """初始化服务"""
        settings = get_settings()
        self.access_key = settings.unsplash_access_key
        self.base_url = "https://api.unsplash.com"
    
    def search_photos(self, query: str, per_page: int = 5) -> List[dict]:
        """
        搜索图片
        
        Args:
            query: 搜索关键词
            per_page: 每页数量
            
        Returns:
            图片列表
        """
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "order_by": "relevant",
                "content_filter": "high",
                "orientation": "landscape",
                "client_id": self.access_key,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            # 提取图片URL
            photos = []
            for photo in results:
                photos.append({
                    "id": photo.get("id"),
                    "url": photo.get("urls", {}).get("regular"),
                    "thumb": photo.get("urls", {}).get("thumb"),
                    "description": photo.get("description") or photo.get("alt_description"),
                    "photographer": photo.get("user", {}).get("name")
                })
            
            return photos
            
        except Exception as e:
            print(f"❌ Unsplash搜索失败: {str(e)}")
            return []
    
    def get_photo_url(self, query: str) -> Optional[str]:
        """
        获取单张图片URL

        Args:
            query: 搜索关键词

        Returns:
            图片URL
        """
        photos = self.search_photos(query, per_page=1)
        if photos:
            return photos[0].get("url")
        return None

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", (text or "").lower())

    def _is_ascii_text(self, text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        return all(ord(ch) < 128 for ch in t)

    def _infer_english_hint(self, name: str) -> List[str]:
        n = (name or "").strip()
        if not n:
            return []

        # Small, high-value mapping for common China POIs.
        mapping: Dict[str, str] = {
            "故宫": "Forbidden City",
            "紫禁城": "Forbidden City",
            "天安门": "Tiananmen",
            "天坛": "Temple of Heaven",
            "颐和园": "Summer Palace",
            "长城": "Great Wall",
            "八达岭": "Badaling Great Wall",
            "慕田峪": "Mutianyu Great Wall",
            "南锣鼓巷": "Nanluoguxiang",
            "什刹海": "Shichahai",
            "鸟巢": "Bird's Nest stadium",
            "水立方": "Water Cube",
            "国博": "National Museum of China",
            "国家博物馆": "National Museum of China",
            "798": "798 Art District",
            "雍和宫": "Lama Temple",
            "兵马俑": "Terracotta Army",
            "秦始皇兵马俑": "Terracotta Army",
            "大雁塔": "Giant Wild Goose Pagoda",
            "成都大熊猫繁育研究基地": "Chengdu Research Base of Giant Panda Breeding",
            "成都熊猫基地": "Chengdu Panda Base",
            "熊猫基地": "Panda Base",
        }

        for k, v in mapping.items():
            if k in n:
                return [v]

        # Generic hints by suffix/keywords
        hints: List[str] = []
        if "博物馆" in n:
            hints.append("museum")
        if "寺" in n or "庙" in n or "宫" in n:
            hints.append("temple")
        if "公园" in n:
            hints.append("park")
        if "长城" in n:
            hints.append("great wall")
        if "老街" in n or "古街" in n or "步行街" in n:
            hints.append("street")
        if "湖" in n:
            hints.append("lake")
        if "山" in n:
            hints.append("mountain")
        if "塔" in n:
            hints.append("pagoda")
        if "广场" in n:
            hints.append("square")
        if "熊猫" in n:
            hints.append("panda")
        return hints

    def _infer_category_en(self, category: str) -> str:
        c = (category or "").strip()
        if not c:
            return ""
        mapping = {
            "历史文化": "historic landmark",
            "自然风光": "nature",
            "美食": "food",
            "购物": "shopping",
            "艺术": "art",
            "休闲": "leisure",
            "城市风光": "cityscape",
            "景点": "landmark",
        }
        if c in mapping:
            return mapping[c]
        # If user passes English category, keep it.
        return c if self._is_ascii_text(c) else ""

    def _infer_city_en(self, city: str) -> str:
        c = (city or "").strip()
        mapping = {
            "北京": "Beijing",
            "上海": "Shanghai",
            "广州": "Guangzhou",
            "深圳": "Shenzhen",
            "成都": "Chengdu",
            "杭州": "Hangzhou",
            "南京": "Nanjing",
            "苏州": "Suzhou",
            "武汉": "Wuhan",
            "西安": "Xi'an",
            "重庆": "Chongqing",
            "厦门": "Xiamen",
            "青岛": "Qingdao",
            "昆明": "Kunming",
            "拉萨": "Lhasa",
            "南昌": "Nanchang",
        }
        return mapping.get(c, c)

    def get_best_photo_url(
        self,
        *,
        name: str,
        city: str = "",
        category: str = "",
    ) -> Tuple[Optional[str], str]:
        """Pick a photo URL with basic relevance checking.

        Returns: (photo_url, used_query)
        """

        name = (name or "").strip()
        city = (city or "").strip()
        category = (category or "").strip()

        if not name:
            return None, ""

        min_rel = float(os.getenv("UNSPLASH_MIN_RELEVANCE", "0.15"))
        max_query_candidates = int(os.getenv("UNSPLASH_MAX_QUERY_CANDIDATES", "8"))
        single_query_mode = max_query_candidates <= 1
        enable_category_fallback = os.getenv("UNSPLASH_ENABLE_CATEGORY_FALLBACK", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

        city_en = self._infer_city_en(city)
        hints = self._infer_english_hint(name)
        category_en = self._infer_category_en(category)

        queries: List[str] = []
        if single_query_mode:
            # Quota-friendly mode: only 1 query candidate.
            # Use a hybrid query to maximize recall in one shot.
            if hints and city and city_en and city_en != city:
                queries.append(f"{hints[0]} {name} {city} {city_en} China")
            elif hints and city_en:
                queries.append(f"{hints[0]} {name} {city_en}")
            elif city:
                queries.append(f"{name} {city}")
            else:
                queries.append(name)

        # Highest priority: exact name + city (Chinese/English)
        if city:
            queries.append(f"{name} {city}")
        if city_en and city_en != city:
            queries.append(f"{name} {city_en}")
            queries.append(f"{name} {city_en} China")

        # Name-centered hint queries
        if hints and city_en:
            queries.append(f"{hints[0]} {city_en} China")
        if hints:
            queries.append(hints[0])

        if city and city_en and city_en != city:
            if hints:
                queries.append(f"{' '.join(hints)} {city_en} China")
                queries.append(f"{' '.join(hints)} {city_en} landmark")
                queries.append(f"{name} {city_en} China")
            else:
                queries.append(f"{name} {city_en} China landmark")

        # Generic fallback if nothing else works (kept last; may still be wrong)
        if hints and city_en:
            queries.append(f"{' '.join(hints)} {city_en}")
        if enable_category_fallback and category_en and city_en:
            queries.append(f"{category_en} {city_en}")

        # De-dup while preserving order
        seen = set()
        qlist: List[str] = []
        for q in queries:
            q = re.sub(r"\s+", " ", q).strip()
            if not q or q in seen:
                continue
            seen.add(q)
            qlist.append(q)

        best_url: Optional[str] = None
        best_query = ""
        best_score = -1.0
        effective_min_rel = min_rel if not single_query_mode else min(min_rel, 0.08)

        for q in qlist[: max(1, max_query_candidates)]:
            photos = self.search_photos(q, per_page=10)
            if not photos:
                continue
            q_tokens = set(self._tokenize(q))
            name_tokens = set(self._tokenize(name))

            for p in photos:
                desc = (p.get("description") or "")
                d_tokens = set(self._tokenize(desc))
                if not d_tokens:
                    continue
                overlap = len(q_tokens & d_tokens)
                rel = overlap / max(1, len(q_tokens))

                # Prefer candidates that hit core landmark hints (e.g. "terracotta", "panda").
                hint_bonus = 0.0
                for h in hints[:2]:
                    h_tokens = set(self._tokenize(h))
                    if h_tokens and len(h_tokens & d_tokens) > 0:
                        hint_bonus += 0.10

                # Small boost if city token also appears in description.
                city_bonus = 0.0
                city_tokens = set(self._tokenize(city_en))
                if city_tokens and len(city_tokens & d_tokens) > 0:
                    city_bonus = 0.05

                # Prefer candidates that mention landmark name tokens.
                name_bonus = 0.0
                if name_tokens and len(name_tokens & d_tokens) > 0:
                    name_bonus += 0.10
                if name_tokens and name_tokens.issubset(d_tokens):
                    name_bonus += 0.05

                rel = min(1.0, rel + hint_bonus + city_bonus + name_bonus)
                if rel > best_score and p.get("url"):
                    best_score = rel
                    best_url = p.get("url")
                    best_query = q

        if best_url and best_score >= effective_min_rel:
            return best_url, best_query

        # Safe fallback: if heuristic confidence is low, return top1 from raw query
        # to avoid excessive zero-recall under quota constraints.
        fallback_queries: List[str] = []
        if city:
            fallback_queries.append(f"{name} {city}")
        fallback_queries.append(name)
        if city_en and city_en != city:
            fallback_queries.append(f"{name} {city_en}")

        seen_fb = set()
        for fq in fallback_queries:
            fq = re.sub(r"\s+", " ", (fq or "")).strip()
            if not fq or fq in seen_fb:
                continue
            seen_fb.add(fq)
            photos = self.search_photos(fq, per_page=1)
            if photos and photos[0].get("url"):
                return photos[0].get("url"), fq

        return None, best_query


# 全局服务实例
_unsplash_service = None


def get_unsplash_service() -> UnsplashService:
    """获取Unsplash服务实例(单例模式)"""
    global _unsplash_service
    
    if _unsplash_service is None:
        _unsplash_service = UnsplashService()
    
    return _unsplash_service

