from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, Text, Enum, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Customer(Base):
    __tablename__ = "customers"
    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(150), unique=True, nullable=False)
    phone      = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())
    vehicles   = relationship("Vehicle", back_populates="customer")

class Vehicle(Base):
    __tablename__ = "vehicles"
    id              = Column(Integer, primary_key=True, index=True)
    vehicle_code    = Column(String(20), unique=True, nullable=False)
    vin             = Column(String(17), unique=True, nullable=False)
    make            = Column(String(50), nullable=False)
    model           = Column(String(50), nullable=False)
    year            = Column(Integer, nullable=False)
    odometer        = Column(Integer, default=0)
    purchase_date   = Column(Date, nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"))
    fuel_level      = Column(Integer, default=100)
    battery_voltage = Column(DECIMAL(4,2), default=12.6)
    engine_temp     = Column(Integer, default=90)
    oil_life        = Column(Integer, default=100)
    customer        = relationship("Customer", back_populates="vehicles")
    fault_codes     = relationship("FaultCode", back_populates="vehicle")
    warranties      = relationship("WarrantyRecord", back_populates="vehicle")

class FaultCode(Base):
    __tablename__ = "active_fault_codes"
    id          = Column(Integer, primary_key=True)
    vehicle_id  = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    dtc_code    = Column(String(10), nullable=False)
    detected_at = Column(DateTime, server_default=func.now())
    resolved    = Column(Boolean, default=False)
    vehicle     = relationship("Vehicle", back_populates="fault_codes")

class WarrantyRecord(Base):
    __tablename__ = "warranty_records"
    id             = Column(Integer, primary_key=True)
    vehicle_id     = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    coverage_type  = Column(String(50), nullable=False)
    start_date     = Column(Date, nullable=False)
    end_date       = Column(Date, nullable=False)
    mileage_limit  = Column(Integer, nullable=False)
    is_extended    = Column(Boolean, default=False)
    vehicle        = relationship("Vehicle", back_populates="warranties")

class ServiceAppointment(Base):
    __tablename__ = "service_appointments"
    id               = Column(Integer, primary_key=True)
    vehicle_id       = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    service_type     = Column(String(100), nullable=False)
    scheduled_date   = Column(Date, nullable=False)
    scheduled_time   = Column(String(8), nullable=False)
    technician       = Column(String(50))
    status           = Column(Enum("pending","confirmed","in_progress","completed"), default="pending")
    warranty_covered = Column(Boolean, default=False)
    notes            = Column(Text)

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id           = Column(Integer, primary_key=True)
    session_id   = Column(String(100), unique=True, nullable=False)
    vehicle_id   = Column(String(20))
    history_json = Column(Text)
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())