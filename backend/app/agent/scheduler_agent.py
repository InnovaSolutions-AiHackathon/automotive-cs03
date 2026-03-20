"""
Scheduler Agent — app/agent/scheduler_agent.py

Specialist agent that suggests available service slots and, when the user
explicitly requests a booking, creates a confirmed ``ServiceAppointment``
record in the ``cs03_scheduler`` database.

Processing flow:
    1. Infer ``service_type`` and ``urgency`` from the message or context.
    2. Detect whether the user is requesting an actual booking.
    3. Call ``scheduler.get_slots`` to retrieve available technician slots.
    4. If booking intent detected AND vehicle code is available: persist an
       appointment row and return a confirmation.
    5. Otherwise: return the next available slot with a booking prompt.

DB schema used:
    cs03_scheduler — ``service_appointments`` and ``technicians`` tables via
    ``app.db.schemas.scheduler.ServiceAppointment`` and ``Technician``.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.services.scheduler import get_slots
from app.db.database import SchedulerSession
from app.db.schemas.scheduler import ServiceAppointment

logger = logging.getLogger(__name__)

_URGENCY_KEYWORDS = {
    "critical": ["critical", "emergency", "urgent", "breakdown", "not starting", "won't start", "overheating"],
    "high":     ["high", "asap", "today", "soon", "immediately"],
}

_BOOKING_KEYWORDS = ["book", "schedule", "arrange", "make an appointment", "create", "set up", "fix me a slot"]


class SchedulerAgent:
    """Agent that provides service slot recommendations and auto-books appointments.

    This agent is stateless — a fresh instance is created per request via
    the ``get_scheduler_agent`` factory.
    """

    async def process_query(
        self, user_message: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Suggest or book a service appointment based on the user's request.

        Args:
            user_message: The user's natural-language scheduling query.
            context: Request context dict with optional keys:
                - ``vehicle_id`` (str) — vehicle code; required for auto-booking.
                - ``service_type`` (str) — explicit service category.
                - ``urgency`` (str) — explicit urgency level.

        Returns:
            dict[str, Any]: Contains ``"response"`` (str) and ``"sources"``
                (list[str]).  When an appointment is auto-booked, also includes
                ``"appointment"`` (dict) with booking details.
                When only showing slots, also includes ``"slots"`` (list).

            On slot lookup failure, returns a graceful message directing the
            user to call the service centre.
        """
        service_type = context.get("service_type") or self._infer_service_type(user_message)
        urgency      = context.get("urgency")      or self._infer_urgency(user_message)
        vehicle_code = context.get("vehicle_id")
        is_booking   = self._is_booking_intent(user_message)

        logger.info(
            f"[SchedulerAgent] process_query vehicle_code={vehicle_code!r} "
            f"service_type={service_type!r} urgency={urgency!r} "
            f"is_booking={is_booking} "
            f"message_preview={user_message[:80]!r}"
        )

        try:
            logger.debug(
                f"[SchedulerAgent] calling get_slots service_type={service_type!r} "
                f"urgency={urgency!r}"
            )
            result = await get_slots(service_type, urgency)
            slots  = result.get("slots", [])

            logger.info(
                f"[SchedulerAgent] get_slots returned {len(slots)} slot(s) "
                f"service_type={service_type!r} urgency={urgency!r}"
            )

            if not slots:
                logger.warning(
                    f"[SchedulerAgent] no slots available for "
                    f"service_type={service_type!r} urgency={urgency!r}"
                )
                return {
                    "response": "No available slots found for the requested service. Please call the service centre directly.",
                    "sources": ["cs03_scheduler DB"],
                }

            first = slots[0]
            logger.debug(
                f"[SchedulerAgent] first slot: date={first['date']} time={first['time']} "
                f"technician={first.get('technician_name')!r}"
            )

            # AUTO-BOOK if user explicitly requested it and we have a vehicle_code
            if is_booking and vehicle_code:
                logger.info(
                    f"[SchedulerAgent] auto-booking appointment for "
                    f"vehicle_code={vehicle_code!r} slot_date={first['date']} "
                    f"slot_time={first['time']}"
                )
                appointment = self._create_appointment(
                    vehicle_code=vehicle_code,
                    service_type=service_type,
                    slot=first,
                    urgency=urgency,
                )
                logger.info(
                    f"[SchedulerAgent] appointment created appointment_id={appointment.id} "
                    f"vehicle_code={vehicle_code!r}"
                )
                return {
                    "response": (
                        f"Appointment CONFIRMED for {vehicle_code}.\n"
                        f"Service: {service_type.replace('_', ' ').title()}\n"
                        f"Date: {first['date']} at {first['time']}\n"
                        f"Technician: {first['technician_name']} | Bay: {first['bay']}\n"
                        f"Urgency: {urgency.upper()}\n"
                        f"Booking ID: {appointment.id}"
                    ),
                    "appointment": {
                        "id":         appointment.id,
                        "date":       str(appointment.scheduled_date),
                        "time":       appointment.scheduled_time,
                        "technician": first["technician_name"],
                        "bay":        appointment.bay,
                        "status":     appointment.status,
                        "urgency":    appointment.urgency,
                    },
                    "sources": ["cs03_scheduler DB"],
                }

            # Otherwise just show next available slot
            logger.info(
                f"[SchedulerAgent] returning slot suggestion (no booking) "
                f"total_slots={len(slots)}"
            )
            lines = [
                f"Next available slot for **{service_type.replace('_', ' ').title()}** ({urgency} priority):",
                f"  📅 {first['date']} at {first['time']}",
                f"  👨‍🔧 Technician: {first['technician_name']} | Bay: {first['bay']}",
            ]
            if len(slots) > 1:
                lines.append(f"  ({len(slots) - 1} more slots available — say 'book this' to confirm.)")

            return {
                "response":    "\n".join(lines),
                "slots":       slots,
                "sources":     ["cs03_scheduler DB"],
            }

        except Exception as exc:
            logger.error(
                f"[SchedulerAgent] error processing scheduling query: {exc}"
            )
            return {
                "response": "Unable to retrieve scheduling information. Please try again.",
                "sources": [],
            }

    def _create_appointment(
        self, vehicle_code: str, service_type: str, slot: dict, urgency: str
    ) -> ServiceAppointment:
        """Persist a new confirmed service appointment to ``cs03_scheduler``.

        Args:
            vehicle_code: The vehicle identifier for the appointment.
            service_type: The service category string (underscores allowed).
            slot: A slot dict from ``get_slots`` containing ``date``, ``time``,
                ``technician_code``, ``bay``, and ``duration_hours``.
            urgency: Urgency level string (``'critical'``, ``'high'``, or
                ``'normal'``).

        Returns:
            ServiceAppointment: The freshly committed and refreshed ORM instance.

        Raises:
            Exception: Re-raises any DB exception after the ``finally`` block
                closes the session.
        """
        logger.debug(
            f"_create_appointment: opening SchedulerSession "
            f"vehicle_code={vehicle_code!r} service_type={service_type!r}"
        )
        db = SchedulerSession()
        try:
            appt = ServiceAppointment(
                vehicle_code    = vehicle_code,
                service_type    = service_type.replace("_", " ").title(),
                scheduled_date  = date.fromisoformat(slot["date"]),
                scheduled_time  = slot["time"],
                technician_code = slot["technician_code"],
                bay             = slot["bay"],
                duration_hours  = slot["duration_hours"],
                status          = "confirmed",
                urgency         = urgency if urgency in ("critical", "high", "normal") else "normal",
                notes           = f"Auto-booked via AI Copilot",
            )
            db.add(appt)
            db.commit()
            db.refresh(appt)
            logger.debug(
                f"_create_appointment: committed appointment_id={appt.id} "
                f"vehicle_code={vehicle_code!r}"
            )
            return appt
        finally:
            db.close()
            logger.debug(
                f"_create_appointment: SchedulerSession closed vehicle_code={vehicle_code!r}"
            )

    @staticmethod
    def _is_booking_intent(message: str) -> bool:
        """Detect whether the message contains an explicit booking request.

        Args:
            message: The user's natural-language message.

        Returns:
            bool: ``True`` if any booking keyword is found in the lowercased
                message.
        """
        msg = message.lower()
        result = any(k in msg for k in _BOOKING_KEYWORDS)
        logger.debug(f"_is_booking_intent: result={result}")
        return result

    @staticmethod
    def _infer_service_type(message: str) -> str:
        """Infer the service type category from the message using keyword matching.

        Args:
            message: The user's natural-language message.

        Returns:
            str: A service type string such as ``'engine'``, ``'brakes'``, or
                ``'general'`` as the default fallback.
        """
        msg = message.lower()
        if any(k in msg for k in ["engine", "misfire", "overheating", "temperature", "cooling", "thermostat"]):
            logger.debug("_infer_service_type: matched 'engine'")
            return "engine"
        if any(k in msg for k in ["brake", "pad", "rotor", "abs"]):
            logger.debug("_infer_service_type: matched 'brakes'")
            return "brakes"
        if any(k in msg for k in ["electric", "battery", "wiring", "voltage"]):
            logger.debug("_infer_service_type: matched 'electrical'")
            return "electrical"
        if any(k in msg for k in ["ac", "air condition", "hvac", "cooling"]):
            logger.debug("_infer_service_type: matched 'ac'")
            return "ac"
        if any(k in msg for k in ["oil", "lube", "fluid"]):
            logger.debug("_infer_service_type: matched 'oil_change'")
            return "oil_change"
        if any(k in msg for k in ["tyre", "tire", "wheel"]):
            logger.debug("_infer_service_type: matched 'tyres'")
            return "tyres"
        logger.debug("_infer_service_type: no match — defaulting to 'general'")
        return "general"

    @staticmethod
    def _infer_urgency(message: str) -> str:
        """Infer the urgency level from the message using keyword matching.

        Checks ``_URGENCY_KEYWORDS`` levels in descending severity order.

        Args:
            message: The user's natural-language message.

        Returns:
            str: ``'critical'``, ``'high'``, or ``'normal'`` (default fallback).
        """
        msg = message.lower()
        for level, keywords in _URGENCY_KEYWORDS.items():
            if any(k in msg for k in keywords):
                logger.debug(f"_infer_urgency: matched level={level!r}")
                return level
        logger.debug("_infer_urgency: no match — defaulting to 'normal'")
        return "normal"


def get_scheduler_agent() -> SchedulerAgent:
    """Factory function — create a new stateless SchedulerAgent instance.

    Returns:
        SchedulerAgent: Fresh instance ready to process a single query.
    """
    logger.debug("get_scheduler_agent: creating new SchedulerAgent instance")
    return SchedulerAgent()
