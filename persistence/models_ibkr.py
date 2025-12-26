"""SQLAlchemy models for IBKR connection status."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IBKRStatus(Base):
    """Model for tracking IBKR connection status."""
    __tablename__ = "ibkr_status"

    id = Column(Integer, primary_key=True)
    paper_trading = Column(Boolean, nullable=False, index=True)
    connected = Column(Boolean, nullable=False, default=False)
    host = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    client_id = Column(Integer, nullable=True)
    last_checked = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_connected = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    reconnect_attempts = Column(Integer, default=0, nullable=False)











