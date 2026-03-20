"""
Telematics Agent Schema — cs03_telematics database.
Contains: DTCCode, TelematicsSnapshot
"""
from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

TelematicsBase = declarative_base()


class DTCCode(TelematicsBase):
    """
    OBD-II / DTC code reference table — replaces hardcoded DTC_DB dict.
    Seed with standard SAE J2012 codes via migration script.
    """
    __tablename__ = "dtc_codes"

    id       = Column(Integer, primary_key=True)
    code     = Column(String(10), unique=True, nullable=False, index=True)
    desc     = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False)   # critical | high | medium | low
    system   = Column(String(50), nullable=False)   # engine | brakes | electrical …
    notes    = Column(String(500))


class TelematicsSnapshot(TelematicsBase):
    """
    Point-in-time vehicle telemetry reading.
    Supports time-series queries per vehicle.
    """
    __tablename__ = "telematics_snapshots"

    id              = Column(Integer, primary_key=True)
    vehicle_code    = Column(String(20), nullable=False, index=True)
    recorded_at     = Column(DateTime, server_default=func.now(), index=True)
    fuel_level      = Column(Integer)
    battery_voltage = Column(DECIMAL(4, 2))
    engine_temp     = Column(Integer)
    oil_life        = Column(Integer)
    active_dtcs     = Column(JSON)   # list of DTC code strings
    raw_payload     = Column(JSON)   # full OBD-II payload for future use
