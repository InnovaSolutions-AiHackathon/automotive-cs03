from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from loguru import logger

# mysql+pymysql:// tells SQLAlchemy to use PyMySQL driver
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # check connection before use
    pool_recycle=3600,      # recycle connections every hour
    echo=(settings.ENVIRONMENT == "development")
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency — yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    from app.db import models  # import so Base sees all models
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("MySQL tables OK")
    except Exception as e:
        logger.error(f"DB error: {e}")