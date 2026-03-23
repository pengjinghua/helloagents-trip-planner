"""Generate a larger photo evaluation dataset.

Default output: 1000 samples (built from curated seed POIs with unique IDs).
Usage:
  python backend/scripts/generate_photo_eval_dataset.py --count 1000 --out backend/scripts/data/photo_eval_samples_1000.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any


SEED_POIS: List[Dict[str, Any]] = [
    {"name": "故宫", "city": "北京", "category": "历史文化", "judge_tokens": ["forbidden city", "palace museum", "故宫", "紫禁城"]},
    {"name": "天坛", "city": "北京", "category": "历史文化", "judge_tokens": ["temple of heaven", "天坛"]},
    {"name": "颐和园", "city": "北京", "category": "历史文化", "judge_tokens": ["summer palace", "颐和园"]},
    {"name": "八达岭长城", "city": "北京", "category": "历史文化", "judge_tokens": ["great wall", "badaling", "长城"]},
    {"name": "外滩", "city": "上海", "category": "城市风光", "judge_tokens": ["the bund", "waitan", "外滩"]},
    {"name": "东方明珠", "city": "上海", "category": "城市风光", "judge_tokens": ["oriental pearl", "东方明珠"]},
    {"name": "迪士尼乐园", "city": "上海", "category": "休闲", "judge_tokens": ["disney", "disneyland", "迪士尼"]},
    {"name": "广州塔", "city": "广州", "category": "城市风光", "judge_tokens": ["canton tower", "guangzhou tower", "广州塔"]},
    {"name": "陈家祠", "city": "广州", "category": "历史文化", "judge_tokens": ["chen clan", "chen clan academy", "陈家祠"]},
    {"name": "珠江夜游", "city": "广州", "category": "城市风光", "judge_tokens": ["pearl river", "珠江"]},
    {"name": "世界之窗", "city": "深圳", "category": "休闲", "judge_tokens": ["window of the world", "世界之窗"]},
    {"name": "深圳湾公园", "city": "深圳", "category": "自然风光", "judge_tokens": ["shenzhen bay", "深圳湾"]},
    {"name": "锦里", "city": "成都", "category": "历史文化", "judge_tokens": ["jinli", "锦里"]},
    {"name": "宽窄巷子", "city": "成都", "category": "历史文化", "judge_tokens": ["kuanzhai alley", "宽窄巷子"]},
    {"name": "成都大熊猫繁育研究基地", "city": "成都", "category": "自然风光", "judge_tokens": ["panda", "chengdu research base", "熊猫"]},
    {"name": "西湖", "city": "杭州", "category": "自然风光", "judge_tokens": ["west lake", "西湖"]},
    {"name": "灵隐寺", "city": "杭州", "category": "历史文化", "judge_tokens": ["lingyin", "lingyin temple", "灵隐寺"]},
    {"name": "夫子庙", "city": "南京", "category": "历史文化", "judge_tokens": ["confucius temple", "夫子庙"]},
    {"name": "中山陵", "city": "南京", "category": "历史文化", "judge_tokens": ["sun yat-sen mausoleum", "中山陵"]},
    {"name": "拙政园", "city": "苏州", "category": "历史文化", "judge_tokens": ["humble administrator's garden", "拙政园"]},
    {"name": "平江路", "city": "苏州", "category": "历史文化", "judge_tokens": ["pingjiang road", "平江路"]},
    {"name": "黄鹤楼", "city": "武汉", "category": "历史文化", "judge_tokens": ["yellow crane tower", "黄鹤楼"]},
    {"name": "东湖", "city": "武汉", "category": "自然风光", "judge_tokens": ["east lake", "donghu", "东湖"]},
    {"name": "兵马俑", "city": "西安", "category": "历史文化", "judge_tokens": ["terracotta", "terracotta army", "兵马俑"]},
    {"name": "大雁塔", "city": "西安", "category": "历史文化", "judge_tokens": ["giant wild goose pagoda", "大雁塔"]},
]


def build_dataset(count: int) -> List[Dict[str, Any]]:
    if count <= 0:
        return []

    out: List[Dict[str, Any]] = []
    seed_len = len(SEED_POIS)
    for i in range(count):
        seed = SEED_POIS[i % seed_len]
        out.append(
            {
                "id": f"{seed['city']}-{seed['name']}-{i+1:04d}",
                "name": seed["name"],
                "city": seed["city"],
                "category": seed["category"],
                "judge_tokens": list(seed["judge_tokens"]),
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate photo eval dataset")
    parser.add_argument("--count", type=int, default=1000, help="Number of samples to generate")
    parser.add_argument(
        "--out",
        type=str,
        default="backend/scripts/data/photo_eval_samples_1000.json",
        help="Output JSON file path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = build_dataset(args.count)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(dataset)} samples -> {out_path}")


if __name__ == "__main__":
    main()
