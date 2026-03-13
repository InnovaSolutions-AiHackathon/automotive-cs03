DTC_DB = {
    "P0300": {"desc":"Random/Multiple Cylinder Misfire Detected",     "severity":"high",     "system":"engine"},
    "P0171": {"desc":"System Too Lean Bank 1",                       "severity":"medium",   "system":"engine"},
    "P0420": {"desc":"Catalyst System Efficiency Below Threshold",   "severity":"medium",   "system":"emission"},
    "C0035": {"desc":"Left Front Wheel Speed Sensor Circuit Fault",  "severity":"high",     "system":"brakes"},
    "B0001": {"desc":"Driver Frontal Stage 1 Airbag Circuit Open",  "severity":"critical", "system":"airbag"},
    "P0562": {"desc":"System Voltage Low",                            "severity":"medium",   "system":"electrical"},
}

from app.db.database import SessionLocal
from app.db.models import Vehicle, FaultCode

async def get_vehicle_data(vehicle_id: str) -> dict:
    db = SessionLocal()
    try:
        v = db.query(Vehicle).filter_by(vehicle_code=vehicle_id).first()
        if not v:
            return {"error": "Vehicle not found"}
        active_codes = [f.dtc_code for f in v.fault_codes if not f.resolved]
        return {
            "vehicle_code": v.vehicle_code, "vin": v.vin,
            "make": v.make, "model": v.model, "year": v.year,
            "odometer": v.odometer, "purchase_date": str(v.purchase_date),
            "fuel_level": v.fuel_level, "battery_voltage": float(v.battery_voltage),
            "engine_temp": v.engine_temp, "oil_life": v.oil_life,
            "active_dtcs": active_codes
        }
    finally:
        db.close()

async def decode_dtc(codes: list) -> dict:
    return {
        "decoded": {c: DTC_DB.get(c, {"desc":"Unknown — manual lookup required","severity":"unknown"})
                    for c in codes}
    }