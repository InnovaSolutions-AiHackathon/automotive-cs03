import chromadb
from chromadb.utils import embedding_functions
from app.config import settings

_collection = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = client.get_or_create_collection(
            name="automotive_knowledge",
            embedding_function=ef
        )
    return _collection