import json
import asyncio
import re
from loguru import logger
from app.config import settings
from app.agent.tools import TOOL_DEFINITIONS, execute_tool
from app.agent.prompts import SYSTEM_PROMPT
from app.db.database import SessionLocal
from app.db.models import AgentSession
from app.agent.gemini_client import GeminiClient


def _load_history(session_id: str) -> list:
    db = SessionLocal()
    try:
        row = db.query(AgentSession).filter_by(session_id=session_id).first()
        return json.loads(row.history_json) if row and row.history_json else []
    finally:
        db.close()


def _save_history(session_id: str, history: list, vehicle_id: str = None):
    db = SessionLocal()
    try:
        row = db.query(AgentSession).filter_by(session_id=session_id).first()
        if row:
            row.history_json = json.dumps(history)
        else:
            db.add(AgentSession(
                session_id=session_id,
                vehicle_id=vehicle_id,
                history_json=json.dumps(history)
            ))
        db.commit()
    finally:
        db.close()


async def run_agent(
    session_id: str,
    user_message: str,
    vehicle_id: str = None,
    image_base64: str = None,
    llm_client=None
) -> dict:
    if llm_client is None:
        llm_client = GeminiClient(api_key=settings.GEMINI_API_KEY)

    history = _load_history(session_id)

    # Build user content
    content = []
    if image_base64:
        content.append({
            "type": "image",
            "source": {"type": "base64",
                       "media_type": "image/jpeg",
                       "data": image_base64}
        })
    content.append({
        "type": "text",
        "text": user_message.strip()
    })
    
    history.append({"role": "user", "content": content})

    tools_log = []
    final_text = ""

    try:
        response = await llm_client.generate(
            messages=history,
            system_prompt=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS
        )

        logger.info(f"Gemini raw response: {response}")

        # Clean the response: remove markdown headings and outer quotes
        text = response.text.strip()
        text = re.sub(r'^["\']|["\']$', '', text)  # strip leading/trailing quotes
        text = re.sub(r'#+\s*', '', text)          # remove markdown headings

        # Store assistant reply
        history.append({
            "role": "assistant",
            "content": [{"type": "text", "text": text}]
        })

        # Use candidate finish_reason if available
        if response.candidates and response.candidates[0].finish_reason == "STOP":
            final_text = text

    except Exception as e:
        logger.error(f"LLM error: {e}")
        final_text = "Sorry, there was an error with the AI service. Please try again."

    _save_history(session_id, history, vehicle_id)

    return {"response": final_text, "tools_used": tools_log, "session_id": session_id}
