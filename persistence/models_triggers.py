"""SQLAlchemy models for trigger events, results, and trade candidates."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TriggerEvent(Base):
    """Model for tracking when triggers fire."""
    __tablename__ = "trigger_events"

    id = Column(Integer, primary_key=True)
    trigger_id = Column(String, nullable=False, index=True)  # ID of the trigger that fired
    symbol = Column(String, index=True, nullable=False)
    condition = Column(String, nullable=False)  # "<", ">", "drop_pct", "rise_pct"
    threshold_value = Column(Float, nullable=False)
    action = Column(String, nullable=False)  # "notify", "buy", "sell", "layer_in"
    current_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    event_metadata = Column(Text, nullable=True)  # JSON string for additional data


class TriggerResult(Base):
    """Model for storing trigger evaluation results with data snapshots."""
    __tablename__ = "trigger_results"

    id = Column(Integer, primary_key=True)
    trigger_id = Column(String, nullable=False, index=True)  # ID of the trigger
    fired_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    data_snapshot = Column(Text, nullable=False)  # JSON string with snapshot of trigger data at time of firing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to trade candidates
    trade_candidates = relationship("TradeCandidate", back_populates="trigger_result", cascade="all, delete-orphan")


class TradeCandidate(Base):
    """Model for trade candidates generated from trigger results."""
    __tablename__ = "trade_candidates"

    id = Column(Integer, primary_key=True)
    trigger_result_id = Column(Integer, ForeignKey("trigger_results.id"), nullable=False, index=True)
    trigger_id = Column(String, nullable=False, index=True)  # ID of the trigger that generated this candidate
    symbol = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # "BUY", "SELL", "HOLD"
    confidence = Column(Float, nullable=False)  # Confidence score (0.0 to 1.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    candidate_metadata = Column(Text, nullable=True)  # JSON string for additional data

    # Relationship to trigger result
    trigger_result = relationship("TriggerResult", back_populates="trade_candidates")

