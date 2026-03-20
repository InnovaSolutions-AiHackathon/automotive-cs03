import json
import logging
import re
from typing import List

from app.agent.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

VALID_INTENTS = {"vehicle", "warranty", "scheduler", "telemetry", "general"}


async def classify_intent(user_message: str, llm_client: GeminiClient) -> List[str]:
    """
    Multi-intent classifier.
    Returns list of intents.
    """

    prompt = f"""
    You are an intent classifier for a vehicle assistant.

    Identify ALL relevant intents from this list:
    - vehicle
    - warranty
    - scheduler
    - telemetry
    - general

    Rules:
    - Multiple intents are allowed
    - If nothing matches, return ["general"]

    Examples:
    "Is my warranty expired?" → {{"intents": ["warranty"]}}
    "Book service and check warranty" → {{"intents": ["scheduler", "warranty"]}}
    "Car model and faults?" → {{"intents": ["vehicle", "telemetry"]}}
    "Tell me a joke" → {{"intents": ["general"]}}

    Return ONLY JSON:
    {{"intents": ["intent1", "intent2"]}}

    Query: "{user_message}"
    """

    try:
        response = await llm_client.generate(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            system_prompt="Return only valid JSON."
        )
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return ["general"]

    raw = response.text.strip()
    logger.debug(f"Raw classifier response: {raw}")

    # ✅ safer cleaning
    raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()

    try:
        parsed = json.loads(raw)

        intents = parsed.get("intents", [])
        intents = [i.lower() for i in intents if i.lower() in VALID_INTENTS]

        if not intents:
            return ["general"]

        logger.info(f"Classified intents: {intents} for message: {user_message}")
        return list(set(intents))

    except Exception as e:
        logger.error(f"Failed to parse classifier response: {e} | Raw: {raw}")
        return ["general"]