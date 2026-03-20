"""
Scheduler Service — app/services/scheduler.py

Generates a list of available service appointment slots for a given service
type and urgency level.

Algorithm:
    1. Load qualified technicians from ``cs03_scheduler`` (``technicians`` table)
       filtered by specialty and active status.
       Falls back to ``_DEFAULT_TECHNICIANS`` if the table is empty or
       unreachable (dev/bootstrap mode).
    2. Starting from an urgency-based day offset (critical=1, high=2,
       normal=3), iterate weekdays (Monday–Friday) and pre-defined time slots
       until 4 slots are collected.
    3. For each slot, randomly select a qualified technician and assign a bay.

DB schema used:
    cs03_scheduler — ``technicians`` table
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

from app.db.database import SchedulerSession
from app.db.schemas.scheduler import Technician

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default seed data — used when technicians table is empty
# ---------------------------------------------------------------------------
_DEFAULT_TECHNICIANS = [
    {"tech_code": "T01_Kumar", "name": "Kumar",  "specialties": ["engine", "transmission", "drivetrain"]},
    {"tech_code": "T02_Patel", "name": "Patel",  "specialties": ["electrical", "diagnostics"]},
    {"tech_code": "T03_Ahmed", "name": "Ahmed",  "specialties": ["brakes", "suspension"]},
    {"tech_code": "T04_Ramos", "name": "Ramos",  "specialties": ["ac", "interior", "general"]},
]

_SLOT_HOURS = [8, 10, 13, 15]
_URGENCY_OFFSET = {"critical": 1, "high": 2, "normal": 3}


def _load_technicians(service_type: str) -> list[dict]:
    """Return active technicians qualified for ``service_type`` from the DB.

    Queries the ``technicians`` table in ``cs03_scheduler`` filtering for
    ``is_active=True`` and matching specialty.  Falls back to
    ``_DEFAULT_TECHNICIANS`` if the DB is unavailable or the table is empty.

    Args:
        service_type: The service category string (e.g. ``'engine'``,
            ``'brakes'``, ``'general'``).

    Returns:
        list[dict]: List of technician dicts, each with keys
            ``tech_code``, ``name``, ``specialties``.  May be empty if no
            qualified technicians are found.
    """
    logger.debug(
        f"_load_technicians: querying cs03_scheduler for service_type={service_type!r}"
    )
    try:
        db = SchedulerSession()
        try:
            techs = db.query(Technician).filter_by(is_active=True).all()
            logger.debug(f"_load_technicians: found {len(techs)} active technician(s) in DB")
            if techs:
                qualified = [
                    {"tech_code": t.tech_code, "name": t.name, "specialties": t.specialties}
                    for t in techs
                    if service_type in t.specialties or "general" in t.specialties
                ]
                logger.info(
                    f"_load_technicians: {len(qualified)} qualified technician(s) "
                    f"for service_type={service_type!r} (from DB)"
                )
                return qualified
            else:
                logger.warning(
                    "_load_technicians: technicians table is empty — using defaults"
                )
        finally:
            db.close()
    except Exception as exc:
        logger.warning(
            f"_load_technicians: could not load technicians from DB, using defaults: {exc}"
        )

    fallback = [
        t for t in _DEFAULT_TECHNICIANS
        if service_type in t["specialties"] or "general" in t["specialties"]
    ]
    logger.info(
        f"_load_technicians: {len(fallback)} qualified technician(s) "
        f"for service_type={service_type!r} (from defaults)"
    )
    return fallback


async def get_slots(service_type: str, urgency: str = "normal") -> dict[str, Any]:
    """Generate available service appointment slots.

    Builds up to 4 slots starting from the urgency-based day offset and
    iterating over weekdays and pre-defined time slots until the limit is
    reached.

    Args:
        service_type: The service category string (e.g. ``'engine'``,
            ``'brakes'``, ``'oil_change'``).
        urgency: Priority level — one of ``'critical'`` (slots from day 1),
            ``'high'`` (from day 2), or ``'normal'`` (from day 3, default).

    Returns:
        dict[str, Any]: Contains:
            - ``"slots"`` (list[dict]) — up to 4 slot dicts, each with
              ``date``, ``time``, ``technician_code``, ``technician_name``,
              ``duration_hours``, ``bay``.
            - ``"urgency"`` (str) — the urgency level used.
            - ``"service_type"`` (str) — the service type used.
            - ``"available"`` (bool) — True if any slots were generated.
    """
    logger.info(
        f"get_slots: service_type={service_type!r} urgency={urgency!r}"
    )

    offset = _URGENCY_OFFSET.get(urgency, _URGENCY_OFFSET["normal"])
    logger.debug(f"get_slots: day_offset={offset} for urgency={urgency!r}")

    qualified = _load_technicians(service_type)
    if not qualified:
        logger.warning(
            f"get_slots: no qualified technicians found for service_type={service_type!r}"
        )

    slots: list[dict] = []
    today = datetime.now()
    days_checked = 0

    for day_offset in range(offset, offset + 14):
        if len(slots) >= 4:
            break
        day = today + timedelta(days=day_offset)
        days_checked += 1
        if day.weekday() >= 5:   # skip weekends
            logger.debug(
                f"get_slots: skipping weekend day={day.strftime('%Y-%m-%d')} "
                f"weekday={day.weekday()}"
            )
            continue
        for hr in _SLOT_HOURS:
            if len(slots) >= 4:
                break
            tech = random.choice(qualified) if qualified else {"tech_code": "TBA", "name": "TBA"}
            slot = {
                "date":           day.strftime("%Y-%m-%d"),
                "time":           f"{hr:02d}:00",
                "technician_code": tech["tech_code"],
                "technician_name": tech["name"],
                "duration_hours": 2,
                "bay":            random.randint(1, 4),
            }
            slots.append(slot)
            logger.debug(
                f"get_slots: added slot date={slot['date']} time={slot['time']} "
                f"technician={slot['technician_name']!r} bay={slot['bay']}"
            )

    logger.info(
        f"get_slots: returning {len(slots)} slot(s) "
        f"service_type={service_type!r} urgency={urgency!r} "
        f"days_searched={days_checked}"
    )
    return {
        "slots":        slots,
        "urgency":      urgency,
        "service_type": service_type,
        "available":    len(slots) > 0,
    }
