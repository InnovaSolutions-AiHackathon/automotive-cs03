"""
General-Purpose Conversational Agent — app/agent/askAI.py

Provides the final-fallback LLM conversation handler used by the orchestrator
when no specialist agent produces a structured response.

Responsibilities:
    - Load per-session conversation history from the ``cs03_agent`` DB.
    - Append the new user message (and optional image) to the history.
    - Send the full history plus system prompt and tool definitions to the
      Gemini LLM.
    - Persist the updated history back to the DB.
    - Return the LLM's text response to the caller.

Session history is stored as JSON in the ``agent_sessions`` table, keyed by
``session_id``, allowing multi-turn conversations to maintain context across
API requests.

DB schema used:
    cs03_agent — ``agent_sessions`` table via
    ``app.db.schemas.agent_session.AgentSession``.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from loguru import logger

from app.agent.gemini_client import GeminiClient
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DEFINITIONS
from app.config import settings
from app.db.database import AgentSession_SM
from app.db.schemas.agent_session import AgentSession


# ---------------------------------------------------------------------------
# Session history helpers
# ---------------------------------------------------------------------------

def _load_history(session_id: str) -> list:
    """Load conversation history for a session from the ``cs03_agent`` DB.

    Args:
        session_id: The unique session identifier string.

    Returns:
        list: The parsed conversation history as a list of message dicts.
            Returns an empty list if no history exists or on DB error.
    """
    logger.debug(f"_load_history: loading history for session_id={session_id!r}")
    db = AgentSession_SM()
    try:
        row = db.query(AgentSession).filter_by(session_id=session_id).first()
        if row and row.history_json:
            history = json.loads(row.history_json)
            logger.debug(
                f"_load_history: loaded {len(history)} turn(s) "
                f"for session_id={session_id!r}"
            )
            return history
        logger.debug(f"_load_history: no existing history for session_id={session_id!r}")
        return []
    except Exception as exc:
        logger.warning(
            f"_load_history: could not load history for session_id={session_id!r}: {exc}"
        )
        return []
    finally:
        db.close()


def _save_history(session_id: str, history: list, vehicle_code: str | None = None) -> None:
    """Persist conversation history for a session to the ``cs03_agent`` DB.

    Creates a new row if one does not exist for ``session_id``; otherwise
    updates the existing row.  Also updates ``vehicle_code`` on the row if
    provided.

    Args:
        session_id: The unique session identifier string.
        history: The current full conversation history list to serialise.
        vehicle_code: Optional vehicle code to associate with the session.
            If ``None``, the existing ``vehicle_code`` on the row is preserved.

    Returns:
        None
    """
    logger.debug(
        f"_save_history: saving {len(history)} turn(s) "
        f"for session_id={session_id!r} vehicle_code={vehicle_code!r}"
    )
    db = AgentSession_SM()
    try:
        row = db.query(AgentSession).filter_by(session_id=session_id).first()
        if row:
            row.history_json = json.dumps(history)
            row.vehicle_code = vehicle_code or row.vehicle_code
            logger.debug(f"_save_history: updated existing session session_id={session_id!r}")
        else:
            db.add(AgentSession(
                session_id=session_id,
                vehicle_code=vehicle_code,
                history_json=json.dumps(history),
            ))
            logger.debug(f"_save_history: created new session session_id={session_id!r}")
        db.commit()
    except Exception as exc:
        logger.error(
            f"_save_history: could not save history for session_id={session_id!r}: {exc}"
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Main agent entrypoint
# ---------------------------------------------------------------------------

async def run_agent(
    session_id: str,
    user_message: str,
    vehicle_id: str | None = None,
    image_base64: str | None = None,
    llm_client: GeminiClient | None = None,
) -> dict[str, Any]:
    """Run the general-purpose conversational LLM agent for a single turn.

    Loads session history, appends the new user message, calls the LLM, and
    persists the updated history.  Handles optional image attachments.

    Args:
        session_id: Unique conversation session identifier.  Used to load
            and save multi-turn history in ``cs03_agent``.
        user_message: The user's text message for this turn.
        vehicle_id: Optional vehicle code; stored on the session row for
            context retrieval.
        image_base64: Optional base-64 encoded JPEG image to include in the
            LLM message content.
        llm_client: Optional pre-configured ``GeminiClient`` instance.  If
            ``None``, a new client is created from application settings.

    Returns:
        dict[str, Any]: Contains:
            - ``"response"`` (str) — the LLM's text reply, or an error
              message if the LLM call fails.
            - ``"session_id"`` (str) — the session ID echoed back.
    """
    logger.info(
        f"run_agent: session_id={session_id!r} vehicle_id={vehicle_id!r} "
        f"has_image={bool(image_base64)} "
        f"message_preview={user_message[:80]!r}"
    )

    if llm_client is None:
        logger.debug("run_agent: no llm_client provided — creating new GeminiClient")
        llm_client = GeminiClient(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )

    logger.debug(f"run_agent: loading history for session_id={session_id!r}")
    history = _load_history(session_id)
    logger.debug(f"run_agent: loaded {len(history)} existing turn(s)")

    content: list[dict] = []
    if image_base64:
        logger.debug("run_agent: attaching image to message content")
        content.append({
            "type":   "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64},
        })
    content.append({"type": "text", "text": user_message.strip()})

    history.append({"role": "user", "content": content})
    logger.debug(f"run_agent: appended user turn, history now {len(history)} turn(s)")

    final_text = ""
    try:
        logger.debug(f"run_agent: calling LLM generate session_id={session_id!r}")
        response = await llm_client.generate(
            messages=history,
            system_prompt=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
        )

        logger.debug(f"LLM raw response type={type(response)}")

        text = response.text.strip()
        text = re.sub(r'^["\']|["\']$', "", text)   # strip outer quotes
        text = re.sub(r"#+\s*", "", text)            # remove markdown headings

        logger.debug(
            f"run_agent: LLM response received length={len(text)} "
            f"session_id={session_id!r}"
        )

        history.append({"role": "assistant", "content": [{"type": "text", "text": text}]})

        if response.candidates and response.candidates[0].finish_reason == "STOP":
            final_text = text
            logger.debug(
                f"run_agent: finish_reason=STOP session_id={session_id!r}"
            )
        else:
            finish_reason = (
                response.candidates[0].finish_reason
                if response.candidates else "unknown"
            )
            logger.warning(
                f"run_agent: unexpected finish_reason={finish_reason!r} "
                f"session_id={session_id!r}"
            )

    except Exception as exc:
        logger.error(
            f"run_agent: LLM generation error session_id={session_id!r}: {exc}"
        )
        final_text = "Sorry, there was an error with the AI service. Please try again."

    logger.debug(
        f"run_agent: saving history {len(history)} turn(s) "
        f"session_id={session_id!r}"
    )
    _save_history(session_id, history, vehicle_id)

    logger.info(
        f"run_agent: complete session_id={session_id!r} "
        f"response_length={len(final_text)}"
    )
    return {"response": final_text, "session_id": session_id}
