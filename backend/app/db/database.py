"""
Database Engine and Session Factories — app/db/database.py

Creates one SQLAlchemy engine per agent schema and exposes:
    - Named ``sessionmaker`` factories (VehicleSession, WarrantySession, etc.)
    - FastAPI ``Depends``-compatible generator helpers (get_db, get_auth_db, etc.)
    - ``create_all_schemas()`` called at app startup to initialise all tables

All schemas reside on the same MySQL server but in separate databases, giving
each agent its own isolated namespace:

    cs03_vehicle    — vehicles, customers, fault_codes
    cs03_warranty   — warranty_records, warranty_rules
    cs03_scheduler  — service_appointments, technicians
    cs03_telematics — dtc_codes
    cs03_auth       — users
    cs03_agent      — agent_sessions (conversation history)
    cs03_insurance  — insurance_plans, insurance_quotes
"""
from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from app.config import settings

# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def _make_engine(schema: str) -> Engine:
    """Create a SQLAlchemy engine for a given MySQL schema.

    Args:
        schema: The MySQL database name (e.g. ``'cs03_vehicle'``).

    Returns:
        A configured :class:`sqlalchemy.engine.Engine` with connection-pool
        settings appropriate for a long-running web service.
    """
    url = settings.db_url(schema)
    logger.debug(f"Creating engine for schema='{schema}'")
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        echo=settings.is_development,
    )
    logger.info(f"Engine created for schema='{schema}' pool_size=5 max_overflow=10")
    return engine


# ---------------------------------------------------------------------------
# Per-agent engines (one schema each)
# ---------------------------------------------------------------------------

vehicle_engine    = _make_engine(settings.MYSQL_DB_VEHICLE)
warranty_engine   = _make_engine(settings.MYSQL_DB_WARRANTY)
scheduler_engine  = _make_engine(settings.MYSQL_DB_SCHEDULER)
telematics_engine = _make_engine(settings.MYSQL_DB_TELEMATICS)
auth_engine       = _make_engine(settings.MYSQL_DB_AUTH)
agent_engine      = _make_engine(settings.MYSQL_DB_AGENT)
insurance_engine  = _make_engine(settings.MYSQL_DB_INSURANCE)

# ---------------------------------------------------------------------------
# Session factories
# ---------------------------------------------------------------------------

VehicleSession    = sessionmaker(autocommit=False, autoflush=False, bind=vehicle_engine)
WarrantySession   = sessionmaker(autocommit=False, autoflush=False, bind=warranty_engine)
SchedulerSession  = sessionmaker(autocommit=False, autoflush=False, bind=scheduler_engine)
TelematicsSession = sessionmaker(autocommit=False, autoflush=False, bind=telematics_engine)
AuthSession       = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)
AgentSession_SM   = sessionmaker(autocommit=False, autoflush=False, bind=agent_engine)
InsuranceSession  = sessionmaker(autocommit=False, autoflush=False, bind=insurance_engine)

# Legacy alias — kept so existing code that imports SessionLocal still works
SessionLocal = VehicleSession


# ---------------------------------------------------------------------------
# FastAPI dependency helpers (yield-based)
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a vehicle-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_vehicle``.
    """
    logger.debug("get_db: opening VehicleSession")
    db = VehicleSession()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_db: VehicleSession closed")


def get_warranty_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a warranty-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_warranty``.
    """
    logger.debug("get_warranty_db: opening WarrantySession")
    db = WarrantySession()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_warranty_db: WarrantySession closed")


def get_scheduler_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a scheduler-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_scheduler``.
    """
    logger.debug("get_scheduler_db: opening SchedulerSession")
    db = SchedulerSession()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_scheduler_db: SchedulerSession closed")


def get_telematics_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a telematics-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_telematics``.
    """
    logger.debug("get_telematics_db: opening TelematicsSession")
    db = TelematicsSession()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_telematics_db: TelematicsSession closed")


def get_auth_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields an auth-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_auth``.
    """
    logger.debug("get_auth_db: opening AuthSession")
    db = AuthSession()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_auth_db: AuthSession closed")


def get_agent_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields an agent-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_agent``.
    """
    logger.debug("get_agent_db: opening AgentSession_SM")
    db = AgentSession_SM()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_agent_db: AgentSession_SM closed")


def get_insurance_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields an insurance-schema DB session.

    Yields:
        Session: An active SQLAlchemy session bound to ``cs03_insurance``.
    """
    logger.debug("get_insurance_db: opening InsuranceSession")
    db = InsuranceSession()
    try:
        yield db
    finally:
        db.close()
        logger.debug("get_insurance_db: InsuranceSession closed")


# ---------------------------------------------------------------------------
# Schema initialisation (called at app startup)
# ---------------------------------------------------------------------------

def create_all_schemas() -> None:
    """Create tables in every agent schema. Idempotent — safe to call on every boot.

    Iterates over all (Base, engine, name) pairs and calls
    ``metadata.create_all()``. Any schema that already has its tables will
    be left unchanged by SQLAlchemy.

    Raises:
        Does not raise — errors are caught and logged per-schema so a single
        failing schema does not block the rest of the startup sequence.
    """
    logger.info("create_all_schemas: starting table initialisation for all schemas")

    from app.db.schemas.vehicle import VehicleBase
    from app.db.schemas.warranty import WarrantyBase
    from app.db.schemas.scheduler import SchedulerBase
    from app.db.schemas.telematics import TelematicsBase
    from app.db.schemas.auth import AuthBase
    from app.db.schemas.agent_session import AgentBase
    from app.db.schemas.insurance import InsuranceBase

    schema_map = [
        (VehicleBase,    vehicle_engine,    settings.MYSQL_DB_VEHICLE),
        (WarrantyBase,   warranty_engine,   settings.MYSQL_DB_WARRANTY),
        (SchedulerBase,  scheduler_engine,  settings.MYSQL_DB_SCHEDULER),
        (TelematicsBase, telematics_engine, settings.MYSQL_DB_TELEMATICS),
        (AuthBase,       auth_engine,       settings.MYSQL_DB_AUTH),
        (AgentBase,      agent_engine,      settings.MYSQL_DB_AGENT),
        (InsuranceBase,  insurance_engine,  settings.MYSQL_DB_INSURANCE),
    ]

    success_count = 0
    for base, engine, name in schema_map:
        try:
            logger.debug(f"create_all_schemas: initialising schema='{name}'")
            base.metadata.create_all(bind=engine)
            logger.info(f"Schema '{name}' tables OK")
            success_count += 1
        except Exception as exc:
            logger.error(f"Schema '{name}' init failed: {exc}")

    logger.info(f"create_all_schemas: complete — {success_count}/{len(schema_map)} schemas OK")


# Keep the old helper so main.py / legacy code still compiles
def create_tables() -> None:
    """Alias for ``create_all_schemas()`` — retained for backwards compatibility.

    Deprecated:
        Use ``create_all_schemas()`` directly in new code.
    """
    logger.debug("create_tables: delegating to create_all_schemas()")
    create_all_schemas()
