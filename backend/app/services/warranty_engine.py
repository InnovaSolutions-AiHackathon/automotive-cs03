"""
Warranty Engine Service — app/services/warranty_engine.py

Core business logic for evaluating warranty coverage for a given vehicle and
repair type.

Algorithm:
    1. Load coverage rules from ``cs03_warranty`` (``warranty_rules`` table).
       Falls back to built-in ``_DEFAULT_COVERAGE`` / ``_DEFAULT_EXCLUSIONS``
       dicts if the table is empty (dev/bootstrap mode).
    2. Reject immediately if ``repair_type`` is in the exclusions list.
    3. Fetch the vehicle's current odometer reading from ``cs03_vehicle``.
    4. Iterate warranty records for the vehicle; check that:
       - The repair type is covered by the record's coverage type.
       - Today's date falls within the warranty period (``start_date``..``end_date``).
       - The odometer reading is below the ``mileage_limit``.
    5. Return the first matching active record, or a ``not covered`` result.

DB schemas used:
    cs03_warranty — ``warranty_records``, ``warranty_rules`` tables
    cs03_vehicle  — ``vehicles`` table (odometer reading only)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.db.database import WarrantySession, VehicleSession
from app.db.schemas.warranty import WarrantyRecord, WarrantyRule
from app.db.schemas.vehicle import Vehicle

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default rules used when the warranty_rules table is empty
# ---------------------------------------------------------------------------
_DEFAULT_COVERAGE: dict[str, list[str]] = {
    "bumper_to_bumper": ["electrical", "interior", "ac", "brakes"],
    "powertrain":       ["engine", "transmission", "drivetrain"],
    "emission":         ["catalytic_converter", "o2_sensor"],
}
_DEFAULT_EXCLUSIONS: list[str] = ["tires", "wiper_blades", "wear_items", "accident_damage"]


def _load_coverage_map() -> tuple[dict[str, list[str]], list[str]]:
    """Load warranty coverage rules from the DB; fall back to defaults on error.

    Queries the ``warranty_rules`` table in ``cs03_warranty``.  If the table
    is empty or unreachable, the built-in ``_DEFAULT_COVERAGE`` and
    ``_DEFAULT_EXCLUSIONS`` constants are returned.

    Returns:
        tuple[dict[str, list[str]], list[str]]: A pair of
            (coverage_map, exclusions_list) where coverage_map maps
            coverage_type strings to lists of covered repair_type strings,
            and exclusions_list contains repair types that are never covered.
    """
    logger.debug("_load_coverage_map: querying warranty_rules from cs03_warranty")
    try:
        db = WarrantySession()
        try:
            rules = db.query(WarrantyRule).all()
            logger.debug(f"_load_coverage_map: found {len(rules)} warranty rule(s) in DB")
            if rules:
                coverage = {r.coverage_type: r.covered_types for r in rules}
                exclusions = list({exc for r in rules for exc in (r.exclusions or [])})
                logger.info(
                    f"_load_coverage_map: loaded {len(coverage)} coverage type(s) "
                    f"exclusion_count={len(exclusions)} from DB"
                )
                return coverage, exclusions
            else:
                logger.warning(
                    "_load_coverage_map: warranty_rules table is empty — using defaults"
                )
        finally:
            db.close()
    except Exception as exc:
        logger.warning(
            f"_load_coverage_map: could not load warranty rules from DB, using defaults: {exc}"
        )
    logger.info("_load_coverage_map: returning built-in default coverage map")
    return _DEFAULT_COVERAGE, _DEFAULT_EXCLUSIONS


async def check_warranty(vehicle_id: str, repair_type: str) -> dict[str, Any]:
    """Check whether a specific repair type is covered under warranty for a vehicle.

    Evaluates all active warranty records for the vehicle against the loaded
    coverage rules, taking into account date range and mileage limits.

    Args:
        vehicle_id: The vehicle code identifier (e.g. ``'VH-001'``).
        repair_type: The category of repair being evaluated (e.g. ``'engine'``,
            ``'brakes'``, ``'tires'``).

    Returns:
        dict[str, Any]: Coverage result dict.  When covered:
            ``{"covered": True, "coverage_type": str, "expires": str,
            "miles_remaining": int, "deductible": int}``.
            When not covered:
            ``{"covered": False, "reason": str}``.
    """
    logger.info(
        f"check_warranty: vehicle_id={vehicle_id!r} repair_type={repair_type!r}"
    )

    logger.debug("check_warranty: loading coverage map")
    coverage_map, exclusions = _load_coverage_map()

    # Check exclusions first (fast path)
    if repair_type in exclusions:
        logger.info(
            f"check_warranty: repair_type={repair_type!r} is an excluded wear item — not covered"
        )
        return {"covered": False, "reason": f"'{repair_type}' is an excluded wear item"}

    # Fetch vehicle odometer from vehicle schema
    logger.debug(
        f"check_warranty: fetching odometer from cs03_vehicle vehicle_id={vehicle_id!r}"
    )
    vehicle_db = VehicleSession()
    try:
        vehicle = vehicle_db.query(Vehicle).filter_by(vehicle_code=vehicle_id).first()
        if not vehicle:
            logger.warning(
                f"check_warranty: vehicle not found vehicle_id={vehicle_id!r}"
            )
            return {"covered": False, "reason": f"Vehicle '{vehicle_id}' not found"}
        odometer = vehicle.odometer
        logger.debug(
            f"check_warranty: odometer={odometer:,} km vehicle_id={vehicle_id!r}"
        )
    finally:
        vehicle_db.close()

    # Fetch warranty records from warranty schema
    logger.debug(
        f"check_warranty: fetching warranty records from cs03_warranty "
        f"vehicle_id={vehicle_id!r}"
    )
    warranty_db = WarrantySession()
    try:
        records = (
            warranty_db.query(WarrantyRecord)
            .filter_by(vehicle_code=vehicle_id)
            .all()
        )
        logger.info(
            f"check_warranty: found {len(records)} warranty record(s) "
            f"for vehicle_id={vehicle_id!r}"
        )

        today = date.today()
        for record in records:
            covered_types = coverage_map.get(record.coverage_type, [])
            logger.debug(
                f"check_warranty: evaluating record coverage_type={record.coverage_type!r} "
                f"covered_types={covered_types} repair_type={repair_type!r}"
            )

            if repair_type not in covered_types:
                logger.debug(
                    f"check_warranty: repair_type={repair_type!r} not in "
                    f"covered_types for coverage_type={record.coverage_type!r} — skipping"
                )
                continue

            within_date  = record.start_date <= today <= record.end_date
            within_miles = odometer <= record.mileage_limit

            logger.debug(
                f"check_warranty: within_date={within_date} "
                f"(today={today} start={record.start_date} end={record.end_date}) "
                f"within_miles={within_miles} "
                f"(odometer={odometer:,} limit={record.mileage_limit:,})"
            )

            if within_date and within_miles:
                miles_remaining = record.mileage_limit - odometer
                logger.info(
                    f"check_warranty: COVERED vehicle_id={vehicle_id!r} "
                    f"coverage_type={record.coverage_type!r} "
                    f"expires={record.end_date} miles_remaining={miles_remaining:,}"
                )
                return {
                    "covered": True,
                    "coverage_type": record.coverage_type,
                    "expires": str(record.end_date),
                    "miles_remaining": miles_remaining,
                    "deductible": 0,
                }

        logger.info(
            f"check_warranty: NOT COVERED — outside warranty period or mileage limit "
            f"vehicle_id={vehicle_id!r} repair_type={repair_type!r}"
        )
        return {"covered": False, "reason": "Outside warranty period or mileage limit"}

    except Exception as exc:
        logger.error(
            f"check_warranty: error for vehicle_id={vehicle_id!r} "
            f"repair_type={repair_type!r}: {exc}"
        )
        return {"covered": False, "reason": "Warranty check failed — please retry"}
    finally:
        warranty_db.close()
        logger.debug(
            f"check_warranty: WarrantySession closed vehicle_id={vehicle_id!r}"
        )
