"""
Telemetry Agent — app/agent/telemetry_agent.py

Specialist agent that retrieves real-time vehicle telemetry (odometer, fuel,
battery, engine temperature, oil life) and decodes any active OBD-II fault
codes (DTCs), then uses an LLM to produce a human-readable diagnostic summary.

Processing flow:
    1. Extract ``vehicle_id`` from the request context.
    2. Call ``telematics.get_vehicle_data`` to fetch sensor readings and
       resolve DTC codes from the ``cs03_vehicle`` and ``cs03_telematics`` DBs.
    3. Build a structured text summary with severity-coded DTC descriptions.
    4. Pass the summary to the LLM (``_diagnose``) for natural-language output.
    5. Return the LLM diagnosis plus the raw ``telemetry`` data dict.

DB schemas used:
    cs03_vehicle    — ``vehicles``, ``fault_codes`` tables
    cs03_telematics — ``dtc_codes`` table (for DTC descriptions)
"""
from __future__ import annotations

import logging
from typing import Any

from app.agent.gemini_client import GeminiClient
from app.config import settings
from app.services.telematics import get_vehicle_data, decode_dtc

logger = logging.getLogger(__name__)

_SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "unknown": "⚪"}


class TelemetryAgent:
    """Agent that produces real-time vehicle diagnostics from telemetry data.

    Uses the telematics service to fetch sensor readings and decoded DTC
    fault codes, then synthesises an LLM-generated diagnostic explanation.

    Attributes:
        _llm: Gemini LLM client used for generating diagnostic narratives.
    """

    def __init__(self) -> None:
        """Initialise TelemetryAgent with a Gemini LLM client."""
        self._llm = GeminiClient(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        logger.debug("TelemetryAgent: initialised with GeminiClient")

    async def process_query(
        self, user_message: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Retrieve vehicle telemetry and produce a diagnostic response.

        Args:
            user_message: The user's natural-language diagnostic query.
            context: Request context dict; must contain ``vehicle_id`` (str)
                for a meaningful response.

        Returns:
            dict[str, Any]: Contains:
                - ``"response"`` (str) — LLM-generated diagnostic narrative or
                  raw summary on LLM failure.
                - ``"telemetry"`` (dict) — raw telemetry data from the service.
                - ``"sources"`` (list[str]) — DB schemas consulted.

            If ``vehicle_id`` is absent, returns a prompt to provide one.
            On service/LLM errors, returns a graceful error message.
        """
        vehicle_id = context.get("vehicle_id")
        logger.info(f"[TelemetryAgent] process_query vehicle_id={vehicle_id!r}")

        if not vehicle_id:
            logger.warning("[TelemetryAgent] no vehicle_id in context — cannot retrieve diagnostics")
            return {
                "response": "Please provide a vehicle ID to retrieve diagnostics.",
                "sources": [],
            }

        try:
            logger.debug(f"[TelemetryAgent] fetching vehicle data vehicle_id={vehicle_id!r}")
            data = await get_vehicle_data(vehicle_id)

            if "error" in data:
                logger.warning(
                    f"[TelemetryAgent] telematics service returned error: {data['error']}"
                )
                return {"response": data["error"], "sources": []}

            logger.debug(
                f"[TelemetryAgent] vehicle data received "
                f"make={data.get('make')!r} model={data.get('model')!r} "
                f"active_dtc_count={len(data.get('active_dtcs', []))}"
            )

            # Build a human-readable summary
            lines = [
                f"Vehicle: {data['make']} {data['model']} {data['year']} (VIN: {data['vin']})",
                f"Odometer: {data['odometer']:,} km | Fuel: {data['fuel_level']}%"
                f" | Battery: {data['battery_voltage']}V",
                f"Engine temp: {data['engine_temp']}°C | Oil life: {data['oil_life']}%",
            ]

            if data["active_dtcs"]:
                decoded = data.get("decoded_dtcs", {})
                fault_lines = []
                for code in data["active_dtcs"]:
                    info = decoded.get(code, {})
                    sev  = info.get("severity", "unknown")
                    icon = _SEVERITY_EMOJI.get(sev, "⚪")
                    fault_lines.append(f"{icon} {code}: {info.get('desc', 'Unknown')}")
                    logger.debug(
                        f"[TelemetryAgent] DTC {code} severity={sev!r} desc={info.get('desc')!r}"
                    )
                lines.append("Active faults: " + " | ".join(fault_lines))
                logger.info(
                    f"[TelemetryAgent] {len(data['active_dtcs'])} active DTC(s) for "
                    f"vehicle_id={vehicle_id!r}"
                )
            else:
                lines.append("No active fault codes.")
                logger.info(
                    f"[TelemetryAgent] no active DTCs for vehicle_id={vehicle_id!r}"
                )

            raw_summary = "\n".join(lines)
            logger.debug(
                f"[TelemetryAgent] calling LLM for diagnosis vehicle_id={vehicle_id!r}"
            )
            diagnosis = await self._diagnose(user_message, raw_summary, data)

            logger.info(
                f"[TelemetryAgent] diagnosis complete vehicle_id={vehicle_id!r} "
                f"response_length={len(diagnosis)}"
            )
            return {
                "response": diagnosis,
                "telemetry": data,
                "sources": ["cs03_vehicle DB", "cs03_telematics DB"],
            }

        except Exception as exc:
            logger.error(f"[TelemetryAgent] error processing query for vehicle_id={vehicle_id!r}: {exc}")
            return {
                "response": "Unable to retrieve vehicle diagnostics. Please try again.",
                "sources": [],
            }

    async def _diagnose(self, user_question: str, raw_summary: str, data: dict) -> str:
        """Use the LLM to generate a diagnostic explanation from raw telemetry.

        Constructs a detailed prompt including the user's question and the
        structured telemetry summary, then calls the Gemini LLM.

        Args:
            user_question: The original user question to anchor the response.
            raw_summary: Pre-formatted string with key telemetry metrics and
                fault code descriptions.
            data: The full raw telemetry data dict (for potential future use
                in more detailed prompts).

        Returns:
            str: LLM-generated diagnostic narrative (3-5 sentences).
                Falls back to ``raw_summary`` on LLM error.
        """
        prompt = (
            "You are an expert automotive diagnostic assistant helping a customer service agent.\n"
            "Based on the vehicle telemetry data below, answer the customer's question clearly.\n"
            "Explain the likely root cause, severity, and recommended action in 3-5 sentences.\n"
            "Use simple language the customer can understand.\n\n"
            f"Customer question: {user_question}\n\n"
            f"Telemetry data:\n{raw_summary}"
        )
        logger.debug("[TelemetryAgent] _diagnose: sending LLM diagnosis prompt")
        try:
            resp = await self._llm.generate(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                system_prompt="You are a concise automotive diagnostic expert. Be direct and actionable."
            )
            text = resp.text.strip()
            logger.debug(f"[TelemetryAgent] _diagnose: LLM response length={len(text)}")
            return text
        except Exception as e:
            logger.warning(
                f"[TelemetryAgent] _diagnose: LLM diagnosis failed, returning raw summary: {e}"
            )
            return raw_summary


def get_telemetry_agent() -> TelemetryAgent:
    """Factory function — create a new stateless TelemetryAgent instance.

    Returns:
        TelemetryAgent: Fresh instance ready to process a single query.
    """
    logger.debug("get_telemetry_agent: creating new TelemetryAgent instance")
    return TelemetryAgent()
