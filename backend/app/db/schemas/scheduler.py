"""
Scheduler Agent Schema — cs03_scheduler database.
Contains: ServiceAppointment, Technician
"""
from sqlalchemy import Column, Integer, String, Date, Boolean, Text, Enum, JSON
from sqlalchemy.orm import declarative_base

SchedulerBase = declarative_base()


class Technician(SchedulerBase):
    """
    Technicians stored in DB — replaces the hardcoded TECHNICIANS dict.
    """
    __tablename__ = "technicians"

    id           = Column(Integer, primary_key=True)
    tech_code    = Column(String(20), unique=True, nullable=False, index=True)
    name         = Column(String(100), nullable=False)
    specialties  = Column(JSON, nullable=False)   # e.g. ["engine", "transmission"]
    is_active    = Column(Boolean, default=True)


class ServiceAppointment(SchedulerBase):
    __tablename__ = "service_appointments"

    id               = Column(Integer, primary_key=True)
    vehicle_code     = Column(String(20), nullable=False, index=True)
    service_type     = Column(String(100), nullable=False)
    scheduled_date   = Column(Date, nullable=False)
    scheduled_time   = Column(String(8), nullable=False)
    technician_code  = Column(String(20))
    bay              = Column(Integer)
    duration_hours   = Column(Integer, default=2)
    status           = Column(
        Enum("pending", "confirmed", "in_progress", "completed", "cancelled"),
        default="pending",
        index=True
    )
    urgency          = Column(Enum("critical", "high", "normal"), default="normal")
    warranty_covered = Column(Boolean, default=False)
    notes            = Column(Text)
