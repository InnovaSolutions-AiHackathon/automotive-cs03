"""
RAG knowledge base ingestion + search.
Knowledge directory comes from settings — no hardcoded paths.
"""
from __future__ import annotations

import os
from loguru import logger

from app.config import settings
from app.rag.vectorstore import get_collection

_CHUNK_SIZE    = 500
_CHUNK_OVERLAP = 450   # sliding window — large overlap for short manuals


async def ingest_knowledge_base() -> None:
    knowledge_dir = settings.KNOWLEDGE_DIR
    if not os.path.isdir(knowledge_dir):
        logger.warning(f"Knowledge directory not found: {knowledge_dir} — skipping ingest")
        return

    col = get_collection()
    if col.count() > 0:
        logger.info(f"KB already has {col.count()} chunks — skipping ingest")
        return

    docs, ids, metas = [], [], []
    for fname in os.listdir(knowledge_dir):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(knowledge_dir, fname)
        with open(fpath, encoding="utf-8") as fh:
            text = fh.read()

        start = 0
        while start < len(text):
            chunk = text[start: start + _CHUNK_SIZE].strip()
            if chunk:
                chunk_id = f"{fname}_{start}"
                docs.append(chunk)
                ids.append(chunk_id)
                metas.append({"source": fname, "offset": start})
            start += _CHUNK_OVERLAP

    if docs:
        col.add(documents=docs, ids=ids, metadatas=metas)
        logger.info(f"Ingested {len(docs)} chunks from {knowledge_dir}")
    else:
        logger.warning(f"No .txt files found in {knowledge_dir}")


async def search_docs(query: str, top_k: int = 3) -> dict:
    col = get_collection()
    if col.count() == 0:
        return {"documents": [], "sources": []}

    try:
        r = col.query(query_texts=[query], n_results=min(top_k, col.count()))
        return {
            "documents": r["documents"][0],
            "sources":   [m["source"] for m in r["metadatas"][0]],
        }
    except Exception as exc:
        logger.error(f"Vector search failed: {exc}")
        return {"documents": [], "sources": []}
