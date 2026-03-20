"""
Legacy shim — do not use in new code.
Import from app.db.database instead.
"""
from app.db.database import (  # noqa: F401  (re-export for backward compatibility)
    SessionLocal,
    get_db,
    create_tables,
)
