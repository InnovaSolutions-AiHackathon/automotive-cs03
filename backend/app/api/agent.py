"""
Agent API Router — app/api/agent.py

Exposes the single ``POST /api/agent/ask`` endpoint that acts as the
front-door for the AI Copilot.  All incoming chat messages are forwarded to
the multi-agent orchestrator (``run_orchestrator``), which classifies intent
and dispatches to the appropriate specialist agent(s).

Responsibilities:
    - Validate that the ``message`` field is non-empty.
    - Assemble a context dict from the optional request fields
      (session_id, vehicle_id, image_base64, user_id).
    - Delegate to ``app.orch.orchestrator.run_orchestrator``.
    - Return the orchestrator response dict directly to the caller.

DB schemas used:
    Indirectly touches all schemas via the orchestrator and its agents.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.orch.orchestrator import run_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


class AskRequest(BaseModel):
    """Request body for the ``/ask`` endpoint.

    Attributes:
        session_id: Unique identifier for the conversation session.
            Used to persist and retrieve chat history in ``cs03_agent``.
        message: The user's natural-language query (required, must be non-empty).
        vehicle_id: Optional vehicle code used to scope agent queries to a
            specific vehicle (e.g. ``'VH-001'``).
        image_base64: Optional base-64 encoded image attached to the message
            (e.g. a photo of a dashboard warning light).
        user_id: Optional authenticated user ID, used by VehicleAgent to
            resolve vehicles belonging to the user when no ``vehicle_id`` is
            given.
    """

    session_id: str
    message: str
    vehicle_id: Optional[str] = None
    image_base64: Optional[str] = None
    user_id: Optional[str] = None


@router.post("/ask")
async def query_handler(payload: AskRequest) -> dict:
    """Handle an AI Copilot chat query.

    Validates the incoming message, builds a context dictionary, and
    delegates to the multi-agent orchestrator.

    Args:
        payload: The parsed ``AskRequest`` body containing the session ID,
            message, and optional vehicle/user context.

    Returns:
        dict: The orchestrator response, which always contains at minimum
            ``{"response": str}``.  May also include ``"data"``, ``"sources"``,
            ``"slots"``, ``"warranty"``, ``"telemetry"``, or ``"appointment"``
            keys depending on which agents responded.

    Raises:
        HTTPException: 400 if ``payload.message`` is blank or whitespace-only.
    """
    logger.info(
        f"POST /api/agent/ask session_id={payload.session_id!r} "
        f"vehicle_id={payload.vehicle_id!r} user_id={payload.user_id!r} "
        f"has_image={bool(payload.image_base64)} "
        f"message_preview={payload.message[:80]!r}"
    )

    if not payload.message.strip():
        logger.warning(
            f"POST /api/agent/ask rejected: empty message session_id={payload.session_id!r}"
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    context = {
        "session_id": payload.session_id,
        "vehicle_id": payload.vehicle_id,
        "image_base64": payload.image_base64,
        "user_id": payload.user_id,
    }
    logger.debug(f"query_handler: built context keys={list(context.keys())}")

    logger.debug(f"query_handler: delegating to run_orchestrator session_id={payload.session_id!r}")
    result = await run_orchestrator(payload.message, context)

    response_preview = str(result.get("response", ""))[:120]
    logger.info(
        f"POST /api/agent/ask completed session_id={payload.session_id!r} "
        f"response_preview={response_preview!r}"
    )
    return result
