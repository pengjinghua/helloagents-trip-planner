"""Lightweight RAG service.

Goals:
- Allow users to ingest their own text, local files, or external URLs.
- Persist chunks in Chroma (lightweight local vector DB).
- Prefer OpenAI-compatible embeddings for semantic retrieval.
- Fall back to lexical scoring when semantic retrieval is unavailable.

This is intentionally minimal and focused on the UX requested.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import math
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from .embeddings_service import embed_texts


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = (data or "").strip()
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize_ws(text: str) -> str:
    # Preserve line breaks somewhat but normalize excessive whitespace.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Drop control chars except \n and \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_low_quality_text(text: str) -> bool:
    """Heuristic filter for binary/garbled text.

    This prevents users from accidentally importing .docx/.pdf as raw bytes and
    getting unreadable chunks in search results.
    """

    raw = text or ""

    # Hard reject common ZIP/DOCX signatures (docx is a zip)
    # These often show up when users upload .docx but the backend decodes bytes as utf-8.
    if "PK\x03\x04" in raw or "PK\x05\x06" in raw or "PK\x07\x08" in raw:
        return True
    low_raw = raw.lower()
    if "[content_types].xml" in low_raw or "_rels/.rels" in low_raw or "word/" in low_raw:
        return True
    if "word/document.xml" in low_raw or "word/styles.xml" in low_raw:
        return True

    if len(raw) < 10:
        return True

    # If there are many control/non-printable characters, this is almost certainly decoded binary.
    # (Normal human text should contain only a few: mainly \n / \t / \r.)
    control = 0
    for ch in raw:
        o = ord(ch)
        if (o < 32 and ch not in "\n\t\r") or (0x7F <= o < 0xA0):
            control += 1
    if control / max(1, len(raw)) >= 0.003:
        return True

    t = _normalize_ws(raw)
    if len(t) < 10:
        return True

    allowed_punct = "，。！？、；：,.!?;:()[]{}<>\"'“”‘’/\\-—_@#%&*+=~|"

    # Count printable-ish characters + guard against high 'odd' ratio.
    good = 0
    odd = 0
    for ch in t:
        o = ord(ch)
        if ch in "\n\t ":
            good += 1
        elif 0x4E00 <= o <= 0x9FFF:  # CJK
            good += 1
        elif 0x30 <= o <= 0x39 or 0x41 <= o <= 0x5A or 0x61 <= o <= 0x7A:
            good += 1
        elif ch in allowed_punct:
            good += 1
        else:
            odd += 1

    ratio = good / max(1, len(t))
    odd_ratio = odd / max(1, len(t))
    # If too many non-printable/unusual bytes, treat as low quality.
    return ratio < 0.65 or odd_ratio > 0.20


def _simple_tokenize(text: str) -> List[str]:
    # Mixed Chinese/English tokenization: split on non-word, keep CJK chars.
    # This is for lexical fallback only.
    tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+", (text or "").lower())
    return tokens


def _chunk_text(text: str, *, max_chars: int = 900, overlap: int = 120) -> List[str]:
    text = _normalize_ws(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []

    buf = ""
    for para in paragraphs:
        if not buf:
            buf = para
            continue

        if len(buf) + 2 + len(para) <= max_chars:
            buf = buf + "\n\n" + para
            continue

        chunks.append(buf)
        # start new buffer with overlap tail
        tail = buf[-overlap:] if overlap > 0 else ""
        buf = (tail + "\n\n" + para).strip()

        # still too large => hard split
        while len(buf) > max_chars:
            chunks.append(buf[:max_chars])
            tail2 = buf[max_chars - overlap : max_chars] if overlap > 0 else ""
            buf = (tail2 + buf[max_chars:]).strip()

    if buf:
        chunks.append(buf)

    # Final cleanup + keep reasonably short chunks (users often paste short rules)
    out = [c.strip() for c in chunks if len(c.strip()) >= 10]
    return out


def _cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _lexical_score(query_tokens: List[str], doc_tokens: List[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0

    q = set(query_tokens)
    d = set(doc_tokens)
    inter = len(q & d)
    if inter == 0:
        return 0.0
    # Jaccard-ish
    return inter / (len(q) + len(d) - inter)


def _l2_normalize(vec: List[float]) -> List[float]:
    s = sum(x * x for x in vec)
    if s <= 0:
        return vec
    inv = 1.0 / math.sqrt(s)
    return [x * inv for x in vec]


def _hash_embedding(text: str, dim: int) -> List[float]:
    """Deterministic local embedding fallback.

    Used only when external embedding API is unavailable.
    """

    tokens = _simple_tokenize(text)
    if not tokens:
        return [0.0] * max(1, int(dim))

    d = max(1, int(dim))
    vec = [0.0] * d
    for tok in tokens:
        idx = (hash(tok) & 0x7FFFFFFF) % d
        vec[idx] += 1.0
    return _l2_normalize(vec)


def _align_embedding(vec: List[float], dim: int) -> List[float]:
    d = max(1, int(dim))
    if len(vec) == d:
        return vec
    if len(vec) > d:
        return vec[:d]
    return vec + [0.0] * (d - len(vec))


@dataclass
class RagSource:
    id: int
    title: str
    source_type: str
    uri: str
    created_at: str


@dataclass
class RagChunk:
    id: int
    source_id: int
    chunk_index: int
    content: str
    embedding_json: Optional[str]

    @property
    def embedding(self) -> Optional[List[float]]:
        if not self.embedding_json:
            return None
        try:
            raw = json.loads(self.embedding_json)
            if isinstance(raw, list):
                return [float(x) for x in raw]
        except Exception:
            return None
        return None


class RagService:
    def __init__(self, persist_dir: str) -> None:
        self._chromadb = importlib.import_module("chromadb")
        if self._chromadb is None:
            raise RuntimeError("缺少 chromadb 依赖，请先安装后重试")

        self._persist_dir = os.path.abspath(persist_dir)
        self._lock = threading.Lock()
        self._state_path = os.path.join(self._persist_dir, "rag_state.json")
        self._state = {
            "next_source_id": 1,
            "next_chunk_id": 1,
            "embedding_dim": None,
        }
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(self._persist_dir, exist_ok=True)

        self._load_state()

        self._client = self._chromadb.PersistentClient(path=self._persist_dir)
        self._sources = self._client.get_or_create_collection(
            name="rag_sources",
            metadata={"description": "RAG source metadata"},
            embedding_function=None,
        )
        self._chunks = self._client.get_or_create_collection(
            name="rag_chunks",
            metadata={"hnsw:space": "cosine", "description": "RAG chunks + vectors"},
            embedding_function=None,
        )

    def _load_state(self) -> None:
        if not os.path.exists(self._state_path):
            return
        try:
            raw = json.loads(open(self._state_path, "r", encoding="utf-8").read())
            if isinstance(raw, dict):
                self._state["next_source_id"] = int(raw.get("next_source_id", 1))
                self._state["next_chunk_id"] = int(raw.get("next_chunk_id", 1))
                emb_dim = raw.get("embedding_dim")
                self._state["embedding_dim"] = int(emb_dim) if emb_dim is not None else None
        except Exception:
            # keep defaults if state is corrupted
            pass

    def _save_state(self) -> None:
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._state_path)

    def _next_source_id(self) -> int:
        v = int(self._state.get("next_source_id") or 1)
        self._state["next_source_id"] = v + 1
        self._save_state()
        return v

    def _next_chunk_ids(self, n: int) -> List[int]:
        start = int(self._state.get("next_chunk_id") or 1)
        ids = list(range(start, start + max(0, int(n))))
        self._state["next_chunk_id"] = start + len(ids)
        self._save_state()
        return ids

    async def _embed_with_fallback(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        current_dim = self._state.get("embedding_dim")

        try:
            vectors = await embed_texts(texts)
            if not vectors:
                raise ValueError("empty embeddings")

            provider_dim = len(vectors[0])
            if current_dim is None:
                self._state["embedding_dim"] = provider_dim
                self._save_state()
                current_dim = provider_dim

            aligned = [_align_embedding([float(x) for x in v], int(current_dim)) for v in vectors]
            return [_l2_normalize(v) for v in aligned]
        except Exception:
            # External embedding unavailable: fallback deterministic local embeddings.
            if current_dim is None:
                current_dim = int(os.getenv("RAG_FALLBACK_EMBEDDING_DIM", "1536"))
                self._state["embedding_dim"] = int(current_dim)
                self._save_state()
            return [_hash_embedding(t, int(current_dim)) for t in texts]

    @staticmethod
    def _safe_meta_str(meta: Dict[str, Any], key: str, default: str = "") -> str:
        v = meta.get(key, default)
        if v is None:
            return default
        return str(v)

    @staticmethod
    def _safe_meta_int(meta: Dict[str, Any], key: str, default: int = 0) -> int:
        v = meta.get(key, default)
        try:
            return int(v)
        except Exception:
            return int(default)

    def list_sources(self) -> List[RagSource]:
        raw = self._sources.get(include=["metadatas"])
        metadatas = raw.get("metadatas") or []
        out: List[RagSource] = []
        for m in metadatas:
            if not isinstance(m, dict):
                continue
            out.append(
                RagSource(
                    id=self._safe_meta_int(m, "source_id", 0),
                    title=self._safe_meta_str(m, "title", "untitled"),
                    source_type=self._safe_meta_str(m, "source_type", "text"),
                    uri=self._safe_meta_str(m, "uri", ""),
                    created_at=self._safe_meta_str(m, "created_at", ""),
                )
            )
        out.sort(key=lambda x: x.id, reverse=True)
        return out

    def delete_source(self, source_id: int) -> Tuple[int, int]:
        """Delete a knowledge source and all its chunks.

        Returns (deleted_sources, deleted_chunks).
        """
        sid = int(source_id)
        with self._lock:
            chunk_rows = self._chunks.get(where={"source_id": sid}, include=[])
            chunk_ids = chunk_rows.get("ids") or []
            deleted_chunks = len(chunk_ids)
            if chunk_ids:
                self._chunks.delete(ids=chunk_ids)

            src_rows = self._sources.get(where={"source_id": sid}, include=[])
            src_ids = src_rows.get("ids") or []
            deleted_sources = len(src_ids)
            if src_ids:
                self._sources.delete(ids=src_ids)

        return deleted_sources, deleted_chunks

    def clear_all(self) -> Tuple[int, int]:
        """Delete all sources and all chunks. Returns (deleted_sources, deleted_chunks)."""
        with self._lock:
            deleted_chunks = int(self._chunks.count())
            deleted_sources = int(self._sources.count())

            try:
                self._client.delete_collection("rag_chunks")
            except Exception:
                pass
            try:
                self._client.delete_collection("rag_sources")
            except Exception:
                pass

            self._sources = self._client.get_or_create_collection(
                name="rag_sources",
                metadata={"description": "RAG source metadata"},
                embedding_function=None,
            )
            self._chunks = self._client.get_or_create_collection(
                name="rag_chunks",
                metadata={"hnsw:space": "cosine", "description": "RAG chunks + vectors"},
                embedding_function=None,
            )

            self._state = {
                "next_source_id": 1,
                "next_chunk_id": 1,
                "embedding_dim": None,
            }
            self._save_state()

        return deleted_sources, deleted_chunks

    async def ingest_text(self, *, title: str, text: str, source_type: str, uri: str) -> RagSource:
        chunks = _chunk_text(text)
        chunks = [c for c in chunks if not _is_low_quality_text(c)]
        if not chunks:
            raise ValueError("导入内容为空/无法切分，或内容疑似为二进制文件（建议上传txt/md，或docx请用docx格式上传）")

        created_at = _utc_now_iso()
        clean_title = title.strip() or "untitled"

        with self._lock:
            source_id = self._next_source_id()

            self._sources.add(
                ids=[f"src:{source_id}"],
                documents=[clean_title],
                metadatas=[
                    {
                        "source_id": source_id,
                        "title": clean_title,
                        "source_type": source_type,
                        "uri": uri,
                        "created_at": created_at,
                    }
                ],
            )

            chunk_ids = self._next_chunk_ids(len(chunks))

        embeddings = await self._embed_with_fallback(chunks)

        with self._lock:
            ids = [f"chk:{cid}" for cid in chunk_ids]
            metadatas = [
                {
                    "chunk_id": int(chunk_ids[idx]),
                    "source_id": source_id,
                    "chunk_index": idx,
                    "source_title": clean_title,
                    "source_type": source_type,
                    "source_uri": uri,
                    "source_created_at": created_at,
                    "created_at": created_at,
                }
                for idx in range(len(chunks))
            ]
            self._chunks.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
                embeddings=embeddings,
            )

        return RagSource(id=source_id, title=clean_title, source_type=source_type, uri=uri, created_at=created_at)

    async def ingest_url(self, *, title: str, url: str) -> RagSource:
        u = (url or "").strip()
        if not u:
            raise ValueError("url 不能为空")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(u, headers={"User-Agent": "helloagents-trip-planner/1.0"})
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            raw = resp.text

        if "text/html" in content_type or ("<html" in raw.lower() and "</html" in raw.lower()):
            parser = _HTMLTextExtractor()
            parser.feed(raw)
            text = parser.get_text()
        else:
            text = raw

        inferred_title = title.strip() or u
        return await self.ingest_text(title=inferred_title, text=text, source_type="url", uri=u)

    async def search(self, *, query: str, top_k: int = 6) -> List[Tuple[float, RagChunk, RagSource]]:
        q = (query or "").strip()
        if not q:
            return []

        n = max(1, min(int(top_k), 20))
        if int(self._chunks.count()) <= 0:
            return []

        scored: List[Tuple[float, RagChunk, RagSource]] = []

        # Semantic retrieval on Chroma vectors
        try:
            query_emb = (await self._embed_with_fallback([q]))[0]
            raw = self._chunks.query(
                query_embeddings=[query_emb],
                n_results=max(n * 3, n),
                include=["documents", "metadatas", "distances"],
            )

            ids = (raw.get("ids") or [[]])[0]
            docs = (raw.get("documents") or [[]])[0]
            metas = (raw.get("metadatas") or [[]])[0]
            dists = (raw.get("distances") or [[]])[0]

            for i in range(min(len(ids), len(docs), len(metas), len(dists))):
                meta = metas[i] or {}
                content = str(docs[i] or "")
                if _is_low_quality_text(content):
                    continue

                chunk = RagChunk(
                    id=self._safe_meta_int(meta, "chunk_id", 0),
                    source_id=self._safe_meta_int(meta, "source_id", 0),
                    chunk_index=self._safe_meta_int(meta, "chunk_index", 0),
                    content=content,
                    embedding_json=None,
                )

                source = RagSource(
                    id=self._safe_meta_int(meta, "source_id", 0),
                    title=self._safe_meta_str(meta, "source_title", ""),
                    source_type=self._safe_meta_str(meta, "source_type", ""),
                    uri=self._safe_meta_str(meta, "source_uri", ""),
                    created_at=self._safe_meta_str(meta, "source_created_at", ""),
                )

                # cosine distance => similarity-like score in [0,1]
                dist = float(dists[i]) if dists[i] is not None else 1.0
                score = max(0.0, min(1.0, 1.0 - dist))
                scored.append((score, chunk, source))

            if scored:
                scored.sort(key=lambda x: x[0], reverse=True)
                return scored[:n]
        except Exception:
            # degrade to lexical fallback
            pass

        # Lexical fallback
        qt = _simple_tokenize(q)
        all_rows = self._chunks.get(include=["documents", "metadatas"])
        docs = all_rows.get("documents") or []
        metas = all_rows.get("metadatas") or []

        for i in range(min(len(docs), len(metas))):
            content = str(docs[i] or "")
            meta = metas[i] or {}
            if _is_low_quality_text(content):
                continue
            score = _lexical_score(qt, _simple_tokenize(content))
            if score <= 0:
                continue

            chunk = RagChunk(
                id=self._safe_meta_int(meta, "chunk_id", 0),
                source_id=self._safe_meta_int(meta, "source_id", 0),
                chunk_index=self._safe_meta_int(meta, "chunk_index", 0),
                content=content,
                embedding_json=None,
            )

            source = RagSource(
                id=self._safe_meta_int(meta, "source_id", 0),
                title=self._safe_meta_str(meta, "source_title", ""),
                source_type=self._safe_meta_str(meta, "source_type", ""),
                uri=self._safe_meta_str(meta, "source_uri", ""),
                created_at=self._safe_meta_str(meta, "source_created_at", ""),
            )
            scored.append((score, chunk, source))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:n]


_rag_singleton: Optional[RagService] = None


def get_rag_service() -> RagService:
    global _rag_singleton
    if _rag_singleton is None:
        # Keep persistent vector DB under backend/app/data
        base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        persist_dir = os.path.abspath(os.path.join(base_dir, "rag_chroma"))
        _rag_singleton = RagService(persist_dir=persist_dir)
    return _rag_singleton
