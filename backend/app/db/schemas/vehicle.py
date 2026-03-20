"""
Vehicle Agent Schema — cs03_vehicle database.
Contains: Customer, Vehicle, FaultCode
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

VehicleBase = declarative_base()


class Customer(VehicleBase):
    __tablename__ = "customers"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(150), unique=True, nullable=False, index=True)
    phone      = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

    vehicles = relationship("Vehicle", back_populates="customer", lazy="select")


class Vehicle(VehicleBase):
    __tablename__ = "vehicles"

    id              = Column(Integer, primary_key=True, index=True)
    vehicle_code    = Column(String(20), unique=True, nullable=False, index=True)
    vin             = Column(String(17), unique=True, nullable=False)
    make            = Column(String(50), nullable=False)
    model           = Column(String(50), nullable=False)
    year            = Column(Integer, nullable=False)
    odometer        = Column(Integer, default=0)
    purchase_date   = Column(Date, nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), index=True)
    fuel_level      = Column(Integer, default=100)
    battery_voltage = Column(DECIMAL(4, 2), default=12.6)
    engine_temp     = Column(Integer, default=90)
    oil_life        = Column(Integer, default=100)

    customer    = relationship("Customer", back_populates="vehicles")
    fault_codes = relationship("FaultCode", back_populates="vehicle", lazy="select")


class FaultCode(VehicleBase):
    __tablename__ = "active_fault_codes"

    id          = Column(Integer, primary_key=True)
    vehicle_id  = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    dtc_code    = Column(String(10), nullable=False, index=True)
    detected_at = Column(DateTime, server_default=func.now())
    resolved    = Column(Boolean, default=False, index=True)

    vehicle = relationship("Vehicle", back_populates="fault_codes")
