# Per-agent database schema models.
# Each module defines its own SQLAlchemy Base, bound to a separate MySQL schema.
from app.db.schemas.vehicle import VehicleBase, Customer, Vehicle, FaultCode
from app.db.schemas.warranty import WarrantyBase, WarrantyRecord
from app.db.schemas.scheduler import SchedulerBase, ServiceAppointment, Technician
from app.db.schemas.telematics import TelematicsBase, DTCCode
from app.db.schemas.auth import AuthBase, User
from app.db.schemas.agent_session import AgentBase, AgentSession

__all__ = [
    "VehicleBase", "Customer", "Vehicle", "FaultCode",
    "WarrantyBase", "WarrantyRecord",
    "SchedulerBase", "ServiceAppointment", "Technician",
    "TelematicsBase", "DTCCode",
    "AuthBase", "User",
    "AgentBase", "AgentSession",
]
