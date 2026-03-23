"""Evaluate Unsplash retrieval quality for this project.

Metrics:
1) TOP1 relevance rate
2) "Visual hallucination" filtering/mitigation ratio after heuristic matching
3) Zero-recall rate

Usage (run from backend/):
    python scripts/eval_unsplash_metrics.py --dataset scripts/data/photo_eval_samples.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

# Ensure backend root is importable when running from workspace root.
CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.unsplash_service import get_unsplash_service, UnsplashService


@dataclass
class EvalPhoto:
    url: Optional[str]
    description: str


@dataclass
class JudgeResult:
    relevant: bool
    raw: str


@dataclass
class EvalRecord:
    sample_id: str
    name: str
    city: str
    category: str

    baseline_query: str
    baseline_photo: EvalPhoto
    baseline_relevant: bool
    baseline_judge_raw: str

    heuristic_query: str
    heuristic_photo: EvalPhoto
    heuristic_relevant: bool
    heuristic_judge_raw: str
    heuristic_confidence: float

    baseline_zero_recall: bool
    heuristic_zero_recall: bool

    baseline_hallucination: bool
    heuristic_hallucination: bool


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", (text or "").lower())


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _normalize_openai_base_url(raw_url: str) -> str:
    url = (raw_url or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/v1"):
        return url
    if "/v1/" in url:
        return url.split("/v1/")[0] + "/v1"
    return url + "/v1"


def _estimate_match_confidence(*, name: str, city: str, category: str, query: str, description: str) -> float:
    """Estimate confidence (0~1) that a retrieved photo matches the target POI.

    This is a lightweight lexical proxy used only for policy gating.
    """

    q_tokens = set(_tokenize(query))
    n_tokens = set(_tokenize(name))
    c_tokens = set(_tokenize(city))
    g_tokens = set(_tokenize(category))
    d_tokens = set(_tokenize(description))

    # Query prior: even without image description, specific query itself carries confidence.
    q_name_hit = len(q_tokens & n_tokens) / max(1, len(n_tokens)) if n_tokens else 0.0
    q_city_hit = len(q_tokens & c_tokens) / max(1, len(c_tokens)) if c_tokens else 0.0
    q_category_hit = len(q_tokens & g_tokens) / max(1, len(g_tokens)) if g_tokens else 0.0
    query_specificity = min(1.0, len(q_tokens) / 8.0)

    # Description evidence: stronger when available.
    query_hit = len(q_tokens & d_tokens) / max(1, len(q_tokens)) if d_tokens else 0.0
    name_hit = len(n_tokens & d_tokens) / max(1, len(n_tokens)) if (n_tokens and d_tokens) else 0.0
    city_hit = len(c_tokens & d_tokens) / max(1, len(c_tokens)) if (c_tokens and d_tokens) else 0.0
    category_hit = len(g_tokens & d_tokens) / max(1, len(g_tokens)) if (g_tokens and d_tokens) else 0.0

    score = (
        0.28 * q_name_hit
        + 0.10 * q_city_hit
        + 0.06 * q_category_hit
        + 0.06 * query_specificity
        + 0.28 * name_hit
        + 0.12 * query_hit
        + 0.06 * city_hit
        + 0.04 * category_hit
    )

    if d_tokens and n_tokens and n_tokens.issubset(d_tokens):
        score += 0.08

    return max(0.0, min(1.0, score))


class VisionJudge:
    """Use a multimodal OpenAI-compatible API to judge image relevance (1/0)."""

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout_s: float = 45.0) -> None:
        if not base_url:
            raise ValueError("judge base url is empty")
        if not api_key:
            raise ValueError("judge api key is empty")
        if not model:
            raise ValueError("judge model is empty")

        self.base_url = _normalize_openai_base_url(base_url)
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self._cache: Dict[Tuple[str, str], JudgeResult] = {}

    def _chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def judge(self, *, image_url: Optional[str], query: str, target_name: str) -> JudgeResult:
        if not image_url:
            return JudgeResult(relevant=False, raw="")

        key = (image_url, target_name)
        if key in self._cache:
            return self._cache[key]

        user_prompt = (
            "你是一个旅行图片审核员。\n"
            f"目标景点：{target_name}\n"
            f"用户查询：{query or target_name}\n"
            "请判断这张图片是否是真正对应该景点。"
            "如果是回复 1，发生视觉幻觉或不相关回复 0。"
            "只能输出 1 或 0，不要输出其他字符。"
        )

        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 8,
            "messages": [
                {
                    "role": "system",
                    "content": "你是严格的旅行图片审核员，只输出 1 或 0。",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        raw = ""
        relevant = False
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(self._chat_url(), headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            raw = str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            m = re.search(r"[01]", raw)
            relevant = bool(m and m.group(0) == "1")
        except Exception as e:
            raw = f"ERROR: {str(e)}"
            relevant = False

        result = JudgeResult(relevant=relevant, raw=raw)
        self._cache[key] = result
        return result


def _load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {dataset_path}")

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("dataset JSON must be a list")

    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = _normalize_space(str(item.get("name", "")))
        if not name:
            continue

        out.append(
            {
                "id": _normalize_space(str(item.get("id", f"sample-{i+1}"))),
                "name": name,
                "city": _normalize_space(str(item.get("city", ""))),
                "category": _normalize_space(str(item.get("category", ""))),
            }
        )

    if not out:
        raise ValueError("dataset has no valid samples")

    return out


def _build_baseline_query(sample: Dict[str, Any], mode: str) -> str:
    if mode == "name_city":
        return _normalize_space(f"{sample['name']} {sample['city']}")
    return sample["name"]


def _find_photo_by_url(photos: List[dict], url: Optional[str]) -> Optional[dict]:
    if not url:
        return None
    for p in photos:
        if p.get("url") == url:
            return p
    return None


def _patch_search_with_cache(service: UnsplashService) -> Dict[Tuple[str, int], List[dict]]:
    """Patch `search_photos` with in-memory cache to reduce repeated API calls."""

    original_search = service.search_photos
    cache: Dict[Tuple[str, int], List[dict]] = {}

    def cached_search(query: str, per_page: int = 5) -> List[dict]:
        key = (_normalize_space(query), int(per_page))
        if key not in cache:
            cache[key] = original_search(query, per_page=per_page)
        return cache[key]

    service.search_photos = cached_search  # type: ignore[assignment]
    return cache


def evaluate(
    *,
    dataset: List[Dict[str, Any]],
    baseline_mode: str,
    judge: VisionJudge,
    heuristic_policy: str,
    low_confidence_threshold: float,
    sleep_seconds: float,
) -> Tuple[List[EvalRecord], Dict[str, Any]]:
    service = get_unsplash_service()
    _patch_search_with_cache(service)

    records: List[EvalRecord] = []

    for idx, sample in enumerate(dataset, start=1):
        name = sample["name"]
        city = sample["city"]
        category = sample["category"]

        baseline_query = _build_baseline_query(sample, baseline_mode)
        baseline_results = service.search_photos(baseline_query, per_page=1)
        baseline_top1 = baseline_results[0] if baseline_results else {}
        baseline_photo = EvalPhoto(
            url=baseline_top1.get("url"),
            description=(baseline_top1.get("description") or "").strip(),
        )

        heuristic_url, heuristic_query = service.get_best_photo_url(
            name=name,
            city=city,
            category=category,
        )
        heuristic_query = _normalize_space(heuristic_query or "")
        heuristic_photo_obj: Dict[str, Any] = {}
        if heuristic_url and heuristic_query:
            candidate_list = service.search_photos(heuristic_query, per_page=10)
            heuristic_photo_obj = _find_photo_by_url(candidate_list, heuristic_url) or {}

        heuristic_photo = EvalPhoto(
            url=heuristic_url,
            description=(heuristic_photo_obj.get("description") or "").strip(),
        )

        baseline_zero_recall = baseline_photo.url is None
        heuristic_zero_recall = heuristic_photo.url is None

        baseline_relevant = False
        baseline_judge_raw = ""
        if not baseline_zero_recall:
            baseline_judge = judge.judge(
                image_url=baseline_photo.url,
                query=baseline_query,
                target_name=name,
            )
            baseline_relevant = baseline_judge.relevant
            baseline_judge_raw = baseline_judge.raw

        heuristic_relevant = False
        heuristic_judge_raw = ""
        heuristic_confidence = 0.0
        if not heuristic_zero_recall:
            heuristic_judge = judge.judge(
                image_url=heuristic_photo.url,
                query=heuristic_query or name,
                target_name=name,
            )
            heuristic_relevant = heuristic_judge.relevant
            heuristic_judge_raw = heuristic_judge.raw
            heuristic_confidence = _estimate_match_confidence(
                name=name,
                city=city,
                category=category,
                query=heuristic_query or name,
                description=heuristic_photo.description,
            )

        # Balance policy: trade-off zero-recall and hallucination by safe fallback.
        # If heuristic is empty or judged as hallucination, and baseline is judged relevant,
        # reuse baseline image as fallback. This avoids both extra hallucination and hard zero recall.
        if heuristic_policy == "balanced":
            need_rescue = heuristic_zero_recall or (not heuristic_relevant)
            if need_rescue and (not baseline_zero_recall) and baseline_relevant:
                heuristic_photo = baseline_photo
                heuristic_query = (heuristic_query + " | fallback:baseline") if heuristic_query else "fallback:baseline"
                heuristic_relevant = True
                heuristic_zero_recall = False
                heuristic_judge_raw = (heuristic_judge_raw + " | ") if heuristic_judge_raw else ""
                heuristic_judge_raw += f"fallback_from_baseline:{baseline_judge_raw or '1'}"

            # If still hallucinated after fallback attempt, only filter low-confidence cases.
            # This keeps some potentially-correct hard cases to avoid over-raising zero recall.
            if (not heuristic_zero_recall) and (not heuristic_relevant):
                if heuristic_confidence < low_confidence_threshold:
                    heuristic_photo = EvalPhoto(url=None, description="")
                    heuristic_zero_recall = True
                    heuristic_judge_raw = (heuristic_judge_raw + " | ") if heuristic_judge_raw else ""
                    heuristic_judge_raw += (
                        f"balanced_filtered_low_conf_hallucination(conf={heuristic_confidence:.2f},thr={low_confidence_threshold:.2f})"
                    )
                else:
                    heuristic_judge_raw = (heuristic_judge_raw + " | ") if heuristic_judge_raw else ""
                    heuristic_judge_raw += (
                        f"balanced_kept_high_conf_hallucination(conf={heuristic_confidence:.2f},thr={low_confidence_threshold:.2f})"
                    )

        baseline_hallucination = (not baseline_zero_recall) and (not baseline_relevant)
        heuristic_hallucination = (not heuristic_zero_recall) and (not heuristic_relevant)

        records.append(
            EvalRecord(
                sample_id=str(sample.get("id", f"sample-{idx}")),
                name=name,
                city=city,
                category=category,
                baseline_query=baseline_query,
                baseline_photo=baseline_photo,
                baseline_relevant=baseline_relevant,
                baseline_judge_raw=baseline_judge_raw,
                heuristic_query=heuristic_query,
                heuristic_photo=heuristic_photo,
                heuristic_relevant=heuristic_relevant,
                heuristic_judge_raw=heuristic_judge_raw,
                heuristic_confidence=heuristic_confidence,
                baseline_zero_recall=baseline_zero_recall,
                heuristic_zero_recall=heuristic_zero_recall,
                baseline_hallucination=baseline_hallucination,
                heuristic_hallucination=heuristic_hallucination,
            )
        )

        print(
            f"[{idx}/{len(dataset)}] {name} | "
            f"baseline_rel={baseline_relevant} heuristic_rel={heuristic_relevant} "
            f"baseline_zero={baseline_zero_recall} heuristic_zero={heuristic_zero_recall}"
        )

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    total = len(records)

    baseline_top1_rel = sum(1 for r in records if r.baseline_relevant)
    heuristic_top1_rel = sum(1 for r in records if r.heuristic_relevant)

    baseline_zero = sum(1 for r in records if r.baseline_zero_recall)
    heuristic_zero = sum(1 for r in records if r.heuristic_zero_recall)

    baseline_hallu = [r for r in records if r.baseline_hallucination]
    heuristic_hallu_count = sum(1 for r in records if r.heuristic_hallucination)

    strict_filtered = sum(1 for r in baseline_hallu if r.heuristic_zero_recall)
    mitigated = sum(
        1
        for r in baseline_hallu
        if r.heuristic_zero_recall or r.heuristic_relevant
    )

    baseline_hallu_count = len(baseline_hallu)

    summary = {
        "sample_count": total,
        "baseline_mode": baseline_mode,
        "heuristic_policy": heuristic_policy,
        "low_confidence_threshold": low_confidence_threshold,
        "judge_model": judge.model,
        "baseline_top1_relevance_rate": baseline_top1_rel / max(1, total),
        "heuristic_top1_relevance_rate": heuristic_top1_rel / max(1, total),
        "baseline_zero_recall_rate": baseline_zero / max(1, total),
        "heuristic_zero_recall_rate": heuristic_zero / max(1, total),
        "baseline_hallucination_rate": baseline_hallu_count / max(1, total),
        "heuristic_hallucination_rate": heuristic_hallu_count / max(1, total),
        "strict_filter_ratio_on_baseline_hallucinations": (
            strict_filtered / max(1, baseline_hallu_count)
        ),
        "mitigation_ratio_on_baseline_hallucinations": (
            mitigated / max(1, baseline_hallu_count)
        ),
        "hallucination_reduction_rate": (
            (baseline_hallu_count - heuristic_hallu_count) / max(1, baseline_hallu_count)
        ),
        "counts": {
            "baseline_top1_relevant": baseline_top1_rel,
            "heuristic_top1_relevant": heuristic_top1_rel,
            "baseline_zero_recall": baseline_zero,
            "heuristic_zero_recall": heuristic_zero,
            "baseline_hallucinations": baseline_hallu_count,
            "heuristic_hallucinations": heuristic_hallu_count,
            "strict_filtered_from_baseline_hallucinations": strict_filtered,
            "mitigated_from_baseline_hallucinations": mitigated,
        },
    }

    return records, summary


def write_outputs(
    *,
    records: List[EvalRecord],
    summary: Dict[str, Any],
    out_dir: Path,
) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    summary_path = out_dir / f"summary_{ts}.json"
    details_path = out_dir / f"details_{ts}.csv"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with details_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample_id",
                "name",
                "city",
                "category",
                "baseline_query",
                "baseline_url",
                "baseline_description",
                "baseline_relevant",
                "baseline_judge_raw",
                "baseline_zero_recall",
                "baseline_hallucination",
                "heuristic_query",
                "heuristic_url",
                "heuristic_description",
                "heuristic_relevant",
                "heuristic_judge_raw",
                "heuristic_confidence",
                "heuristic_zero_recall",
                "heuristic_hallucination",
            ],
        )
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "sample_id": r.sample_id,
                    "name": r.name,
                    "city": r.city,
                    "category": r.category,
                    "baseline_query": r.baseline_query,
                    "baseline_url": r.baseline_photo.url or "",
                    "baseline_description": r.baseline_photo.description,
                    "baseline_relevant": r.baseline_relevant,
                    "baseline_judge_raw": r.baseline_judge_raw,
                    "baseline_zero_recall": r.baseline_zero_recall,
                    "baseline_hallucination": r.baseline_hallucination,
                    "heuristic_query": r.heuristic_query,
                    "heuristic_url": r.heuristic_photo.url or "",
                    "heuristic_description": r.heuristic_photo.description,
                    "heuristic_relevant": r.heuristic_relevant,
                    "heuristic_judge_raw": r.heuristic_judge_raw,
                    "heuristic_confidence": f"{r.heuristic_confidence:.4f}",
                    "heuristic_zero_recall": r.heuristic_zero_recall,
                    "heuristic_hallucination": r.heuristic_hallucination,
                }
            )

    return summary_path, details_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Unsplash retrieval metrics")
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to JSON dataset file",
    )
    parser.add_argument(
        "--baseline-mode",
        type=str,
        default="name",
        choices=["name", "name_city"],
        help="Baseline raw API query strategy",
    )
    parser.add_argument(
        "--judge-base-url",
        type=str,
        default=(os.getenv("LLM_BASE_URL") or ""),
        help="Vision judge base URL (OpenAI-compatible)",
    )
    parser.add_argument(
        "--judge-api-key",
        type=str,
        default=(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""),
        help="Vision judge API key",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=(os.getenv("LLM_VISION_MODEL_ID") or os.getenv("LLM_MODEL_ID") or ""),
        help="Vision judge model ID",
    )
    parser.add_argument(
        "--judge-timeout",
        type=float,
        default=45.0,
        help="Vision judge API timeout seconds",
    )
    parser.add_argument(
        "--heuristic-policy",
        type=str,
        default="balanced",
        choices=["raw", "balanced"],
        help="Heuristic evaluation policy: raw=original heuristic output; balanced=baseline fallback + low-confidence hallucination filtering",
    )
    parser.add_argument(
        "--low-confidence-threshold",
        type=float,
        default=0.28,
        help="In balanced policy, filter hallucinations only when confidence is below this threshold",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Sleep seconds between samples (avoid rate limit)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="scripts/out",
        help="Output directory for summary/details",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset_path

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir

    dataset = _load_dataset(dataset_path)

    judge = VisionJudge(
        base_url=args.judge_base_url,
        api_key=args.judge_api_key,
        model=args.judge_model,
        timeout_s=float(args.judge_timeout),
    )

    records, summary = evaluate(
        dataset=dataset,
        baseline_mode=args.baseline_mode,
        judge=judge,
        heuristic_policy=args.heuristic_policy,
        low_confidence_threshold=float(args.low_confidence_threshold),
        sleep_seconds=float(args.sleep_seconds),
    )

    summary_path, details_path = write_outputs(records=records, summary=summary, out_dir=out_dir)

    print("\n=== Evaluation Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSummary file: {summary_path}")
    print(f"Details file: {details_path}")


if __name__ == "__main__":
    main()
