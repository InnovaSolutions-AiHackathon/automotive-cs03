from typing import Dict, Any, List
from app.agent.vector_client import VectorDBClient

from agent.claude_client import ClaudeClient

class RAGAgent:
    def __init__(self, vector_db: VectorDBClient, llm: ClaudeClient):
        self.vector_db = vector_db
        self.llm = llm

    async def process_query(self, user_query: str, vehicle_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        End-to-end query processing:
        1. Retrieve relevant docs
        2. Generate response
        """
        docs = await self.retrieve_knowledge(user_query, vehicle_info)
        response = await self.generate_response(user_query, docs, vehicle_info)
        return {"response": response, "sources": docs}

    async def retrieve_knowledge(self, query: str, vehicle_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Semantic search in vector DB
        """
        enriched_query = f"{query} for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}"
        results = await self.vector_db.search(enriched_query, top_k=5)
        return results

    async def generate_response(self, query: str, docs: List[Dict[str, Any]], vehicle_info: Dict[str, Any]) -> str:
        """
        Use LLM (Claude, GPT, etc.) to generate a contextual answer
        """
        context = "\n".join([doc["content"] for doc in docs])
        prompt = f"""
        User query: {query}
        Vehicle info: {vehicle_info}
        Relevant docs:
        {context}

        Provide a helpful, concise answer for the customer.
        """
        return await self.llm.generate(prompt)

    async def index_document(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """
        Add new documents to knowledge base
        """
        await self.vector_db.upsert(doc_id, content, metadata)


# Factory function
def get_rag_agent() -> RAGAgent:
    vector_db = VectorDBClient(api_key="YOUR_VECTOR_DB_KEY")
    llm = ClaudeClient(api_key="YOUR_LLM_KEY")
    return RAGAgent(vector_db, llm)
