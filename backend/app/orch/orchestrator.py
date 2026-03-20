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

    # 🔥 MULTI-INTENT
    intents = await classify_intent(user_message, llm_client)

    print(f"Orchestrator classified '{user_message}' → {intents}")

    responses = []

    # 🔹 Call agents based on intents
    if "vehicle" in intents:
        responses.append(await vehicle_agent.process_query(user_message, context))

    if "warranty" in intents:
        responses.append(await get_warranty_agent().process_query(user_message, context))

    if "scheduler" in intents:
        responses.append(await get_scheduler_agent().process_query(user_message, context))

    if "telemetry" in intents:
        responses.append(await get_telemetry_agent().process_query(user_message, context))

    # 🔹 If only general OR no structured response
    if not responses or intents == ["general"]:
        return await run_agent(
            session_id=context.get("session_id", "default"),
            user_message=user_message,
            llm_client=llm_client
        )

    # 🔥 Merge responses safely
    return merge_responses(responses)

# =========================
# 🔹 Response merger
# =========================
def merge_responses(responses: list) -> dict:
    final_texts = []
    merged_data = {}
    sources = set()

    for r in responses:
        if not isinstance(r, dict):
            continue

        # 🔹 Collect text
        if "response" in r:
            final_texts.append(r["response"])
        elif "message" in r:
            final_texts.append(r["message"])

        # 🔹 Merge structured data
        for key, value in r.items():
            if key in ["response", "message", "sources"]:
                continue

            if key not in merged_data:
                merged_data[key] = value
            else:
                # Handle list merging
                if isinstance(value, list) and isinstance(merged_data[key], list):
                    merged_data[key].extend(value)
                # Handle conflicts (keep latest)
                else:
                    merged_data[key] = value

        # 🔹 Merge sources
        sources.update(r.get("sources", []))

    return {
        "response": " | ".join(final_texts),
        "data": merged_data,
        "sources": list(sources)
    }