"""Evaluate RAG uplift (Chroma) on a small Chinese benchmark.

Metrics:
1) Top1 accuracy
2) Recall@3
3) MRR@3

Baseline: title-only lexical retrieval (simulates no-RAG/weak retrieval).
RAG: Chroma vector retrieval via `RagService.search()`.

Usage (run from repo root or backend/):
    python backend/scripts/eval_rag_chroma_metrics.py \
      --dataset backend/scripts/data/rag_eval_samples_cn_30.json \
      --out-dir backend/scripts/out
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.rag_service import RagService


@dataclass
class EvalRow:
    query: str
    expected_title: str
    baseline_top1: str
    baseline_top3: str
    rag_top1: str
    rag_top3: str
    baseline_hit1: bool
    baseline_hit3: bool
    rag_hit1: bool
    rag_hit3: bool
    baseline_rr3: float
    rag_rr3: float


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", (text or "").lower())


def _jaccard(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    if inter == 0:
        return 0.0
    return inter / max(1, len(sa | sb))


def _top_k_title_lexical(query: str, titles: List[str], k: int = 3) -> List[str]:
    qt = _tokenize(query)
    scored: List[Tuple[float, str]] = []
    for t in titles:
        score = _jaccard(qt, _tokenize(t))
        scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[: max(1, k)]]


def _rr_at_k(expected_title: str, ranked_titles: List[str], k: int = 3) -> float:
    for idx, title in enumerate(ranked_titles[: max(1, k)], start=1):
        if title == expected_title:
            return 1.0 / idx
    return 0.0


def _load_dataset(dataset_path: Path) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {dataset_path}")

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("dataset JSON must be an object with documents/queries")

    documents = raw.get("documents") or []
    queries = raw.get("queries") or []

    if not isinstance(documents, list) or not isinstance(queries, list):
        raise ValueError("dataset.documents and dataset.queries must be lists")

    docs_out: List[Dict[str, str]] = []
    for i, d in enumerate(documents, start=1):
        if not isinstance(d, dict):
            continue
        title = _normalize_space(str(d.get("title", "")))
        text = _normalize_space(str(d.get("text", "")))
        if not title or not text:
            continue
        docs_out.append({"id": str(i), "title": title, "text": text})

    queries_out: List[Dict[str, str]] = []
    for q in queries:
        if not isinstance(q, dict):
            continue
        query = _normalize_space(str(q.get("query", "")))
        expected_title = _normalize_space(str(q.get("expected_title", "")))
        if not query or not expected_title:
            continue
        queries_out.append({"query": query, "expected_title": expected_title})

    if not docs_out or not queries_out:
        raise ValueError("dataset has no valid documents or queries")

    return docs_out, queries_out


async def evaluate(dataset_path: Path, out_dir: Path, top_k: int = 3) -> Tuple[Path, Path, Dict[str, Any]]:
    docs, queries = _load_dataset(dataset_path)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rag_db_dir = out_dir / f"rag_eval_chroma_{ts}"
    rag = RagService(persist_dir=str(rag_db_dir))

    # Ingest benchmark docs into a temporary Chroma DB.
    for d in docs:
        await rag.ingest_text(
            title=d["title"],
            text=d["text"],
            source_type="benchmark",
            uri=f"benchmark://{d['id']}",
        )

    all_titles = [d["title"] for d in docs]

    rows: List[EvalRow] = []

    for item in queries:
        query = item["query"]
        expected = item["expected_title"]

        baseline_titles = _top_k_title_lexical(query, all_titles, k=top_k)

        rag_results = await rag.search(query=query, top_k=top_k)
        rag_titles = [src.title for _, _, src in rag_results]

        # unique keep order
        seen = set()
        rag_titles_uniq: List[str] = []
        for t in rag_titles:
            if t not in seen:
                seen.add(t)
                rag_titles_uniq.append(t)

        while len(rag_titles_uniq) < top_k:
            rag_titles_uniq.append("")
        while len(baseline_titles) < top_k:
            baseline_titles.append("")

        baseline_rr3 = _rr_at_k(expected, baseline_titles, k=top_k)
        rag_rr3 = _rr_at_k(expected, rag_titles_uniq, k=top_k)

        rows.append(
            EvalRow(
                query=query,
                expected_title=expected,
                baseline_top1=baseline_titles[0],
                baseline_top3=" | ".join(baseline_titles[:top_k]),
                rag_top1=rag_titles_uniq[0],
                rag_top3=" | ".join(rag_titles_uniq[:top_k]),
                baseline_hit1=(baseline_titles[0] == expected),
                baseline_hit3=(expected in baseline_titles[:top_k]),
                rag_hit1=(rag_titles_uniq[0] == expected),
                rag_hit3=(expected in rag_titles_uniq[:top_k]),
                baseline_rr3=baseline_rr3,
                rag_rr3=rag_rr3,
            )
        )

    n = len(rows)
    baseline_top1 = sum(1 for r in rows if r.baseline_hit1) / max(1, n)
    baseline_recall3 = sum(1 for r in rows if r.baseline_hit3) / max(1, n)
    baseline_mrr3 = sum(r.baseline_rr3 for r in rows) / max(1, n)

    rag_top1 = sum(1 for r in rows if r.rag_hit1) / max(1, n)
    rag_recall3 = sum(1 for r in rows if r.rag_hit3) / max(1, n)
    rag_mrr3 = sum(r.rag_rr3 for r in rows) / max(1, n)

    summary = {
        "sample_count": n,
        "top_k": top_k,
        "dataset": str(dataset_path),
        "rag_db_dir": str(rag_db_dir),
        "baseline": {
            "name": "title_lexical_only",
            "top1_accuracy": baseline_top1,
            "recall_at_3": baseline_recall3,
            "mrr_at_3": baseline_mrr3,
        },
        "rag_chroma": {
            "name": "chroma_vector_retrieval",
            "top1_accuracy": rag_top1,
            "recall_at_3": rag_recall3,
            "mrr_at_3": rag_mrr3,
        },
        "uplift": {
            "top1_accuracy_pp": (rag_top1 - baseline_top1) * 100.0,
            "recall_at_3_pp": (rag_recall3 - baseline_recall3) * 100.0,
            "mrr_at_3_pp": (rag_mrr3 - baseline_mrr3) * 100.0,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / f"rag_summary_{ts}.json"
    details_path = out_dir / f"rag_details_{ts}.csv"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with details_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query",
                "expected_title",
                "baseline_top1",
                "baseline_top3",
                "rag_top1",
                "rag_top3",
                "baseline_hit1",
                "baseline_hit3",
                "rag_hit1",
                "rag_hit3",
                "baseline_rr3",
                "rag_rr3",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "query": r.query,
                    "expected_title": r.expected_title,
                    "baseline_top1": r.baseline_top1,
                    "baseline_top3": r.baseline_top3,
                    "rag_top1": r.rag_top1,
                    "rag_top3": r.rag_top3,
                    "baseline_hit1": r.baseline_hit1,
                    "baseline_hit3": r.baseline_hit3,
                    "rag_hit1": r.rag_hit1,
                    "rag_hit3": r.rag_hit3,
                    "baseline_rr3": f"{r.baseline_rr3:.4f}",
                    "rag_rr3": f"{r.rag_rr3:.4f}",
                }
            )

    return summary_path, details_path, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAG uplift with Chroma")
    parser.add_argument(
        "--dataset",
        type=str,
        default="scripts/data/rag_eval_samples_cn_30.json",
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="scripts/out",
        help="Output directory",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="k for Recall@k/MRR@k",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset = Path(args.dataset)
    if not dataset.is_absolute():
        dataset = Path.cwd() / dataset

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir

    summary_path, details_path, summary = asyncio.run(evaluate(dataset, out_dir, top_k=int(args.top_k)))

    print("\n=== RAG Chroma Evaluation Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSummary file: {summary_path}")
    print(f"Details file: {details_path}")


if __name__ == "__main__":
    main()
