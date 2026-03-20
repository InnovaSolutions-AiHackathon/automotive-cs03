"""
Multi-Agent Orchestrator — app/orch/orchestrator.py

Central routing layer that:
    1. Classifies the user's intent via ``classify_intent`` (LLM-based).
    2. Dispatches to one or more specialist agents in parallel using
       ``asyncio.gather``.
    3. Merges the agents' structured responses into a single reply.
    4. Falls back to the RAG agent for knowledge queries when no structured
       agent matches.
    5. Falls back to the general conversational LLM (``run_agent``) as a
       last resort.

Agent intent map:
    ``vehicle``   → VehicleAgent   (cs03_vehicle DB)
    ``warranty``  → WarrantyAgent  (cs03_warranty DB)
    ``scheduler`` → SchedulerAgent (cs03_scheduler DB)
    ``telemetry`` → TelemetryAgent (cs03_vehicle + cs03_telematics DB)

Fallbacks:
    ``general`` intent → RAGAgent → run_agent (conversational LLM)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agent.askAI import run_agent
from app.agent.classify_intent import classify_intent
from app.agent.gemini_client import GeminiClient
from app.agent.rag_agent import get_rag_agent
from app.agent.scheduler_agent import get_scheduler_agent
from app.agent.telemetry_agent import get_telemetry_agent
from app.agent.vehicle_agent import get_vehicle_agent
from app.agent.warranty_agent import get_warranty_agent
from app.config import settings

logger = logging.getLogger(__name__)


def _build_llm_client() -> GeminiClient:
    """Instantiate a fresh Gemini LLM client using application settings.

    Returns:
        GeminiClient: Configured client for the model specified in
            ``settings.GEMINI_MODEL``.
    """
    logger.debug(
        f"_build_llm_client: creating GeminiClient model={settings.GEMINI_MODEL!r}"
    )
    return GeminiClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)


async def run_orchestrator(user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route a user message to the appropriate agent(s) and return a merged response.

    Processing pipeline:
        1. Classify user intent (may return multiple intents).
        2. Fan out to all matching specialist agents concurrently.
        3. If structured agents produced responses, merge and return.
        4. Otherwise try RAG agent for knowledge retrieval.
        5. Final fallback: conversational LLM via ``run_agent``.

    Args:
        user_message: The raw user query string.
        context: Optional dict with keys:
            - ``session_id`` (str) — conversation session identifier.
            - ``vehicle_id`` (str | None) — vehicle code to scope queries.
            - ``image_base64`` (str | None) — attached image data.
            - ``user_id`` (str | None) — authenticated user ID.

    Returns:
        dict: Always contains ``"response"`` (str).  May also include
            ``"data"``, ``"sources"``, ``"slots"``, ``"warranty"``,
            ``"telemetry"``, or ``"appointment"`` keys depending on which
            agents handled the request.
    """
    if context is None:
        context = {}

    session_id = context.get("session_id", "unknown")
    vehicle_id = context.get("vehicle_id")

    logger.info(
        f"[Orchestrator] run_orchestrator called "
        f"session_id={session_id!r} vehicle_id={vehicle_id!r} "
        f"message_preview={user_message[:80]!r}"
    )

    llm_client = _build_llm_client()

    logger.debug(f"[Orchestrator] classifying intent message_preview={user_message[:80]!r}")
    intents = await classify_intent(user_message, llm_client)
    logger.info(f"[Orchestrator] intents={intents} message='{user_message[:80]}'")

    # Map intent → agent factory (instantiated fresh per request — stateless)
    intent_map = {
        "vehicle":   get_vehicle_agent,
        "warranty":  get_warranty_agent,
        "scheduler": get_scheduler_agent,
        "telemetry": get_telemetry_agent,
    }

    # Build coroutines for all matched structured agents
    tasks: list[asyncio.Task] = []
    matched_intents: list[str] = []
    for intent in intents:
        factory = intent_map.get(intent)
        if factory:
            logger.debug(f"[Orchestrator] spawning agent for intent={intent!r}")
            agent = factory()
            tasks.append(
                asyncio.create_task(agent.process_query(user_message, context))
            )
            matched_intents.append(intent)

    logger.debug(
        f"[Orchestrator] {len(tasks)} agent task(s) queued "
        f"intents={matched_intents}"
    )

    structured_responses: list[dict] = []
    if tasks:
        logger.debug("[Orchestrator] awaiting all agent tasks via asyncio.gather")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(
                    f"[Orchestrator] agent task[{idx}] failed intent={matched_intents[idx]!r} "
                    f"error={res}"
                )
            else:
                logger.debug(
                    f"[Orchestrator] agent task[{idx}] succeeded intent={matched_intents[idx]!r}"
                )
                structured_responses.append(res)

    logger.debug(
        f"[Orchestrator] {len(structured_responses)} structured response(s) received"
    )

    # If structured agents returned useful data, merge and return
    if structured_responses:
        logger.info(
            f"[Orchestrator] merging {len(structured_responses)} structured response(s)"
        )
        return _merge_responses(structured_responses)

    # RAG fallback for "general" intent with a knowledge question
    if intents == ["general"]:
        logger.info("[Orchestrator] no structured agents matched — trying RAG fallback")
        rag_agent = get_rag_agent()
        rag_response = await rag_agent.process_query(user_message, context)
        if rag_response.get("response") and "No relevant" not in rag_response["response"]:
            logger.info("[Orchestrator] RAG fallback produced a useful response")
            return rag_response
        logger.warning("[Orchestrator] RAG fallback returned no relevant docs")

    # Final fallback: conversational LLM
    logger.info("[Orchestrator] using conversational LLM as final fallback")
    return await run_agent(
        session_id=context.get("session_id", "default"),
        user_message=user_message,
        vehicle_id=context.get("vehicle_id"),
        image_base64=context.get("image_base64"),
        llm_client=llm_client,
    )


def _merge_responses(responses: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple agent response dicts into a single unified response.

    Combines text responses (deduplicated by relevance heuristic) and merges
    all non-text data keys.  When a ``telemetry`` agent response is present,
    bare vehicle-summary text from the vehicle agent is suppressed to avoid
    duplicate information.

    Args:
        responses: List of response dicts from individual agents.  Each dict
            is expected to have at minimum a ``"response"`` or ``"message"``
            key.

    Returns:
        dict: Merged result containing:
            - ``"response"`` (str) — concatenated text blocks separated by
              double newlines.
            - ``"data"`` (dict) — merged non-text data from all agents.
            - ``"sources"`` (list[str]) — sorted, deduplicated source labels.
    """
    logger.debug(f"_merge_responses: merging {len(responses)} responses")

    texts: list[str] = []
    merged_data: dict[str, Any] = {}
    sources: set[str] = set()

    # If telemetry agent responded with full diagnostics, skip plain vehicle
    # summary texts to avoid duplicate vehicle name/VIN lines.
    has_telemetry = any("telemetry" in r for r in responses if isinstance(r, dict))
    logger.debug(f"_merge_responses: has_telemetry={has_telemetry}")

    for r in responses:
        if not isinstance(r, dict):
            logger.warning(f"_merge_responses: skipping non-dict response type={type(r)}")
            continue

        text = r.get("response") or r.get("message", "")

        # Suppress the bare vehicle-agent summary when telemetry already covers it
        if has_telemetry and "telemetry" not in r and text and "telemetry" not in r:
            is_bare_summary = all(
                kw not in text.lower()
                for kw in ("fault", "warranty", "service", "appointment", "owner")
            )
            if is_bare_summary:
                logger.debug("_merge_responses: suppressing bare vehicle summary (telemetry present)")
                text = ""

        if text:
            texts.append(text)

        sources.update(r.get("sources", []))

        for key, value in r.items():
            if key in ("response", "message", "sources"):
                continue
            if key not in merged_data:
                merged_data[key] = value
            elif isinstance(value, list) and isinstance(merged_data[key], list):
                merged_data[key].extend(value)
            else:
                merged_data[key] = value

    merged = {
        "response": "\n\n".join(filter(None, texts)),
        "data":     merged_data,
        "sources":  sorted(sources),
    }
    logger.debug(
        f"_merge_responses: complete text_blocks={len(texts)} "
        f"sources={sorted(sources)} data_keys={list(merged_data.keys())}"
    )
    return merged
