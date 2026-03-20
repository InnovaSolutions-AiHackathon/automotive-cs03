"""
Telematics Service — app/services/telematics.py

Provides vehicle sensor data retrieval and OBD-II DTC fault code decoding.

Responsibilities:
    - Fetch live vehicle telemetry (odometer, fuel level, battery voltage,
      engine temperature, oil life) from ``cs03_vehicle``.
    - Collect the list of unresolved DTC fault codes for the vehicle.
    - Resolve DTC codes to human-readable descriptions and severity levels
      via the ``cs03_telematics`` DB (``dtc_codes`` table).
    - Fall back to a built-in ``_SEED_DTC`` dictionary for codes not found
      in the DB, and to an ``unknown`` sentinel for completely unrecognised
      codes.

DB schemas used:
    cs03_vehicle    — ``vehicles``, ``fault_codes`` tables
    cs03_telematics — ``dtc_codes`` table
"""
from __future__ import annotations

import logging
from typing import Any

from app.db.database import TelematicsSession, VehicleSession
from app.db.schemas.telematics import DTCCode
from app.db.schemas.vehicle import Vehicle, FaultCode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed DTC data — used when dtc_codes table is empty
# ---------------------------------------------------------------------------
_SEED_DTC: dict[str, dict] = {
    "P0300": {"desc": "Random/Multiple Cylinder Misfire Detected",    "severity": "high",     "system": "engine"},
    "P0171": {"desc": "System Too Lean Bank 1",                      "severity": "medium",   "system": "engine"},
    "P0420": {"desc": "Catalyst System Efficiency Below Threshold",  "severity": "medium",   "system": "emission"},
    "C0035": {"desc": "Left Front Wheel Speed Sensor Circuit Fault", "severity": "high",     "system": "brakes"},
    "B0001": {"desc": "Driver Frontal Stage 1 Airbag Circuit Open",  "severity": "critical", "system": "airbag"},
    "P0562": {"desc": "System Voltage Low",                          "severity": "medium",   "system": "electrical"},
}


def _lookup_dtc_in_db(codes: list[str]) -> dict[str, dict]:
    """Resolve a list of DTC codes to descriptions using the DB then seed fallback.

    Queries the ``dtc_codes`` table in ``cs03_telematics`` for all provided
    codes.  Any code not found in the DB is resolved from ``_SEED_DTC`` (or
    given an ``'unknown'`` sentinel if not in the seed data either).

    Args:
        codes: List of OBD-II DTC code strings (e.g. ``['P0300', 'P0171']``).

    Returns:
        dict[str, dict]: Mapping of DTC code string to an info dict with keys
            ``desc`` (str), ``severity`` (str), and ``system`` (str).
    """
    logger.debug(
        f"_lookup_dtc_in_db: resolving {len(codes)} DTC code(s): {codes}"
    )
    result: dict[str, dict] = {}
    try:
        db = TelematicsSession()
        try:
            rows = db.query(DTCCode).filter(DTCCode.code.in_(codes)).all()
            logger.debug(
                f"_lookup_dtc_in_db: found {len(rows)} DTC row(s) in cs03_telematics"
            )
            for row in rows:
                result[row.code] = {
                    "desc":     row.desc,
                    "severity": row.severity,
                    "system":   row.system,
                }
        finally:
            db.close()
    except Exception as exc:
        logger.warning(
            f"_lookup_dtc_in_db: DTC DB lookup failed, using seed data: {exc}"
        )

    # Fill in anything not found in DB from seed / unknown fallback
    missing_codes = [code for code in codes if code not in result]
    if missing_codes:
        logger.debug(
            f"_lookup_dtc_in_db: resolving {len(missing_codes)} code(s) from seed/fallback: "
            f"{missing_codes}"
        )
    for code in codes:
        if code not in result:
            seed_entry = _SEED_DTC.get(code)
            if seed_entry:
                result[code] = seed_entry
                logger.debug(f"_lookup_dtc_in_db: code={code!r} resolved from seed data")
            else:
                result[code] = {
                    "desc": "Unknown — manual lookup required",
                    "severity": "unknown",
                    "system": "unknown",
                }
                logger.warning(
                    f"_lookup_dtc_in_db: code={code!r} not found in DB or seed — marked unknown"
                )

    logger.debug(f"_lookup_dtc_in_db: returning {len(result)} resolved DTC(s)")
    return result


async def get_vehicle_data(vehicle_id: str) -> dict[str, Any]:
    """Fetch full telemetry data for a vehicle including decoded DTC codes.

    Retrieves sensor readings and unresolved fault codes from ``cs03_vehicle``,
    then resolves the DTC codes via ``_lookup_dtc_in_db``.

    Args:
        vehicle_id: The vehicle code identifier (e.g. ``'VH-001'``).

    Returns:
        dict[str, Any]: Telemetry payload containing:
            ``vehicle_code``, ``vin``, ``make``, ``model``, ``year``,
            ``odometer``, ``purchase_date``, ``fuel_level``, ``battery_voltage``,
            ``engine_temp``, ``oil_life``, ``active_dtcs`` (list[str]),
            ``decoded_dtcs`` (dict[str, dict]).

        If the vehicle is not found, returns ``{"error": str}``.
        On DB/exception errors, returns ``{"error": "Failed to fetch vehicle data"}``.
    """
    logger.info(f"get_vehicle_data: vehicle_id={vehicle_id!r}")

    logger.debug(
        f"get_vehicle_data: opening VehicleSession for vehicle_id={vehicle_id!r}"
    )
    db = VehicleSession()
    try:
        v = db.query(Vehicle).filter_by(vehicle_code=vehicle_id).first()
        if not v:
            logger.warning(
                f"get_vehicle_data: vehicle not found vehicle_id={vehicle_id!r}"
            )
            return {"error": f"Vehicle '{vehicle_id}' not found"}

        logger.debug(
            f"get_vehicle_data: vehicle found make={v.make!r} model={v.model!r} "
            f"year={v.year} odometer={v.odometer:,}"
        )

        active_codes = [f.dtc_code for f in v.fault_codes if not f.resolved]
        logger.info(
            f"get_vehicle_data: {len(active_codes)} active DTC code(s) "
            f"vehicle_id={vehicle_id!r}"
        )

        if active_codes:
            logger.debug(
                f"get_vehicle_data: decoding {len(active_codes)} DTC code(s): {active_codes}"
            )
            decoded = _lookup_dtc_in_db(active_codes)
        else:
            decoded = {}
            logger.debug(f"get_vehicle_data: no active DTCs vehicle_id={vehicle_id!r}")

        payload = {
            "vehicle_code":    v.vehicle_code,
            "vin":             v.vin,
            "make":            v.make,
            "model":           v.model,
            "year":            v.year,
            "odometer":        v.odometer,
            "purchase_date":   str(v.purchase_date),
            "fuel_level":      v.fuel_level,
            "battery_voltage": float(v.battery_voltage),
            "engine_temp":     v.engine_temp,
            "oil_life":        v.oil_life,
            "active_dtcs":     active_codes,
            "decoded_dtcs":    decoded,
        }
        logger.info(
            f"get_vehicle_data: returning telemetry payload vehicle_id={vehicle_id!r} "
            f"active_dtc_count={len(active_codes)}"
        )
        return payload

    except Exception as exc:
        logger.error(
            f"get_vehicle_data: telematics fetch error for vehicle_id={vehicle_id!r}: {exc}"
        )
        return {"error": "Failed to fetch vehicle data"}
    finally:
        db.close()
        logger.debug(
            f"get_vehicle_data: VehicleSession closed vehicle_id={vehicle_id!r}"
        )


async def decode_dtc(codes: list[str]) -> dict[str, Any]:
    """Decode a list of OBD-II DTC codes to descriptions and severity levels.

    Convenience wrapper around ``_lookup_dtc_in_db`` for standalone DTC
    resolution without fetching full vehicle data.

    Args:
        codes: List of DTC code strings to decode (e.g. ``['P0300']``).
            Empty lists are handled gracefully.

    Returns:
        dict[str, Any]: ``{"decoded": {code: {desc, severity, system}, ...}}``
    """
    logger.info(f"decode_dtc: decoding {len(codes)} code(s): {codes}")
    if not codes:
        logger.debug("decode_dtc: empty codes list — returning empty decoded dict")
        return {"decoded": {}}
    result = {"decoded": _lookup_dtc_in_db(codes)}
    logger.info(f"decode_dtc: resolved {len(result['decoded'])} code(s)")
    return result
