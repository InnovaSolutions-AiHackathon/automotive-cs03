"""
Warranty API Router — app/api/warranty.py

Provides REST endpoints for warranty eligibility checks and record retrieval.

Endpoints:
    POST /api/warranty/check                  — check if a repair type is covered
    GET  /api/warranty/vehicle/{vehicle_code} — list all warranty records for a vehicle

DB schema used:
    cs03_warranty — ``warranty_records`` table via
    ``app.db.schemas.warranty.WarrantyRecord``.

The warranty eligibility logic is delegated to
``app.services.warranty_engine.check_warranty``.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.warranty_engine import check_warranty
from app.db.database import WarrantySession
from app.db.schemas.warranty import WarrantyRecord

logger = logging.getLogger(__name__)

router = APIRouter()


class WarrantyRequest(BaseModel):
    """Request body for the ``/check`` endpoint.

    Attributes:
        vehicle_id: The vehicle code to check coverage for (e.g. ``'VH-001'``).
        repair_type: The category of repair being evaluated (e.g. ``'engine'``,
            ``'brakes'``, ``'electrical'``).
    """

    vehicle_id: str
    repair_type: str


@router.post("/check")
async def warranty_check(req: WarrantyRequest):
    """Check warranty coverage for a given vehicle and repair type.

    Delegates to the warranty engine which evaluates active warranty records
    against the coverage map loaded from ``cs03_warranty``.

    Args:
        req: The parsed ``WarrantyRequest`` containing ``vehicle_id`` and
            ``repair_type``.

    Returns:
        dict: Engine result containing at minimum ``{"covered": bool}``.
            When covered: also includes ``coverage_type``, ``expires``,
            ``miles_remaining``, ``deductible``.
            When not covered: includes ``reason``.
    """
    logger.info(
        f"POST /api/warranty/check vehicle_id={req.vehicle_id!r} "
        f"repair_type={req.repair_type!r}"
    )

    logger.debug(
        f"warranty_check: delegating to check_warranty "
        f"vehicle_id={req.vehicle_id!r} repair_type={req.repair_type!r}"
    )
    result = await check_warranty(req.vehicle_id, req.repair_type)

    logger.info(
        f"warranty_check: result covered={result.get('covered')} "
        f"vehicle_id={req.vehicle_id!r} repair_type={req.repair_type!r}"
    )
    return result


@router.get("/vehicle/{vehicle_code}")
async def vehicle_warranties(vehicle_code: str):
    """Return all warranty records for a vehicle.

    Args:
        vehicle_code: The vehicle identifier to query records for.

    Returns:
        dict: Contains ``vehicle_code`` (str) and ``warranties`` (list of dicts),
            each warranty dict having: ``coverage_type``, ``start_date``,
            ``end_date``, ``mileage_limit``, ``is_extended``.
    """
    logger.info(f"GET /api/warranty/vehicle/{vehicle_code}")

    logger.debug(
        f"vehicle_warranties: opening WarrantySession for vehicle_code={vehicle_code!r}"
    )
    db = WarrantySession()
    try:
        records = db.query(WarrantyRecord).filter_by(vehicle_code=vehicle_code).all()
        logger.info(
            f"vehicle_warranties: found {len(records)} records for vehicle_code={vehicle_code!r}"
        )
        return {
            "vehicle_code": vehicle_code,
            "warranties": [
                {
                    "coverage_type": r.coverage_type,
                    "start_date":    str(r.start_date),
                    "end_date":      str(r.end_date),
                    "mileage_limit": r.mileage_limit,
                    "is_extended":   r.is_extended,
                }
                for r in records
            ]
        }
    finally:
        db.close()
        logger.debug(f"vehicle_warranties: WarrantySession closed vehicle_code={vehicle_code!r}")
