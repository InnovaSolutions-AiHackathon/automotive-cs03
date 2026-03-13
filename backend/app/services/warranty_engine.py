from datetime import date
from app.db.database import SessionLocal
from app.db.models import Vehicle, WarrantyRecord

COVERAGE_MAP = {
    "bumper_to_bumper": ["electrical", "interior", "ac", "brakes"],
    "powertrain":       ["engine", "transmission", "drivetrain"],
    "emission":         ["catalytic_converter", "o2_sensor"],
}
EXCLUSIONS = ["tires", "wiper_blades", "wear_items", "accident_damage"]

async def check_warranty(vehicle_id: str, repair_type: str) -> dict:
    if repair_type in EXCLUSIONS:
        return {"covered": False, "reason": "Excluded wear item"}

    db = SessionLocal()
    try:
        vehicle = db.query(Vehicle).filter_by(vehicle_code=vehicle_id).first()
        if not vehicle:
            return {"covered": False, "reason": "Vehicle not found"}

        today = date.today()
        for warranty in vehicle.warranties:
            covered_types = COVERAGE_MAP.get(warranty.coverage_type, [])
            if repair_type in covered_types:
                within_date = warranty.start_date <= today <= warranty.end_date
                within_miles = vehicle.odometer <= warranty.mileage_limit
                if within_date and within_miles:
                    return {
                        "covered": True,
                        "coverage_type": warranty.coverage_type,
                        "expires": str(warranty.end_date),
                        "miles_remaining": warranty.mileage_limit - vehicle.odometer,
                        "deductible": 0
                    }
        return {"covered": False, "reason": "Outside warranty period or mileage limit"}
    finally:
        db.close()