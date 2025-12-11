"""SQLAlchemy models for trade requests and executions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TradeRequest(Base):
    """Model for pending trade approval requests."""
    __tablename__ = "trade_requests"

    id = Column(Integer, primary_key=True)
    trade_id = Column(String, unique=True, index=True, nullable=False)
    approval_code = Column(String, unique=True, index=True, nullable=False)
    
    # Trade details
    symbol = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)  # "BUY" or "SELL"
    quantity = Column(Integer, nullable=False)
    order_type = Column(String, nullable=False)  # "MARKET", "LIMIT", etc.
    price = Column(Float, nullable=True)  # Limit price if applicable
    
    # Status tracking
    status = Column(String, nullable=False, default="pending", index=True)  # pending, approved, rejected, expired
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Additional metadata
    forecast_id = Column(String, index=True, nullable=True)  # Link to forecast if applicable
    trade_details = Column(Text, nullable=True)  # JSON string for additional details
    paper_trading = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationship to executions
    executions = relationship("TradeExecution", back_populates="trade_request", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TradeRequest(trade_id='{self.trade_id}', symbol='{self.symbol}', status='{self.status}')>"


class TradeExecution(Base):
    """Model for executed trades (fills, IBKR responses)."""
    __tablename__ = "trade_executions"

    id = Column(Integer, primary_key=True)
    trade_request_id = Column(Integer, ForeignKey("trade_requests.id"), nullable=False, index=True)
    
    # Execution details
    symbol = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)  # "BUY" or "SELL"
    quantity = Column(Integer, nullable=False)
    execution_price = Column(Float, nullable=False)
    execution_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Broker response
    order_id = Column(String, index=True, nullable=True)  # IBKR order ID
    status = Column(String, nullable=False)  # "Filled", "PartiallyFilled", "Submitted", "Rejected", etc.
    broker_response = Column(Text, nullable=True)  # JSON string for full broker response
    
    # Additional metadata
    forecast_id = Column(String, index=True, nullable=True)  # Link to forecast if applicable
    paper_trading = Column(Boolean, default=False, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    
    # Relationship to trade request
    trade_request = relationship("TradeRequest", back_populates="executions")
    
    def __repr__(self):
        return f"<TradeExecution(trade_request_id={self.trade_request_id}, symbol='{self.symbol}', status='{self.status}')>"





