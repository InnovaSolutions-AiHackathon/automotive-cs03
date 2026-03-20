"""
RAG Agent — app/agent/rag_agent.py

Retrieval-Augmented Generation agent that searches the ChromaDB knowledge
base and uses a Gemini LLM to synthesise an answer from the retrieved documents.

Processing flow:
    1. Optionally enrich the user query with vehicle context (make/model/year).
    2. Call ``search_docs`` to retrieve the top-k most relevant document chunks
       from ChromaDB.
    3. Build a structured prompt combining the user question and retrieved docs.
    4. Send the prompt to the Gemini LLM for synthesis.
    5. Return the LLM answer with source attributions.

DB schemas used:
    ChromaDB (vector store) — knowledge-base document chunks.
    No MySQL schemas are accessed directly by this agent.
"""
from __future__ import annotations

import logging
from typing import Any

from app.agent.gemini_client import GeminiClient
from app.config import settings
from app.rag.ingest import search_docs

logger = logging.getLogger(__name__)

_SYNTHESIS_PROMPT = (
    "You are an expert automotive customer service assistant. "
    "Using ONLY the provided reference documents, answer the user's question accurately. "
    "If the documents do not contain enough information, say so clearly. "
    "Be concise and professional."
)


class RAGAgent:
    """Agent that retrieves relevant documents and synthesises LLM answers.

    Attributes:
        llm: Gemini LLM client used for answer synthesis.
    """

    def __init__(self, llm: GeminiClient) -> None:
        """Initialise RAGAgent with an LLM client.

        Args:
            llm: A configured ``GeminiClient`` instance for generating answers.
        """
        self.llm = llm
        logger.debug("RAGAgent: initialised with GeminiClient")

    async def process_query(
        self, user_message: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Retrieve relevant knowledge-base documents and synthesise an answer.

        Args:
            user_message: The user's natural-language question.
            context: Request context dict; may contain ``vehicle_info`` (dict)
                with ``make``, ``model``, and optional ``year`` keys to enrich
                the search query.

        Returns:
            dict[str, Any]: Contains:
                - ``"response"`` (str) — LLM-synthesised answer from documents.
                - ``"sources"`` (list[str]) — deduplicated source identifiers
                  from the retrieved documents.

            If no documents are found, returns a ``"No relevant documentation"``
            message.  On any error, returns a graceful error message.
        """
        vehicle_info = context.get("vehicle_info", {})

        logger.info(
            f"[RAGAgent] process_query message_preview={user_message[:80]!r} "
            f"has_vehicle_info={bool(vehicle_info)}"
        )

        try:
            # Enrich query with vehicle context if available
            enriched = user_message
            if vehicle_info.get("make") and vehicle_info.get("model"):
                enriched = (
                    f"{user_message} "
                    f"(vehicle: {vehicle_info['make']} {vehicle_info['model']} "
                    f"{vehicle_info.get('year', '')})"
                )
                logger.debug(
                    f"[RAGAgent] enriched query with vehicle context: "
                    f"{vehicle_info['make']} {vehicle_info['model']}"
                )

            logger.debug(f"[RAGAgent] searching docs top_k=4 enriched_query_preview={enriched[:80]!r}")
            docs = await search_docs(enriched, top_k=4)
            documents  = docs.get("documents", [])
            sources    = docs.get("sources", [])

            logger.info(
                f"[RAGAgent] search_docs returned {len(documents)} document(s) "
                f"sources={sources}"
            )

            if not documents:
                logger.warning("[RAGAgent] no relevant documents found for query")
                return {
                    "response": "No relevant documentation found for this query.",
                    "sources": [],
                }

            context_text = "\n\n".join(
                f"[Source: {src}]\n{doc}"
                for doc, src in zip(documents, sources)
            )
            prompt = (
                f"User question: {user_message}\n\n"
                f"Reference documents:\n{context_text}"
            )

            logger.debug(
                f"[RAGAgent] sending synthesis prompt to LLM "
                f"doc_count={len(documents)}"
            )
            response = await self.llm.generate(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                system_prompt=_SYNTHESIS_PROMPT,
            )

            answer = response.text.strip()
            logger.info(
                f"[RAGAgent] synthesis complete response_length={len(answer)} "
                f"source_count={len(set(sources))}"
            )
            return {
                "response": answer,
                "sources":  list(set(sources)),
            }

        except Exception as exc:
            logger.error(f"[RAGAgent] error processing query: {exc}")
            return {
                "response": "Unable to retrieve knowledge base information.",
                "sources": [],
            }


def get_rag_agent() -> RAGAgent:
    """Factory function — create a new RAGAgent instance with a fresh LLM client.

    Returns:
        RAGAgent: Configured instance ready to process a single query.
    """
    logger.debug(
        f"get_rag_agent: creating RAGAgent with model={settings.GEMINI_MODEL!r}"
    )
    llm = GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
    )
    return RAGAgent(llm=llm)
