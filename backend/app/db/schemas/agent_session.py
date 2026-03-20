"""
Agent Session Schema — cs03_agent database.
Contains: AgentSession (conversation history per session)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

AgentBase = declarative_base()


class AgentSession(AgentBase):
    __tablename__ = "agent_sessions"

    id           = Column(Integer, primary_key=True)
    session_id   = Column(String(100), unique=True, nullable=False, index=True)
    vehicle_code = Column(String(20), index=True)
    user_id      = Column(Integer, index=True)
    history_json = Column(Text)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())
