import anthropic
import json
from app.config import settings
from app.agent.tools import TOOL_DEFINITIONS, execute_tool
from app.agent.prompts import SYSTEM_PROMPT
from app.db.database import SessionLocal
from app.db.models import AgentSession
from loguru import logger

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

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
    image_base64: str = None
) -> dict:
    history = _load_history(session_id)

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
        "text": f"Vehicle ID: {vehicle_id or 'unknown'}\n\n{user_message}"
    })
    history.append({"role": "user", "content": content})

    tools_log = []
    final_text = ""

    while True:
        try:
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=history
            )

            history.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                final_text = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                break

            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.info(f"🔧 {block.name} → {block.input}")
                        result = await execute_tool(block.name, block.input)
                        tools_log.append({"tool": block.name, "result": result})
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })
                history.append({"role": "user", "content": results})
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            final_text = "Sorry, there was an error with the AI service. Please try again."
            break

    _save_history(session_id, history, vehicle_id)

    return {"response": final_text, "tools_used": tools_log, "session_id": session_id}