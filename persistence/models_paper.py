"""SQLAlchemy models for paper trading data."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    quantity = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)




