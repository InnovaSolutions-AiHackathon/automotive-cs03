import os
from app.rag.vectorstore import get_collection
from loguru import logger

KNOWLEDGE_DIR = "./knowledge_base"

async def ingest_knowledge_base():
    col = get_collection()
    if col.count() > 0:
        logger.info(f"KB already has {col.count()} chunks — skipping ingest")
        return
    docs, ids, metas = [], [], []
    for fname in os.listdir(KNOWLEDGE_DIR):
        if not fname.endswith(".txt"): continue
        with open(os.path.join(KNOWLEDGE_DIR, fname), encoding="utf-8") as f:
            text = f.read()
        start = 0
        while start < len(text):
            chunk = text[start:start+500].strip()
            if chunk:
                docs.append(chunk); ids.append(f"{fname}_{start}")
                metas.append({"source": fname})
            start += 450
    if docs:
        col.add(documents=docs, ids=ids, metadatas=metas)
        logger.info(f"✅ Ingested {len(docs)} chunks from knowledge_base/")

async def search_docs(query: str, top_k: int = 3) -> dict:
    col = get_collection()
    r = col.query(query_texts=[query], n_results=top_k)
    return {
        "documents": r["documents"][0],
        "sources": [m["source"] for m in r["metadatas"][0]]
    }