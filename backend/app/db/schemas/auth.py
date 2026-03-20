"""
Auth Schema — cs03_auth database.
Contains: User
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

AuthBase = declarative_base()


class User(AuthBase):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name  = Column(String(50), nullable=False)
    email      = Column(String(150), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)   # bcrypt hash — never plaintext
    mobile     = Column(String(20))
    role       = Column(Enum("agent", "supervisor", "admin"), default="agent")
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
