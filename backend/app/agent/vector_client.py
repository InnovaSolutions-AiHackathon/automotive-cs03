# app/agent/vector_client.py
import chromadb
from typing import List, Dict, Any

class VectorDBClient:
    def __init__(self, collection_name: str = "docs"):
        # Initialize Chroma client
        self.client = chromadb.Client()
        # Create or get collection
        self.collection = self.client.get_or_create_collection(collection_name)

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search in ChromaDB.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        # Return documents with metadata
        docs = []
        for i in range(len(results["documents"][0])):
            docs.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i]
            })
        return docs

    async def upsert(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """
        Add or update a document in ChromaDB.
        """
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )
