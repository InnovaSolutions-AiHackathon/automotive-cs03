import json
import logging
import re
from typing import Dict, Any, List

from app.db.database import SessionLocal
from app.db.models import Vehicle, Customer, FaultCode, WarrantyRecord, ServiceAppointment
from app.agent.gemini_client import GeminiClient
from app.config import settings

logger = logging.getLogger(__name__)

VALID_FIELDS = {"model", "make", "year", "owner", "faults", "warranty", "service"}


class VehicleAgent:
    def __init__(self):
        self.session_factory = SessionLocal
        self.llm_client = GeminiClient(api_key=settings.GEMINI_API_KEY)

    async def process_query(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        vehicle_code = context.get("vehicle_id")
        user_id = context.get("user_id")

        with self.session_factory() as db:

            # 🔹 Resolve vehicle
            vehicle = self._resolve_vehicle(db, vehicle_code, user_id)
            if isinstance(vehicle, dict):  # early response case
                return vehicle

            # 🔹 Detect fields
            fields = self._detect_fields_rule(user_message)
            if not fields:
                fields = await self._detect_fields_llm(user_message)

            fields = list(set(fields) & VALID_FIELDS)
            logger.info(f"[VehicleAgent] Fields: {fields}")

            # 🔹 Fetch data
            data = self._fetch_data(db, vehicle, fields)

            # 🔹 Build response
            if not data:
                return self._default_summary(vehicle)

            return {
                "response": " | ".join(data),
                "sources": ["MySQL DB"]
            }

    # =========================
    # 🔹 Vehicle resolution
    # =========================
    def _resolve_vehicle(self, db, vehicle_code, user_id):
        if vehicle_code:
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_code == vehicle_code).first()
            if not vehicle:
                return {"response": f"No vehicle found with code {vehicle_code}.", "sources": ["MySQL DB"]}
            return vehicle

        vehicles = db.query(Vehicle).filter(Vehicle.customer_id == user_id).all()

        if not vehicles:
            return {"response": "No vehicles found for your account.", "sources": ["MySQL DB"]}

        vehicle_list = [{"code": v.vehicle_code, "name": f"{v.make} {v.model}"} for v in vehicles]

        if len(vehicles) == 1: 
            return {
            "message": "We found your vehicle. Please confirm if this is the one.",
            "vehicles": vehicles
            }

        return {
            "message": "You have multiple vehicles. Please select one.",
            "vehicles": vehicles
        }

    # =========================
    # 🔹 Rule-based detection
    # =========================
    def _detect_fields_rule(self, msg: str) -> List[str]:
        msg = msg.lower()
        mapping = {
            "model": ["model"],
            "make": ["make", "brand"],
            "year": ["year", "age"],
            "owner": ["owner"],
            "faults": ["fault", "dtc", "issue", "problem"],
            "warranty": ["warranty", "coverage"],
            "service": ["service", "appointment"]
        }

        return [
            field for field, keywords in mapping.items()
            if any(k in msg for k in keywords)
        ]

    # =========================
    # 🔹 LLM fallback
    # =========================
    async def _detect_fields_llm(self, user_message: str) -> List[str]:
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
            parsed = json.loads(raw)

            return parsed.get("fields", [])

        except Exception as e:
            logger.error(f"LLM field detection failed: {e}")
            return []

    # =========================
    # 🔹 Data fetching
    # =========================
    def _fetch_data(self, db, vehicle, fields: List[str]) -> List[str]:
        results = []

        if "model" in fields:
            results.append(f"Model: {vehicle.model}")

        if "make" in fields:
            results.append(f"Make: {vehicle.make}")

        if "year" in fields:
            results.append(f"Year: {vehicle.year}")

        if "owner" in fields:
            customer = db.query(Customer).filter(Customer.id == vehicle.customer_id).first()
            results.append(f"Owner: {customer.name if customer else 'Unknown'}")

        if "faults" in fields:
            faults = db.query(FaultCode).filter(FaultCode.vehicle_id == vehicle.id).all()
            results.append(f"Fault codes: {[f.dtc_code for f in faults]}")

        if "warranty" in fields:
            warranties = db.query(WarrantyRecord).filter(WarrantyRecord.vehicle_id == vehicle.id).all()
            results.append(
                f"Warranty: {[f'{w.coverage_type} until {w.end_date}' for w in warranties]}"
            )

        if "service" in fields:
            appts = db.query(ServiceAppointment).filter(ServiceAppointment.vehicle_id == vehicle.id).all()
            results.append(
                f"Service: {[f'{a.service_type} on {a.scheduled_date}' for a in appts]}"
            )

        return results

    # =========================
    # 🔹 Default fallback
    # =========================
    def _default_summary(self, vehicle) -> Dict[str, Any]:
        return {
            "response": f"{vehicle.make} {vehicle.model} ({vehicle.year}) | VIN: {vehicle.vin}",
            "sources": ["MySQL DB"]
        }

    # =========================
    # 🔹 JSON cleaner
    # =========================
    def _clean_json(self, text: str) -> str:
        text = text.strip()
        return re.sub(r"^```json\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()


def get_vehicle_agent() -> VehicleAgent:
    return VehicleAgent()