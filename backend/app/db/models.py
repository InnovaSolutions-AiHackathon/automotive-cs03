"""
Backward-compatibility re-exports.
New code should import directly from app.db.schemas.<module>.
"""
from app.db.schemas.vehicle import VehicleBase as Base, Customer, Vehicle, FaultCode
from app.db.schemas.warranty import WarrantyRecord, WarrantyRule
from app.db.schemas.scheduler import ServiceAppointment, Technician
from app.db.schemas.telematics import DTCCode, TelematicsSnapshot
from app.db.schemas.auth import User
from app.db.schemas.agent_session import AgentSession

__all__ = [
    "Base",
    "Customer", "Vehicle", "FaultCode",
    "WarrantyRecord", "WarrantyRule",
    "ServiceAppointment", "Technician",
    "DTCCode", "TelematicsSnapshot",
    "User",
    "AgentSession",
]
