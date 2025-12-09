"""SQLAlchemy models for backtest results."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Backtest(Base):
    """Model for storing backtest evaluation results."""
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True)
    backtest_id = Column(String, unique=True, nullable=False, index=True)  # Unique ID from domain model
    forecast_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    horizon = Column(Integer, nullable=False)
    
    # Store realised series as JSON string
    realised_series = Column(Text, nullable=False)  # JSON array of floats
    
    # Store metrics as JSON string
    metrics = Column(Text, nullable=False)  # JSON object with all metrics
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Additional metadata as JSON
    backtest_metadata = Column(Text, nullable=True)  # JSON object for additional metadata

