"""
Warranty Agent — app/agent/warranty_agent.py

Specialist agent that validates warranty eligibility for a vehicle and repair
type.  When the repair is NOT covered, augments the response with relevant
knowledge-base content from the RAG store.

Processing flow:
    1. Extract ``vehicle_id`` from context; infer ``repair_type`` via keyword
       matching if not provided explicitly.
    2. Delegate coverage check to ``warranty_engine.check_warranty``.
    3. If covered: return a structured coverage summary.
    4. If not covered: retrieve related RAG documents and append them to the
       response text.

DB schemas used:
    cs03_warranty — ``warranty_records``, ``warranty_rules`` tables
    cs03_vehicle  — ``vehicles`` table (for odometer lookup in the engine)
    ChromaDB      — knowledge-base vector store (RAG fallback)
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.warranty_engine import check_warranty
from app.rag.ingest import search_docs

logger = logging.getLogger(__name__)


class WarrantyAgent:
    """Agent that checks warranty coverage and augments uncovered results with RAG knowledge.

    This agent is stateless — a fresh instance is created per request via
    the ``get_warranty_agent`` factory.
    """

    async def process_query(
        self, user_message: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Check warranty coverage for a vehicle and repair type.

        Args:
            user_message: The user's natural-language warranty query.
            context: Request context dict with optional keys:
                - ``vehicle_id`` (str) — vehicle code to check coverage for.
                - ``repair_type`` (str) — explicit repair category; if absent,
                  inferred from ``user_message`` via ``_infer_repair_type``.

        Returns:
            dict[str, Any]: Contains:
                - ``"response"`` (str) — human-readable coverage result.
                - ``"warranty"`` (dict) — raw result from the warranty engine.
                - ``"sources"`` (list[str]) — DB schemas consulted.

            If ``vehicle_id`` is absent, returns a prompt asking for it.
            On errors, returns a graceful error message.
        """
        vehicle_id  = context.get("vehicle_id")
        repair_type = context.get("repair_type", self._infer_repair_type(user_message))

        logger.info(
            f"[WarrantyAgent] process_query vehicle_id={vehicle_id!r} "
            f"repair_type={repair_type!r} "
            f"message_preview={user_message[:80]!r}"
        )

        if not vehicle_id:
            logger.warning("[WarrantyAgent] no vehicle_id in context — cannot check warranty")
            return {
                "response": "Please provide a vehicle ID to check warranty coverage.",
                "sources": [],
            }

        try:
            logger.debug(
                f"[WarrantyAgent] calling check_warranty vehicle_id={vehicle_id!r} "
                f"repair_type={repair_type!r}"
            )
            result = await check_warranty(vehicle_id, repair_type)

            logger.info(
                f"[WarrantyAgent] warranty check complete covered={result.get('covered')} "
                f"vehicle_id={vehicle_id!r} repair_type={repair_type!r}"
            )

            if result.get("covered"):
                text = (
                    f"Warranty ACTIVE — {result['coverage_type']} coverage, "
                    f"expires {result['expires']}, "
                    f"{result['miles_remaining']:,} miles remaining."
                )
                logger.info(
                    f"[WarrantyAgent] covered: coverage_type={result.get('coverage_type')!r} "
                    f"expires={result.get('expires')!r}"
                )
            else:
                reason = result.get('reason', 'Unknown reason')
                logger.info(
                    f"[WarrantyAgent] not covered: reason={reason!r} — augmenting with RAG"
                )
                # Augment with RAG knowledge base
                logger.debug("[WarrantyAgent] querying RAG knowledge base (top_k=2)")
                rag = await search_docs(user_message, top_k=2)
                rag_docs = rag.get("documents", [])
                logger.debug(f"[WarrantyAgent] RAG returned {len(rag_docs)} document(s)")
                rag_text = " ".join(rag_docs)
                text = f"Warranty NOT covered: {reason}. {rag_text}".strip()

            return {"response": text, "sources": ["cs03_warranty DB"], "warranty": result}

        except Exception as exc:
            logger.error(
                f"[WarrantyAgent] error checking warranty for vehicle_id={vehicle_id!r}: {exc}"
            )
            return {
                "response": "Unable to retrieve warranty information. Please try again.",
                "sources": [],
            }

    @staticmethod
    def _infer_repair_type(message: str) -> str:
        """Infer the repair type category from free-text using keyword matching.

        Scans the lowercased message for known repair-category keywords.
        Returns the first match, or ``'general'`` if none are found.

        Args:
            message: The user's natural-language message.

        Returns:
            str: A repair type string such as ``'engine'``, ``'brakes'``, or
                ``'general'`` as the default fallback.
        """
        keywords = [
            "engine", "transmission", "drivetrain", "electrical", "brakes",
            "suspension", "ac", "interior", "catalytic_converter", "o2_sensor",
            "tires", "wiper_blades",
        ]
        msg = message.lower()
        for kw in keywords:
            if kw.replace("_", " ") in msg or kw in msg:
                logger.debug(f"_infer_repair_type: matched keyword={kw!r}")
                return kw
        logger.debug("_infer_repair_type: no keyword matched — defaulting to 'general'")
        return "general"


def get_warranty_agent() -> WarrantyAgent:
    """Factory function — create a new stateless WarrantyAgent instance.

    Returns:
        WarrantyAgent: Fresh instance ready to process a single query.
    """
    logger.debug("get_warranty_agent: creating new WarrantyAgent instance")
    return WarrantyAgent()
