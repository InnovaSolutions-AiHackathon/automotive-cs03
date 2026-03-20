"""
FastAPI Application Entry Point — app/main.py

Bootstraps the Automotive CS03 AI Copilot web service:

    1. Initialises all per-agent MySQL schemas via ``create_all_schemas()``.
    2. Seeds default lookup data (technicians, DTC codes, warranty rules,
       insurance plans) into empty tables on first boot.
    3. Ingests the knowledge-base documents into ChromaDB for RAG queries.
    4. Registers all API routers with their URL prefixes.
    5. Adds CORS middleware using origins from ``settings.CORS_ORIGINS``.

Routers and prefixes:
    /api/agent       — multi-agent orchestrator (POST /ask)
    /api/vehicles    — vehicle lookup (GET /{vehicle_code})
    /api/warranty    — warranty check and records
    /api/scheduling  — slot availability and appointment booking
    /api/telematics  — real-time sensor data (delegated to telematics router)
    /api/user        — signup, login, /me
    /api/insurance   — insurance plans and quotes
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import agent, insurance, scheduling, telematics, user, vehicles, warranty
from app.config import settings
from app.db.database import create_all_schemas
from app.rag.ingest import ingest_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager — runs startup and shutdown logic.

    Startup sequence:
        1. Log startup banner.
        2. Initialise all MySQL schemas.
        3. Seed default data rows if tables are empty.
        4. Ingest knowledge-base documents into ChromaDB.

    Yields:
        Control back to FastAPI to serve requests.

    Shutdown:
        Logs a clean shutdown message.
    """
    logger.info("Automotive CS03 AI Copilot starting up...")

    # Initialise all per-agent MySQL schemas
    logger.info("lifespan: initialising MySQL schemas")
    create_all_schemas()

    # Seed default data (technicians, DTC codes, warranty rules) if empty
    logger.info("lifespan: seeding default lookup data")
    await _seed_defaults()

    # Load / index knowledge base into ChromaDB
    logger.info("lifespan: ingesting knowledge base into ChromaDB")
    await ingest_knowledge_base()

    logger.info("Startup complete — ready to serve")
    yield
    logger.info("Shutdown complete")


async def _seed_defaults() -> None:
    """Orchestrate seeding of all default lookup tables.

    Calls individual seed helpers for technicians, DTC codes, warranty rules,
    and insurance plans. Each helper is idempotent and skips seeding when rows
    already exist.
    """
    logger.debug("_seed_defaults: running all seed helpers")
    await _seed_technicians()
    await _seed_dtc_codes()
    await _seed_warranty_rules()
    await _seed_insurance_plans()
    logger.info("_seed_defaults: all seed helpers complete")


async def _seed_technicians() -> None:
    """Seed the ``technicians`` table with default workshop staff.

    Skips if the table already contains at least one row.
    Uses ``cs03_scheduler`` schema.

    Raises:
        Does not raise — warnings are logged on failure.
    """
    from app.db.database import SchedulerSession
    from app.db.schemas.scheduler import Technician

    logger.debug("_seed_technicians: checking technician count")
    db = SchedulerSession()
    try:
        count = db.query(Technician).count()
        logger.debug(f"_seed_technicians: existing count={count}")
        if count > 0:
            logger.info("_seed_technicians: table already populated, skipping")
            return
        seeds = [
            Technician(tech_code="T01_Kumar", name="Kumar",  specialties=["engine", "transmission", "drivetrain"]),
            Technician(tech_code="T02_Patel", name="Patel",  specialties=["electrical", "diagnostics"]),
            Technician(tech_code="T03_Ahmed", name="Ahmed",  specialties=["brakes", "suspension"]),
            Technician(tech_code="T04_Ramos", name="Ramos",  specialties=["ac", "interior", "general"]),
        ]
        db.add_all(seeds)
        db.commit()
        logger.info(f"Seeded {len(seeds)} technicians")
    except Exception as exc:
        logger.warning(f"Technician seeding skipped: {exc}")
    finally:
        db.close()


async def _seed_dtc_codes() -> None:
    """Seed the ``dtc_codes`` table with common OBD-II fault codes.

    Skips if the table already contains at least one row.
    Uses ``cs03_telematics`` schema.

    Raises:
        Does not raise — warnings are logged on failure.
    """
    from app.db.database import TelematicsSession
    from app.db.schemas.telematics import DTCCode

    logger.debug("_seed_dtc_codes: checking DTC code count")
    db = TelematicsSession()
    try:
        count = db.query(DTCCode).count()
        logger.debug(f"_seed_dtc_codes: existing count={count}")
        if count > 0:
            logger.info("_seed_dtc_codes: table already populated, skipping")
            return
        seeds = [
            DTCCode(code="P0300", desc="Random/Multiple Cylinder Misfire Detected",    severity="high",     system="engine"),
            DTCCode(code="P0171", desc="System Too Lean Bank 1",                      severity="medium",   system="engine"),
            DTCCode(code="P0420", desc="Catalyst System Efficiency Below Threshold",  severity="medium",   system="emission"),
            DTCCode(code="C0035", desc="Left Front Wheel Speed Sensor Circuit Fault", severity="high",     system="brakes"),
            DTCCode(code="B0001", desc="Driver Frontal Stage 1 Airbag Circuit Open",  severity="critical", system="airbag"),
            DTCCode(code="P0562", desc="System Voltage Low",                          severity="medium",   system="electrical"),
        ]
        db.add_all(seeds)
        db.commit()
        logger.info(f"Seeded {len(seeds)} DTC codes")
    except Exception as exc:
        logger.warning(f"DTC code seeding skipped: {exc}")
    finally:
        db.close()


async def _seed_insurance_plans() -> None:
    """Seed the ``insurance_plans`` table with standard plan tiers.

    Skips if the table already contains at least one row.
    Uses ``cs03_insurance`` schema.

    Raises:
        Does not raise — warnings are logged on failure.
    """
    from app.db.database import InsuranceSession
    from app.db.schemas.insurance import InsurancePlan

    logger.debug("_seed_insurance_plans: checking insurance plan count")
    db = InsuranceSession()
    try:
        count = db.query(InsurancePlan).count()
        logger.debug(f"_seed_insurance_plans: existing count={count}")
        if count > 0:
            logger.info("_seed_insurance_plans: table already populated, skipping")
            return
        seeds = [
            InsurancePlan(name="Basic Cover",    price=1500, duration="1 Year",  features=["Third-party liability", "Accidental damage"]),
            InsurancePlan(name="Standard Cover", price=2300, duration="1 Year",  features=["Third-party liability", "Accidental damage", "Theft", "Natural calamities"]),
            InsurancePlan(name="Premium Cover",  price=3500, duration="2 Years", features=["Full comprehensive", "Zero depreciation", "Roadside assistance", "Engine protection"]),
        ]
        db.add_all(seeds)
        db.commit()
        logger.info(f"Seeded {len(seeds)} insurance plans")
    except Exception as exc:
        logger.warning(f"Insurance plan seeding skipped: {exc}")
    finally:
        db.close()


async def _seed_warranty_rules() -> None:
    """Seed the ``warranty_rules`` table with coverage type definitions.

    Skips if the table already contains at least one row.
    Uses ``cs03_warranty`` schema.

    Raises:
        Does not raise — warnings are logged on failure.
    """
    from app.db.database import WarrantySession
    from app.db.schemas.warranty import WarrantyRule

    logger.debug("_seed_warranty_rules: checking warranty rule count")
    db = WarrantySession()
    try:
        count = db.query(WarrantyRule).count()
        logger.debug(f"_seed_warranty_rules: existing count={count}")
        if count > 0:
            logger.info("_seed_warranty_rules: table already populated, skipping")
            return
        seeds = [
            WarrantyRule(
                coverage_type="bumper_to_bumper",
                covered_types=["electrical", "interior", "ac", "brakes"],
                exclusions=["tires", "wiper_blades", "wear_items", "accident_damage"],
            ),
            WarrantyRule(
                coverage_type="powertrain",
                covered_types=["engine", "transmission", "drivetrain"],
                exclusions=["tires", "wiper_blades", "wear_items", "accident_damage"],
            ),
            WarrantyRule(
                coverage_type="emission",
                covered_types=["catalytic_converter", "o2_sensor"],
                exclusions=[],
            ),
        ]
        db.add_all(seeds)
        db.commit()
        logger.info(f"Seeded {len(seeds)} warranty rules")
    except Exception as exc:
        logger.warning(f"Warranty rule seeding skipped: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Automotive CS03 AI Copilot",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router,      prefix="/api/agent")
app.include_router(vehicles.router,   prefix="/api/vehicles")
app.include_router(warranty.router,   prefix="/api/warranty")
app.include_router(scheduling.router, prefix="/api/scheduling")
app.include_router(telematics.router, prefix="/api/telematics")
app.include_router(user.router,       prefix="/api/user")
app.include_router(insurance.router,  prefix="/api/insurance")

logger.info(
    f"FastAPI app configured: {len(app.routes)} routes registered, "
    f"CORS origins={settings.CORS_ORIGINS}"
)


@app.get("/")
async def health():
    """Health-check endpoint.

    Returns:
        dict: Service status, name, and version string.
    """
    logger.debug("Health check requested")
    return {"status": "ok", "service": "Automotive CS03 AI Copilot", "version": "2.0.0"}
