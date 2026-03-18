import json
import logging
from app.agent.gemini_client import GeminiClient
from app.config import settings
logger = logging.getLogger(__name__)

async def classify_intent(user_message: str, llm_client: GeminiClient) -> str:
    """
    Classify user queries into one of the predefined intents using Gemini.
    Returns: 'vehicle', 'warranty', 'scheduler', 'telemetry', or 'general'
    """

    prompt = f"""
    You are an intent classifier for a vehicle assistant.
    Classify the following user query into EXACTLY one of these categories:
    - vehicle (questions about vehicle details, models, specs, ownership)
    - warranty (questions about warranty, coverage, guarantee, expiry, validity)
    - scheduler (questions about booking, scheduling, appointments, service times)
    - telemetry (questions about diagnostics, performance, vehicle data, sensors)
    - general (anything else)

    Examples:
    "Is my warranty expired?" → {{"intent": "warranty"}}
    "Book me a service appointment" → {{"intent": "scheduler"}}
    "My car is making noise" → {{"intent": "telemetry"}}
    "Tell me a joke" → {{"intent": "general"}}
    "What model is my bike?" → {{"intent": "vehicle"}}

    Return ONLY a valid JSON object with a single key 'intent'.
    Do not add any text before or after the JSON.
    Query: "{user_message}"
    """

    response = await llm_client.generate(
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        system_prompt="You are a strict intent classification assistant. Always respond with valid JSON only."
    )

    raw_text = response.text.strip()
    print(f"Raw classifier response: {raw_text}")

    # Fallback: handle plain text responses like 'warranty'
    if raw_text.lower() in ["vehicle", "warranty", "scheduler", "telemetry", "general"]:
        print(f"Classified intent (fallback): {raw_text.lower()} for message: {user_message}")
        return raw_text.lower()

    try:
        parsed = json.loads(raw_text)
        intent = parsed.get("intent", "general").lower()
        print(f"Classified intent: {intent} for message: {user_message}")
        return intent
    except Exception as e:
        print(f"Failed to parse classifier response: {e} | Raw: {raw_text}")
        return "general"
