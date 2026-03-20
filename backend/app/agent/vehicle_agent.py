"""
Vehicle Agent — app/agent/vehicle_agent.py

Specialist agent responsible for answering questions about a specific vehicle's
attributes, fault codes, warranty records, and service history.

Processing flow:
    1. Resolve the target vehicle from the context (by vehicle_code or user_id).
    2. Detect relevant data fields using rule-based keyword matching; fall back
       to an LLM extraction call if no fields are detected.
    3. Fetch the required data from the appropriate DB schema(s).
    4. Use the LLM to compose a natural-language response from the raw facts.
    5. Return a default odometer/fuel/temp summary if no specific fields matched.

DB schemas used:
    cs03_vehicle   — ``vehicles``, ``customers``, ``fault_codes`` tables
    cs03_warranty  — ``warranty_records`` table
    cs03_scheduler — ``service_appointments`` table
"""
import json
import logging
import re
from typing import Dict, Any, List

from app.db.database import SessionLocal, WarrantySession, SchedulerSession
from app.db.schemas.vehicle import Vehicle, Customer, FaultCode
from app.db.schemas.warranty import WarrantyRecord
from app.db.schemas.scheduler import ServiceAppointment
from app.agent.gemini_client import GeminiClient
from app.config import settings

logger = logging.getLogger(__name__)

VALID_FIELDS = {"model", "make", "year", "owner", "faults", "warranty", "service", "summary"}


class VehicleAgent:
    """Agent that answers vehicle-specific queries by fetching DB data and composing LLM responses.

    Attributes:
        session_factory: SQLAlchemy session factory for the ``cs03_vehicle`` schema.
        llm_client: Gemini LLM client for field detection and response composition.
    """

    def __init__(self):
        """Initialise VehicleAgent with vehicle DB session factory and LLM client."""
        self.session_factory = SessionLocal
        self.llm_client = GeminiClient(api_key=settings.GEMINI_API_KEY)
        logger.debug("VehicleAgent: initialised with SessionLocal and GeminiClient")

    async def process_query(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a vehicle-related query and return a structured response.

        Resolves the vehicle, detects data fields, fetches relevant DB data,
        and composes a natural-language answer via LLM.

        Args:
            user_message: The user's natural-language query string.
            context: Request context dict with optional keys:
                - ``vehicle_id`` (str) — specific vehicle code to query.
                - ``user_id`` (str) — user ID to resolve vehicle by owner.

        Returns:
            Dict[str, Any]: Always contains ``"response"`` (str) and
                ``"sources"`` (list[str]).  If vehicle resolution requires
                selection (multiple vehicles or single confirmation), returns
                ``"message"`` and ``"vehicles"`` instead.
        """
        vehicle_code = context.get("vehicle_id")
        user_id = context.get("user_id")

        logger.info(
            f"[VehicleAgent] process_query vehicle_code={vehicle_code!r} "
            f"user_id={user_id!r} message_preview={user_message[:80]!r}"
        )

        with self.session_factory() as vdb, \
             WarrantySession() as wdb, \
             SchedulerSession() as sdb:

            # Resolve vehicle
            logger.debug(
                f"[VehicleAgent] resolving vehicle vehicle_code={vehicle_code!r} "
                f"user_id={user_id!r}"
            )
            vehicle = self._resolve_vehicle(vdb, vehicle_code, user_id)
            if isinstance(vehicle, dict):  # early response case
                logger.info(
                    f"[VehicleAgent] early return from _resolve_vehicle keys={list(vehicle.keys())}"
                )
                return vehicle

            logger.debug(
                f"[VehicleAgent] vehicle resolved vehicle_code={vehicle.vehicle_code!r} "
                f"make={vehicle.make!r} model={vehicle.model!r}"
            )

            # Detect fields
            logger.debug("[VehicleAgent] running rule-based field detection")
            fields = self._detect_fields_rule(user_message)
            if not fields:
                logger.warning(
                    "[VehicleAgent] rule-based detection found no fields — falling back to LLM"
                )
                fields = await self._detect_fields_llm(user_message)

            fields = list(set(fields) & VALID_FIELDS)
            logger.info(f"[VehicleAgent] Fields: {fields}")

            # Fetch data — pass all three sessions
            logger.debug(f"[VehicleAgent] fetching data for fields={fields}")
            data = self._fetch_data(vdb, wdb, sdb, vehicle, fields)
            logger.debug(f"[VehicleAgent] fetched {len(data)} data item(s)")

            # Build response
            if not data:
                logger.warning(
                    f"[VehicleAgent] no data fetched for fields={fields} — returning default summary"
                )
                return self._default_summary(vehicle)

            # Use LLM to compose a natural language response
            logger.debug("[VehicleAgent] composing LLM response from fetched data")
            response_text = await self._compose_response(user_message, vehicle, data)

            logger.info(
                f"[VehicleAgent] response composed length={len(response_text)} "
                f"vehicle_code={vehicle.vehicle_code!r}"
            )
            return {
                "response": response_text,
                "sources": ["cs03_vehicle DB", "cs03_warranty DB", "cs03_scheduler DB"]
            }

    # =========================
    # Vehicle resolution
    # =========================
    def _resolve_vehicle(self, db, vehicle_code, user_id):
        """Look up the target vehicle from the database.

        If ``vehicle_code`` is provided, queries directly by code.
        Otherwise resolves by ``user_id`` (owner lookup) and returns a vehicle
        selection prompt when the result is ambiguous.

        Args:
            db: Active SQLAlchemy session for ``cs03_vehicle``.
            vehicle_code: Direct vehicle identifier, or ``None``.
            user_id: Authenticated user ID for owner-based lookup, or ``None``.

        Returns:
            Vehicle | dict: The ``Vehicle`` ORM object if uniquely resolved,
                or a dict with ``"response"``/``"message"`` for early returns.
        """
        if vehicle_code:
            logger.debug(f"_resolve_vehicle: querying by vehicle_code={vehicle_code!r}")
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_code == vehicle_code).first()
            if not vehicle:
                logger.warning(f"_resolve_vehicle: no vehicle found vehicle_code={vehicle_code!r}")
                return {"response": f"No vehicle found with code {vehicle_code}.", "sources": ["MySQL DB"]}
            logger.debug(f"_resolve_vehicle: found vehicle vehicle_code={vehicle_code!r}")
            return vehicle

        logger.debug(f"_resolve_vehicle: querying by user_id={user_id!r}")
        vehicles = db.query(Vehicle).filter(Vehicle.customer_id == user_id).all()

        if not vehicles:
            logger.warning(f"_resolve_vehicle: no vehicles found for user_id={user_id!r}")
            return {"response": "No vehicles found for your account.", "sources": ["MySQL DB"]}

        vehicle_list = [{"code": v.vehicle_code, "name": f"{v.make} {v.model}"} for v in vehicles]

        vehicle_list = [
            {"vehicle_code": v.vehicle_code, "make": v.make, "model": v.model, "year": v.year}
            for v in vehicles
        ]

        logger.info(
            f"_resolve_vehicle: found {len(vehicles)} vehicle(s) for user_id={user_id!r}"
        )

        if len(vehicles) == 1:
            return {
                "message": "We found your vehicle. Please confirm if this is the one.",
                "vehicles": vehicle_list,
            }

        return {
            "message": "You have multiple vehicles. Please select one.",
            "vehicles": vehicle_list,
        }

    # =========================
    # Rule-based detection
    # =========================
    def _detect_fields_rule(self, msg: str) -> List[str]:
        """Detect vehicle data fields from a message using keyword matching.

        Args:
            msg: The user's message string (will be lowercased internally).

        Returns:
            List[str]: List of matched field names from ``VALID_FIELDS``.
                May be empty if no keywords match.
        """
        msg = msg.lower()
        mapping = {
            "summary":  ["status", "details", "detail", "info", "overview", "summary", "all", "everything", "show me"],
            "model":    ["model"],
            "make":     ["make", "brand"],
            "year":     ["year", "age"],
            "owner":    ["owner", "customer", "driver"],
            "faults":   ["fault", "dtc", "issue", "problem", "error", "code", "diagnostic"],
            "warranty": ["warranty", "coverage", "covered"],
            "service":  ["service", "appointment", "repair", "maintenance"],
        }

        detected = [
            field for field, keywords in mapping.items()
            if any(k in msg for k in keywords)
        ]
        logger.debug(f"_detect_fields_rule: detected fields={detected}")
        return detected

    # =========================
    # LLM fallback
    # =========================
    async def _detect_fields_llm(self, user_message: str) -> List[str]:
        """Use the LLM to extract vehicle data fields when rule-based detection fails.

        Sends a structured prompt and parses the ``{"fields": [...]}`` JSON
        response.

        Args:
            user_message: The user's original query string.

        Returns:
            List[str]: Field names extracted by the LLM.  Returns ``[]`` on
                any error.
        """
        logger.debug(
            f"_detect_fields_llm: sending field extraction prompt "
            f"message_preview={user_message[:80]!r}"
        )
        prompt = (
            "Extract vehicle-related fields from the query.\n"
            "Allowed fields: model, make, year, owner, faults, warranty, service.\n"
            'Return ONLY JSON: {"fields": ["field1"]}'
        )

        try:
            response = await self.llm_client.generate(
                messages=[{"role": "user", "content": [{"type": "text", "text": user_message}]}],
                system_prompt=prompt
            )

            raw = self._clean_json(response.text)
            logger.debug(f"_detect_fields_llm: raw LLM response cleaned={raw!r}")
            parsed = json.loads(raw)

            fields = parsed.get("fields", [])
            logger.info(f"_detect_fields_llm: LLM detected fields={fields}")
            return fields

        except Exception as e:
            logger.error(f"_detect_fields_llm: LLM field detection failed: {e}")
            return []

    # =========================
    # Data fetching
    # =========================
    def _fetch_data(self, vdb, wdb, sdb, vehicle, fields: List[str]) -> List[str]:
        """Fetch vehicle-related facts from the database for the given fields.

        Queries ``cs03_vehicle``, ``cs03_warranty``, and ``cs03_scheduler``
        as needed based on the requested fields list.

        Args:
            vdb: Active SQLAlchemy session for ``cs03_vehicle``.
            wdb: Active SQLAlchemy session for ``cs03_warranty``.
            sdb: Active SQLAlchemy session for ``cs03_scheduler``.
            vehicle: The resolved ``Vehicle`` ORM instance.
            fields: List of field names to fetch data for.

        Returns:
            List[str]: Human-readable fact strings (e.g. ``"Model: Camry"``).
                ``"summary"`` field expands to all other fields.
        """
        results = []

        # "summary" expands to all fields
        if "summary" in fields:
            logger.debug("_fetch_data: 'summary' field detected — expanding to all fields")
            fields = list(VALID_FIELDS - {"summary"})

        if "model" in fields:
            results.append(f"Model: {vehicle.model}")

        if "make" in fields:
            results.append(f"Make: {vehicle.make}")

        if "year" in fields:
            results.append(f"Year: {vehicle.year}")

        if "owner" in fields:
            logger.debug(
                f"_fetch_data: querying customer for vehicle.customer_id={vehicle.customer_id}"
            )
            customer = vdb.query(Customer).filter(Customer.id == vehicle.customer_id).first()
            results.append(f"Owner: {customer.name if customer else 'Unknown'}")

        if "faults" in fields:
            logger.debug(
                f"_fetch_data: querying fault codes for vehicle.id={vehicle.id}"
            )
            faults = vdb.query(FaultCode).filter(
                FaultCode.vehicle_id == vehicle.id, FaultCode.resolved == False
            ).all()
            codes = [f.dtc_code for f in faults]
            logger.debug(f"_fetch_data: found {len(codes)} active fault code(s)")
            results.append(f"Active fault codes: {codes if codes else 'None'}")

        if "warranty" in fields:
            logger.debug(
                f"_fetch_data: querying warranty records for vehicle_code={vehicle.vehicle_code!r}"
            )
            warranties = wdb.query(WarrantyRecord).filter(
                WarrantyRecord.vehicle_code == vehicle.vehicle_code
            ).all()
            logger.debug(f"_fetch_data: found {len(warranties)} warranty record(s)")
            if warranties:
                results.append(
                    "Warranty: " + ", ".join(
                        f"{w.coverage_type} until {w.end_date}" for w in warranties
                    )
                )
            else:
                results.append("Warranty: No warranty records found")

        if "service" in fields:
            logger.debug(
                f"_fetch_data: querying last 5 appointments for vehicle_code={vehicle.vehicle_code!r}"
            )
            appts = sdb.query(ServiceAppointment).filter(
                ServiceAppointment.vehicle_code == vehicle.vehicle_code
            ).order_by(ServiceAppointment.scheduled_date.desc()).limit(5).all()
            logger.debug(f"_fetch_data: found {len(appts)} appointment(s)")
            if appts:
                results.append(
                    "Service history: " + ", ".join(
                        f"{a.service_type} on {a.scheduled_date} [{a.status}]" for a in appts
                    )
                )
            else:
                results.append("Service: No appointments found")

        logger.debug(f"_fetch_data: returning {len(results)} fact string(s)")
        return results

    # =========================
    # LLM natural language composer
    # =========================
    async def _compose_response(self, user_question: str, vehicle, data: List[str]) -> str:
        """Compose a natural-language answer from raw DB facts using the LLM.

        Builds a prompt with vehicle facts and sends it to the LLM to generate
        a concise, customer-friendly response.  Falls back to joining the raw
        fact strings on LLM error.

        Args:
            user_question: The original user query to focus the answer on.
            vehicle: The resolved ``Vehicle`` ORM instance.
            data: List of fact strings assembled by ``_fetch_data``.

        Returns:
            str: A 2-4 sentence natural-language answer, or the raw fact
                strings joined by newlines on LLM failure.
        """
        facts = "\n".join(f"- {d}" for d in data)
        prompt = (
            "You are an automotive customer service agent assistant.\n"
            "Given the following vehicle facts from the database, answer the customer's question "
            "in 2-4 clear, helpful sentences. Be direct and actionable. "
            "Do NOT repeat all facts — focus on what is relevant to the question.\n\n"
            f"Customer question: {user_question}\n\n"
            f"Vehicle: {vehicle.make} {vehicle.model} {vehicle.year} ({vehicle.vehicle_code})\n"
            f"Facts:\n{facts}"
        )
        logger.debug(
            f"_compose_response: sending composition prompt "
            f"vehicle_code={vehicle.vehicle_code!r} fact_count={len(data)}"
        )
        try:
            resp = await self.llm_client.generate(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                system_prompt="You are a concise automotive support assistant. Answer in plain English."
            )
            text = resp.text.strip()
            logger.debug(
                f"_compose_response: LLM response received length={len(text)}"
            )
            return text
        except Exception as e:
            logger.warning(
                f"_compose_response: LLM compose failed, falling back to raw facts: {e}"
            )
            return "\n".join(data)

    # =========================
    # Default fallback
    # =========================
    def _default_summary(self, vehicle) -> Dict[str, Any]:
        """Build a minimal vehicle summary when no specific fields were requested.

        Assembles key telemetry values (odometer, fuel, temperature, oil) that
        are always available without additional DB queries.

        Args:
            vehicle: The resolved ``Vehicle`` ORM instance.

        Returns:
            Dict[str, Any]: Dict with ``"response"`` (pipe-separated summary
                string) and ``"sources"`` (list).
        """
        parts = [f"{vehicle.make} {vehicle.model} ({vehicle.year})"]
        if vehicle.vin:
            parts.append(f"VIN: {vehicle.vin}")
        if vehicle.odometer is not None:
            parts.append(f"Odometer: {vehicle.odometer:,} km")
        if vehicle.fuel_level is not None:
            parts.append(f"Fuel: {vehicle.fuel_level}%")
        if vehicle.engine_temp is not None:
            parts.append(f"Engine temp: {vehicle.engine_temp}°C")
        if vehicle.oil_life is not None:
            parts.append(f"Oil life: {vehicle.oil_life}%")

        logger.debug(
            f"_default_summary: built summary for vehicle_code={vehicle.vehicle_code!r} "
            f"parts={len(parts)}"
        )
        return {
            "response": " | ".join(parts),
            "sources": ["MySQL DB"]
        }

    # =========================
    # JSON cleaner
    # =========================
    def _clean_json(self, text: str) -> str:
        """Strip markdown code fences from an LLM JSON response.

        Args:
            text: Raw LLM output string, possibly wrapped in ```json ... ```.

        Returns:
            str: Cleaned string with code fence markers removed.
        """
        text = text.strip()
        return re.sub(r"^```json\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()


def get_vehicle_agent() -> VehicleAgent:
    """Factory function — create a new stateless VehicleAgent instance.

    Returns:
        VehicleAgent: Fresh instance ready to process a single query.
    """
    logger.debug("get_vehicle_agent: creating new VehicleAgent instance")
    return VehicleAgent()
