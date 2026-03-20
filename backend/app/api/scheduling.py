"""
Scheduling API Router — app/api/scheduling.py

Provides REST endpoints for service slot availability and appointment booking.

Endpoints:
    POST /api/scheduling/slots                        — get available time slots
    POST /api/scheduling/book                         — book a service appointment
    GET  /api/scheduling/appointments/{vehicle_code}  — list appointments for a vehicle

DB schema used:
    cs03_scheduler — ``service_appointments`` table via
    ``app.db.schemas.scheduler.ServiceAppointment``.

Slot generation logic (technician lookup, scheduling windows) is handled by
``app.services.scheduler.get_slots``.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.scheduler import get_slots
from app.db.database import SchedulerSession
from app.db.schemas.scheduler import ServiceAppointment

logger = logging.getLogger(__name__)

router = APIRouter()


class SlotsRequest(BaseModel):
    """Request body for the ``/slots`` endpoint.

    Attributes:
        service_type: The type of service needed (e.g. ``'engine'``,
            ``'brakes'``, ``'oil_change'``).
        urgency: Priority level — one of ``'critical'``, ``'high'``, or
            ``'normal'`` (default ``'normal'``).
    """

    service_type: str
    urgency: str = "normal"


class BookRequest(BaseModel):
    """Request body for the ``/book`` endpoint.

    Attributes:
        vehicle_code: Vehicle identifier (e.g. ``'VH-001'``).
        service_type: Type of service to be performed.
        scheduled_date: ISO-8601 date string ``YYYY-MM-DD``.
        scheduled_time: Time string ``HH:MM``.
        technician_code: Optional technician identifier to request.
        urgency: Priority level (default ``'normal'``).
        notes: Optional free-text notes for the appointment.
        warranty_covered: Whether the appointment cost is covered by warranty.
    """

    vehicle_code: str
    service_type: str
    scheduled_date: str   # YYYY-MM-DD
    scheduled_time: str   # HH:MM
    technician_code: Optional[str] = None
    urgency: str = "normal"
    notes: Optional[str] = None
    warranty_covered: bool = False


@router.post("/slots")
async def available_slots(req: SlotsRequest):
    """Return available service slots for the given service type and urgency.

    Args:
        req: The parsed ``SlotsRequest`` with ``service_type`` and ``urgency``.

    Returns:
        dict: Slot availability result from the scheduler service, containing:
            ``slots`` (list), ``urgency`` (str), ``service_type`` (str),
            ``available`` (bool).
    """
    logger.info(
        f"POST /api/scheduling/slots service_type={req.service_type!r} urgency={req.urgency!r}"
    )

    logger.debug(
        f"available_slots: delegating to get_slots "
        f"service_type={req.service_type!r} urgency={req.urgency!r}"
    )
    result = await get_slots(req.service_type, req.urgency)

    slot_count = len(result.get("slots", []))
    logger.info(
        f"available_slots: returning {slot_count} slots "
        f"service_type={req.service_type!r} urgency={req.urgency!r}"
    )
    return result


@router.post("/book", status_code=status.HTTP_201_CREATED)
async def book_appointment(req: BookRequest):
    """Persist a service appointment to the scheduler DB.

    Parses the ISO date string, constructs a ``ServiceAppointment`` ORM object,
    commits it to ``cs03_scheduler``, and returns the persisted booking details.

    Args:
        req: The parsed ``BookRequest`` containing all appointment fields.

    Returns:
        dict: Confirmation payload containing ``booked`` (True), ``appointment_id``,
            ``vehicle_code``, ``service_type``, ``date``, ``time``, ``technician``,
            and ``status`` (``'confirmed'``).

    Raises:
        HTTPException: 500 if the database insert fails.
    """
    logger.info(
        f"POST /api/scheduling/book vehicle_code={req.vehicle_code!r} "
        f"service_type={req.service_type!r} date={req.scheduled_date!r} "
        f"time={req.scheduled_time!r} urgency={req.urgency!r} "
        f"warranty_covered={req.warranty_covered}"
    )

    logger.debug(f"book_appointment: opening SchedulerSession for vehicle_code={req.vehicle_code!r}")
    db = SchedulerSession()
    try:
        appt = ServiceAppointment(
            vehicle_code=req.vehicle_code,
            service_type=req.service_type,
            scheduled_date=date.fromisoformat(req.scheduled_date),
            scheduled_time=req.scheduled_time,
            technician_code=req.technician_code,
            urgency=req.urgency,
            notes=req.notes,
            warranty_covered=req.warranty_covered,
            status="confirmed",
        )
        logger.debug(
            f"book_appointment: adding ServiceAppointment to session "
            f"vehicle_code={req.vehicle_code!r} service_type={req.service_type!r}"
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        logger.info(
            f"book_appointment: appointment created appointment_id={appt.id} "
            f"vehicle_code={req.vehicle_code!r} date={req.scheduled_date!r}"
        )
        return {
            "booked": True,
            "appointment_id": appt.id,
            "vehicle_code":   appt.vehicle_code,
            "service_type":   appt.service_type,
            "date":           str(appt.scheduled_date),
            "time":           appt.scheduled_time,
            "technician":     appt.technician_code,
            "status":         appt.status,
        }
    except Exception as exc:
        db.rollback()
        logger.error(
            f"book_appointment: DB insert failed for vehicle_code={req.vehicle_code!r} "
            f"error={exc}"
        )
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    finally:
        db.close()
        logger.debug(f"book_appointment: SchedulerSession closed vehicle_code={req.vehicle_code!r}")


@router.get("/appointments/{vehicle_code}")
async def vehicle_appointments(vehicle_code: str):
    """List all appointments for a vehicle.

    Queries ``cs03_scheduler`` for all ``ServiceAppointment`` rows belonging
    to the given vehicle, ordered by ``scheduled_date`` ascending.

    Args:
        vehicle_code: The vehicle identifier to retrieve appointments for.

    Returns:
        dict: Contains ``vehicle_code`` (str) and ``appointments`` (list of dicts),
            each dict having: ``id``, ``service_type``, ``date``, ``time``,
            ``technician``, ``status``, ``urgency``.
    """
    logger.info(f"GET /api/scheduling/appointments/{vehicle_code}")

    logger.debug(
        f"vehicle_appointments: opening SchedulerSession for vehicle_code={vehicle_code!r}"
    )
    db = SchedulerSession()
    try:
        appts = (
            db.query(ServiceAppointment)
            .filter_by(vehicle_code=vehicle_code)
            .order_by(ServiceAppointment.scheduled_date.asc())
            .all()
        )
        logger.info(
            f"vehicle_appointments: found {len(appts)} appointments "
            f"vehicle_code={vehicle_code!r}"
        )
        return {
            "vehicle_code": vehicle_code,
            "appointments": [
                {
                    "id":           a.id,
                    "service_type": a.service_type,
                    "date":         str(a.scheduled_date),
                    "time":         a.scheduled_time,
                    "technician":   a.technician_code,
                    "status":       a.status,
                    "urgency":      a.urgency,
                }
                for a in appts
            ]
        }
    finally:
        db.close()
        logger.debug(
            f"vehicle_appointments: SchedulerSession closed vehicle_code={vehicle_code!r}"
        )
