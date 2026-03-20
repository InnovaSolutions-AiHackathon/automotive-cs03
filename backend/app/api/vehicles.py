"""
Vehicles API Router — app/api/vehicles.py

Provides REST endpoints for querying vehicle records stored in the
``cs03_vehicle`` MySQL schema.

Endpoints:
    GET /api/vehicles/           — list all vehicles (code, make, model, year)
    GET /api/vehicles/{vehicle_code} — get full details for one vehicle including
                                       active DTC fault codes

DB schema used:
    cs03_vehicle  — ``vehicles`` and ``fault_codes`` tables via
    ``app.db.schemas.vehicle.Vehicle`` and ``FaultCode``.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas.vehicle import Vehicle

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{vehicle_code}")
def get_vehicle(vehicle_code: str, db: Session = Depends(get_db)):
    """Retrieve full details for a single vehicle by its vehicle code.

    Args:
        vehicle_code: The unique vehicle identifier (e.g. ``'VH-001'``).
        db: Injected SQLAlchemy session for the ``cs03_vehicle`` schema.

    Returns:
        dict: Vehicle record containing:
            - ``vehicle_code`` (str)
            - ``vin`` (str)
            - ``make`` (str)
            - ``model`` (str)
            - ``year`` (int)
            - ``odometer`` (int)
            - ``fuel_level`` (float)
            - ``battery_voltage`` (float)
            - ``engine_temp`` (float)
            - ``oil_life`` (float)
            - ``active_dtcs`` (list[str]) — unresolved DTC codes only

    Raises:
        HTTPException: 404 if no vehicle with ``vehicle_code`` exists.
    """
    logger.info(f"GET /api/vehicles/{vehicle_code}")

    logger.debug(f"get_vehicle: querying cs03_vehicle for vehicle_code={vehicle_code!r}")
    v = db.query(Vehicle).filter_by(vehicle_code=vehicle_code).first()

    if not v:
        logger.warning(f"get_vehicle: vehicle not found vehicle_code={vehicle_code!r}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    active_dtcs = [f.dtc_code for f in v.fault_codes if not f.resolved]
    logger.info(
        f"get_vehicle: found vehicle_code={vehicle_code!r} "
        f"make={v.make!r} model={v.model!r} year={v.year} "
        f"active_dtc_count={len(active_dtcs)}"
    )

    return {
        "vehicle_code":    v.vehicle_code,
        "vin":             v.vin,
        "make":            v.make,
        "model":           v.model,
        "year":            v.year,
        "odometer":        v.odometer,
        "fuel_level":      v.fuel_level,
        "battery_voltage": float(v.battery_voltage),
        "engine_temp":     v.engine_temp,
        "oil_life":        v.oil_life,
        "active_dtcs":     active_dtcs,
    }


@router.get("/")
def list_vehicles(db: Session = Depends(get_db)):
    """List all vehicles in the system (summary view).

    Args:
        db: Injected SQLAlchemy session for the ``cs03_vehicle`` schema.

    Returns:
        list[dict]: Each dict contains ``vehicle_code``, ``make``, ``model``,
            and ``year`` for every vehicle row in the database.
    """
    logger.info("GET /api/vehicles/ — listing all vehicles")

    logger.debug("list_vehicles: querying cs03_vehicle for all Vehicle rows")
    vehicles = db.query(Vehicle).all()

    logger.info(f"list_vehicles: returning {len(vehicles)} vehicles")
    return [
        {"vehicle_code": v.vehicle_code, "make": v.make, "model": v.model, "year": v.year}
        for v in vehicles
    ]
