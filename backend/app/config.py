"""
Application Configuration — app/config.py

Loads all environment variables via pydantic-settings (reads from .env file).
Provides a single ``settings`` singleton used throughout the backend.

Responsibilities:
    - LLM provider credentials (Anthropic Claude, Google Gemini)
    - MySQL connection parameters (one server, multiple per-agent schemas)
    - ChromaDB path for vector-store RAG
    - JWT / auth settings
    - Environment / CORS configuration

DB schemas managed:
    - cs03_vehicle, cs03_warranty, cs03_scheduler, cs03_telematics,
      cs03_auth, cs03_agent, cs03_insurance
"""
from __future__ import annotations

import logging
from typing import List

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Pydantic-settings model for all application configuration.

    All values are read from environment variables or the .env file at startup.
    Sensitive fields (API keys, passwords, SECRET_KEY) have no default values
    so the application will fail fast if they are missing.

    Attributes:
        ANTHROPIC_API_KEY: API key for Anthropic Claude LLM.
        CLAUDE_MODEL: Anthropic model identifier to use.
        GEMINI_API_KEY: API key for Google Gemini LLM.
        GEMINI_MODEL: Gemini model identifier to use.
        MYSQL_USER: MySQL username for all schema connections.
        MYSQL_PASSWORD: MySQL password (required, no default).
        MYSQL_HOST: MySQL host address.
        MYSQL_PORT: MySQL port number.
        MYSQL_DB_VEHICLE: Schema name for vehicle data.
        MYSQL_DB_WARRANTY: Schema name for warranty data.
        MYSQL_DB_SCHEDULER: Schema name for scheduling data.
        MYSQL_DB_TELEMATICS: Schema name for telematics/DTC data.
        MYSQL_DB_AUTH: Schema name for authentication/users.
        MYSQL_DB_AGENT: Schema name for agent session history.
        MYSQL_DB_INSURANCE: Schema name for insurance plans.
        CHROMA_PATH: Filesystem path for ChromaDB vector store.
        KNOWLEDGE_DIR: Directory containing knowledge-base documents to ingest.
        ENVIRONMENT: Runtime environment label (development/production).
        CORS_ORIGINS: List of allowed CORS origins.
        SECRET_KEY: HMAC secret for JWT signing (required, no default).
        JWT_ALGORITHM: Algorithm used to sign JWTs.
        ACCESS_TOKEN_EXPIRE_MINUTES: JWT lifetime in minutes.
    """

    # ------------------------------------------------------------------
    # LLM providers — values MUST come from .env (no hardcoded fallback)
    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-5"

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"

    # ------------------------------------------------------------------
    # MySQL — one server, per-agent schemas
    # ------------------------------------------------------------------
    MYSQL_USER: str = "cs03_user"
    MYSQL_PASSWORD: str
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306

    # Per-agent database schemas
    MYSQL_DB_VEHICLE: str = "cs03_vehicle"
    MYSQL_DB_WARRANTY: str = "cs03_warranty"
    MYSQL_DB_SCHEDULER: str = "cs03_scheduler"
    MYSQL_DB_TELEMATICS: str = "cs03_telematics"
    MYSQL_DB_AUTH: str = "cs03_auth"
    MYSQL_DB_AGENT: str = "cs03_agent"
    MYSQL_DB_INSURANCE: str = "cs03_insurance"

    # ------------------------------------------------------------------
    # ChromaDB
    # ------------------------------------------------------------------
    CHROMA_PATH: str = "./chroma_db"
    KNOWLEDGE_DIR: str = "./knowledge_base"

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:4200"]
    SECRET_KEY: str  # used for JWT — no fallback

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def db_url(self, schema: str) -> str:
        """Build a SQLAlchemy connection URL for the given schema.

        Args:
            schema: The MySQL database/schema name to connect to.

        Returns:
            A fully-qualified ``mysql+pymysql://`` connection string.
        """
        url = (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{schema}"
        )
        logger.debug(f"Built DB URL for schema='{schema}' host={self.MYSQL_HOST}:{self.MYSQL_PORT}")
        return url

    @property
    def is_development(self) -> bool:
        """Return True when running in development mode (enables SQLAlchemy echo).

        Returns:
            bool: True if ENVIRONMENT is 'development' (case-insensitive).
        """
        return self.ENVIRONMENT.lower() == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
logger.info(
    f"Settings loaded: environment={settings.ENVIRONMENT} "
    f"gemini_model={settings.GEMINI_MODEL} "
    f"mysql_host={settings.MYSQL_HOST}:{settings.MYSQL_PORT}"
)
