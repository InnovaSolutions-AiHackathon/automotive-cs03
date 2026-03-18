from app.agent.claude_agent import run_agent
from app.agent.warranty_agent import get_warranty_agent
from app.agent.scheduler_agent import get_scheduler_agent
from app.agent.telemetry_agent import get_telemetry_agent

async def run_orchestrator(user_message: str, context: dict = None) -> dict:
    """
    Routes user messages to the correct agent.
    """
    if context is None:
        context = {}

    lower_msg = user_message.lower()

    print(f"Orchestrator received message: {lower_msg}")

    if "warranty" in lower_msg:
        # call warranty agent
        return await get_warranty_agent().process_query(user_message, context)

    elif "schedule" in lower_msg:
        # call scheduler agent
        return await get_scheduler_agent().process_query(user_message, context)

    elif "telemetry" in lower_msg:
        # call telemetry agent
        return await get_telemetry_agent().process_query(user_message, context)

    else:
        # Default → Claude agent (RAG + tools)
        return await run_agent(
            session_id=context.get("session_id", "default"),
            user_message=user_message,
            vehicle_id=context.get("vehicle_id")
        )
