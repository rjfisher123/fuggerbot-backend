"""SQLAlchemy models for portfolio account state and positions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AccountState(Base):
    """Model representing overall account state."""
    __tablename__ = "account_state"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    cash = Column(Float, nullable=False, default=0.0)
    buying_power = Column(Float, nullable=False, default=0.0)

    realized_pnl = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)

    equity = Column(Float, nullable=False, default=0.0)


class Position(Base):
    """Model representing a portfolio position."""
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)

    quantity = Column(Float, nullable=False, default=0.0)
    avg_cost = Column(Float, nullable=False, default=0.0)

    market_value = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
