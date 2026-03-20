"""
Warranty Agent Schema — cs03_warranty database.
Contains: WarrantyRecord, WarrantyRule
"""
from sqlalchemy import Column, Integer, String, Date, Boolean, Text, JSON
from sqlalchemy.orm import declarative_base

WarrantyBase = declarative_base()


class WarrantyRecord(WarrantyBase):
    __tablename__ = "warranty_records"

    id            = Column(Integer, primary_key=True)
    vehicle_code  = Column(String(20), nullable=False, index=True)
    coverage_type = Column(String(50), nullable=False)
    start_date    = Column(Date, nullable=False)
    end_date      = Column(Date, nullable=False)
    mileage_limit = Column(Integer, nullable=False)
    is_extended   = Column(Boolean, default=False)


class WarrantyRule(WarrantyBase):
    """
    Configurable warranty coverage rules stored in DB — no more hardcoded COVERAGE_MAP.
    Each row maps a coverage_type to a JSON list of covered repair types.
    """
    __tablename__ = "warranty_rules"

    id            = Column(Integer, primary_key=True)
    coverage_type = Column(String(50), unique=True, nullable=False)
    covered_types = Column(JSON, nullable=False)   # e.g. ["engine", "transmission"]
    exclusions    = Column(JSON, nullable=False, default=list)  # e.g. ["tires"]
    notes         = Column(Text)
