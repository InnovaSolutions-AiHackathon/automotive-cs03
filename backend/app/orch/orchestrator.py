from multiprocessing import context

from app.agent.askAI import run_agent
from app.agent.vehicle_agent import get_vehicle_agent
from app.agent.warranty_agent import get_warranty_agent
from app.agent.scheduler_agent import get_scheduler_agent
from app.agent.telemetry_agent import get_telemetry_agent
from app.agent.gemini_client import GeminiClient
from app.agent.classify_intent import classify_intent
from app.config import settings

vehicle_agent = get_vehicle_agent()

async def run_orchestrator(user_message: str, context: dict = None) -> dict:
    if context is None:
        context = {}

    llm_client = GeminiClient(api_key=settings.GEMINI_API_KEY)

    # Classify intent
    intent = await classify_intent(user_message, llm_client)
    #intent = "vehicle"  # For testing, hardcode to vehicle intent

    print(f"Orchestrator classified user message '{user_message}' with intent: {intent}")

    if intent == "vehicle":
        return await vehicle_agent.process_query(user_message, context)
    if intent == "warranty":
        return await get_warranty_agent().process_query(user_message, context)
    elif intent == "scheduler":
        return await get_scheduler_agent().process_query(user_message, context)
    elif intent == "telemetry":
        return await get_telemetry_agent().process_query(user_message, context)
    else:
        return await run_agent(
            session_id=context.get("session_id", "default"),
            user_message=user_message,
            llm_client=llm_client
        )
