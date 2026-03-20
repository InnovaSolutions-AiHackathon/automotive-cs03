"""
Intent Classifier — app/agent/classify_intent.py

Uses a Gemini LLM call to perform multi-label intent classification on a
user query.  Returns a list of one or more intent strings from the set:

    ``vehicle``, ``warranty``, ``scheduler``, ``telemetry``, ``general``

Behaviour:
    - Multiple intents may be returned for compound queries.
    - Any unrecognised intent label from the LLM is filtered out.
    - If the LLM call fails or returns unparseable JSON, ``["general"]`` is
      returned as a safe fallback.
    - Markdown code fences are stripped from the LLM output before parsing.

DB schemas used:
    None — this module is stateless and makes only LLM API calls.
"""
import json
import logging
import re
from typing import List

from app.agent.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

VALID_INTENTS = {"vehicle", "warranty", "scheduler", "telemetry", "general"}


async def classify_intent(user_message: str, llm_client: GeminiClient) -> List[str]:
    """Classify the user's message into one or more structured intents.

    Sends a structured prompt to the Gemini LLM requesting a JSON response
    with an ``intents`` array.  Validates and filters the returned labels
    against ``VALID_INTENTS``.

    Args:
        user_message: The raw natural-language query from the user.
        llm_client: An initialised ``GeminiClient`` instance to use for the
            classification call.

    Returns:
        List[str]: A deduplicated list of intent strings, e.g.
            ``["warranty", "scheduler"]``.  Falls back to ``["general"]``
            on any error or empty result.

    Raises:
        Does not raise — exceptions are caught and logged; ``["general"]``
        is returned in all failure cases.
    """
    logger.info(
        f"classify_intent: classifying message_preview={user_message[:80]!r}"
    )

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

    logger.debug("classify_intent: sending classification prompt to LLM")
    try:
        response = await llm_client.generate(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            system_prompt="Return only valid JSON."
        )
    except Exception as e:
        logger.error(f"classify_intent: Gemini API error: {e}")
        return ["general"]

    raw = response.text.strip()
    logger.debug(f"classify_intent: raw classifier response: {raw}")

    # Strip markdown code fences if present
    raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    logger.debug(f"classify_intent: cleaned response: {raw}")

    try:
        parsed = json.loads(raw)

        intents = parsed.get("intents", [])
        logger.debug(f"classify_intent: raw intents from LLM: {intents}")

        intents = [i.lower() for i in intents if i.lower() in VALID_INTENTS]

        if not intents:
            logger.warning(
                "classify_intent: no valid intents after filtering — defaulting to ['general']"
            )
            return ["general"]

        deduplicated = list(set(intents))
        logger.info(
            f"classify_intent: classified intents={deduplicated} "
            f"for message_preview={user_message[:80]!r}"
        )
        return deduplicated

    except Exception as e:
        logger.error(
            f"classify_intent: failed to parse classifier response: {e} | raw={raw!r}"
        )
        return ["general"]
