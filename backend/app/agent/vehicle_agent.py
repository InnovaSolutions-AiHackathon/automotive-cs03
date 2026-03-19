import logging
from typing import Dict, Any, List
from app.db.database import SessionLocal
from app.db.models import Vehicle, Customer, FaultCode, WarrantyRecord, ServiceAppointment

logger = logging.getLogger(__name__)

class VehicleAgent:
    """
    VehicleAgent handles queries related to vehicle metadata, ownership,
    telemetry, warranties, and service appointments.
    """

    def __init__(self):
        self.session_factory = SessionLocal

    async def process_query(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        vehicle_code = context.get("vehicle_id")
        user_id = context.get("user_id")  # assume we track logged-in user

        with self.session_factory() as db:
            # If no vehicle_id provided, try to resolve vehicles for this user
            if not vehicle_code:
                vehicles = db.query(Vehicle).filter(Vehicle.customer_id == user_id).all()
                if not vehicles:
                    return {"response": "No vehicles found for your account.", "sources": ["MySQL DB"]}
                if len(vehicles) == 1:
                    v = vehicles[0]
                    return {"response": f"Your vehicle details: {v.make} {v.model} ({v.year}).",
                            "sources": ["MySQL DB"]}
                else:
                    vehicle_list = [f"{v.vehicle_code}: {v.make} {v.model} ({v.year})" for v in vehicles]
                    return {
                            "message": "You have multiple vehicles. Please select one to proceed.",
                            "vehicles": vehicles
                            }

            # If vehicle_id is provided, continue with field detection
            fields = self.detect_fields(user_message)
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_code == vehicle_code).first()
            if not vehicle:
                return {"response": f"No vehicle found with code {vehicle_code}.", "sources": ["MySQL DB"]}

            responses = []
            if "model" in fields: responses.append(f"Model: {vehicle.model}")
            if "make" in fields: responses.append(f"Make: {vehicle.make}")
            if "year" in fields: responses.append(f"Year: {vehicle.year}")
            if "owner" in fields:
                customer = db.query(Customer).filter(Customer.id == vehicle.customer_id).first()
                responses.append(f"Owner: {customer.name if customer else 'Unknown'}")
            if "faults" in fields:
                faults = db.query(FaultCode).filter(FaultCode.vehicle_id == vehicle.id).all()
                fault_list = [f.dtc_code for f in faults]
                responses.append(f"Active fault codes: {fault_list}")
            if "warranty" in fields:
                warranties = db.query(WarrantyRecord).filter(WarrantyRecord.vehicle_id == vehicle.id).all()
                warranty_info = [f"{w.coverage_type} until {w.end_date}" for w in warranties]
                responses.append(f"Warranties: {warranty_info}")
            if "service" in fields:
                appts = db.query(ServiceAppointment).filter(ServiceAppointment.vehicle_id == vehicle.id).all()
                service_info = [f"{a.service_type} on {a.scheduled_date} ({a.status})" for a in appts]
                responses.append(f"Service appointments: {service_info}")

            if not responses:
                summary = {
                    "make": vehicle.make,
                    "model": vehicle.model,
                    "year": vehicle.year,
                    "vin": vehicle.vin,
                    "odometer": vehicle.odometer,
                    "fuel_level": vehicle.fuel_level,
                    "battery_voltage": str(vehicle.battery_voltage),
                    "engine_temp": vehicle.engine_temp,
                    "oil_life": vehicle.oil_life,
                }
                return {"response": f"Vehicle summary: {summary}", "sources": ["MySQL DB"]}

            return {"response": " | ".join(responses), "sources": ["MySQL DB"]}

    def detect_fields(self, user_message: str) -> List[str]:
        msg = user_message.lower()
        fields = []
        if "model" in msg: fields.append("model")
        if "make" in msg or "brand" in msg: fields.append("make")
        if "year" in msg or "age" in msg: fields.append("year")
        if "owner" in msg: fields.append("owner")
        if "fault" in msg or "dtc" in msg: fields.append("faults")
        if "warranty" in msg or "coverage" in msg: fields.append("warranty")
        if "service" in msg or "appointment" in msg: fields.append("service")
        return fields


def get_vehicle_agent() -> VehicleAgent:
    return VehicleAgent()
