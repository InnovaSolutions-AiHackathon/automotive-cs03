"""
Insurance Agent Schema — cs03_insurance database.
Contains: InsurancePlan, VehicleInsurance
"""
from sqlalchemy import Column, Integer, String, Date, Boolean, DECIMAL, JSON, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

InsuranceBase = declarative_base()


class InsurancePlan(InsuranceBase):
    """Available insurance plans — replaces hardcoded plans list."""
    __tablename__ = "insurance_plans"

    id       = Column(Integer, primary_key=True)
    name     = Column(String(100), unique=True, nullable=False)
    price    = Column(DECIMAL(10, 2), nullable=False)
    duration = Column(String(20), nullable=False)   # e.g. "1 Year", "2 Years"
    features = Column(JSON)
    is_active = Column(Boolean, default=True)


class VehicleInsurance(InsuranceBase):
    """Active insurance policy for a vehicle."""
    __tablename__ = "vehicle_insurance"

    id          = Column(Integer, primary_key=True)
    vehicle_code = Column(String(20), nullable=False, index=True)
    provider    = Column(String(100), nullable=False)
    policy_no   = Column(String(50), unique=True, nullable=False)
    plan_name   = Column(String(100))
    start_date  = Column(Date, nullable=False)
    expires_on  = Column(Date, nullable=False)
    premium     = Column(DECIMAL(10, 2))
    status      = Column(Enum("active", "expired", "cancelled"), default="active", index=True)
    created_at  = Column(Date, server_default=func.current_date())
