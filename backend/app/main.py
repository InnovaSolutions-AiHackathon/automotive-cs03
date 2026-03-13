from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api import agent, vehicles, warranty, scheduling, telematics
from app.config import settings
from app.db.database import create_tables
from app.rag.ingest import ingest_knowledge_base
from loguru import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚗 Automotive CS03 starting up...")
    create_tables()
    logger.info("✅ MySQL tables verified")
    await ingest_knowledge_base()
    logger.info("✅ Knowledge base loaded")
    yield
    logger.info("👋 Shutdown complete")

app = FastAPI(
    title="Automotive CS03 AI Copilot",
    version="1.0.0",
    lifespan=lifespan
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

@app.get("/")
async def health():
    return {"status": "ok", "service": "Automotive CS03"}