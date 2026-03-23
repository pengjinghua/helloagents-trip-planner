"""RAG API routes.

Supports:
- ingest text
- ingest url
- ingest file (txt/md)
- search
- list sources
"""

from __future__ import annotations

import os
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File

from ...models.schemas import (
    RagIngestTextRequest,
    RagIngestUrlRequest,
    RagSearchRequest,
    RagSourcesResponse,
    RagSearchResponse,
    RagIngestResponse,
)
from ...services.rag_service import get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG知识库"])


def _extract_docx_text(raw: bytes) -> str:
    try:
        from docx import Document  # type: ignore
    except Exception as e:
        raise RuntimeError("缺少python-docx依赖，请先安装后重试") from e

    doc = Document(BytesIO(raw))
    parts = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


@router.get("/sources", response_model=RagSourcesResponse, summary="列出已导入的知识源")
async def list_sources():
    try:
        rag = get_rag_service()
        sources = [
            {
                "id": s.id,
                "title": s.title,
                "source_type": s.source_type,
                "uri": s.uri,
                "created_at": s.created_at,
            }
            for s in rag.list_sources()
        ]
        return RagSourcesResponse(success=True, message="ok", data=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出知识源失败: {str(e)}")


@router.delete("/sources/{source_id}", summary="删除某个知识源(含历史chunks)")
async def delete_source(source_id: int):
    try:
        rag = get_rag_service()
        deleted_sources, deleted_chunks = rag.delete_source(int(source_id))
        if deleted_sources <= 0:
            raise HTTPException(status_code=404, detail="未找到该知识源")
        return {
            "success": True,
            "message": "删除成功",
            "data": {"deleted_sources": deleted_sources, "deleted_chunks": deleted_chunks},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/clear", summary="清空知识库(删除所有sources与chunks)")
async def clear_all():
    try:
        rag = get_rag_service()
        deleted_sources, deleted_chunks = rag.clear_all()
        return {
            "success": True,
            "message": "清空成功",
            "data": {"deleted_sources": deleted_sources, "deleted_chunks": deleted_chunks},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


@router.post("/ingest/text", response_model=RagIngestResponse, summary="导入文本到知识库")
async def ingest_text(req: RagIngestTextRequest):
    try:
        rag = get_rag_service()
        source = await rag.ingest_text(title=req.title, text=req.text, source_type="text", uri=req.title or "text")
        data = {
            "id": source.id,
            "title": source.title,
            "source_type": source.source_type,
            "uri": source.uri,
            "created_at": source.created_at,
        }
        return RagIngestResponse(success=True, message="导入成功", data=data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.post("/ingest/url", response_model=RagIngestResponse, summary="导入URL内容到知识库")
async def ingest_url(req: RagIngestUrlRequest):
    try:
        rag = get_rag_service()
        source = await rag.ingest_url(title=req.title or "", url=req.url)
        data = {
            "id": source.id,
            "title": source.title,
            "source_type": source.source_type,
            "uri": source.uri,
            "created_at": source.created_at,
        }
        return RagIngestResponse(success=True, message="导入成功", data=data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.post("/ingest/file", response_model=RagIngestResponse, summary="上传文件并导入到知识库")
async def ingest_file(file: UploadFile = File(...), title: str = ""):
    try:
        name = file.filename or "uploaded"
        raw = await file.read()

        ext = os.path.splitext(name.lower())[1]

        if ext == ".docx":
            text = _extract_docx_text(raw)
        elif ext in {".txt", ".md", ".markdown", ".csv"}:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="ignore")
        else:
            raise ValueError("暂不支持该文件类型，请上传 txt/md/csv/docx")

        rag = get_rag_service()
        source = await rag.ingest_text(
            title=(title.strip() or name),
            text=text,
            source_type="file",
            uri=name,
        )
        data = {
            "id": source.id,
            "title": source.title,
            "source_type": source.source_type,
            "uri": source.uri,
            "created_at": source.created_at,
        }
        return RagIngestResponse(success=True, message="导入成功", data=data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.post("/search", response_model=RagSearchResponse, summary="检索知识库")
async def search(req: RagSearchRequest):
    try:
        rag = get_rag_service()
        results = await rag.search(query=req.query, top_k=req.top_k)
        items = [
            {
                "score": float(score),
                "source": {
                    "id": source.id,
                    "title": source.title,
                    "source_type": source.source_type,
                    "uri": source.uri,
                    "created_at": source.created_at,
                },
                "chunk": {
                    "id": chunk.id,
                    "source_id": chunk.source_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                },
            }
            for score, chunk, source in results
        ]
        return RagSearchResponse(success=True, message="ok", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")
