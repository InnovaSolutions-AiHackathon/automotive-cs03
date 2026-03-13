from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Vehicle

router = APIRouter()

@router.get("/{vehicle_code}")
def get_vehicle(vehicle_code: str, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter_by(vehicle_code=vehicle_code).first()
    if not v: raise HTTPException(status_code=404, detail="Not found")
    codes = [f.dtc_code for f in v.fault_codes if not f.resolved]
    return {
        "vehicle_code": v.vehicle_code, "vin": v.vin,
        "make": v.make, "model": v.model, "year": v.year,
        "odometer": v.odometer, "fuel_level": v.fuel_level,
        "battery_voltage": float(v.battery_voltage),
        "engine_temp": v.engine_temp, "oil_life": v.oil_life,
        "active_dtcs": codes
    }

@router.get("/")
def list_vehicles(db: Session = Depends(get_db)):
    return [
        {"vehicle_code": v.vehicle_code, "make": v.make,
         "model": v.model, "year": v.year}
        for v in db.query(Vehicle).all()
    ]