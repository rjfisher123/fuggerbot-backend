"""Repository classes for trade requests and executions."""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from persistence.models_trades import TradeRequest, TradeExecution


class TradeRequestRepository:
    """Repository for managing trade requests."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_trade_request(
        self,
        trade_id: str,
        approval_code: str,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str,
        price: Optional[float] = None,
        expires_at: Optional[datetime] = None,
        forecast_id: Optional[str] = None,
        trade_details: Optional[Dict[str, Any]] = None,
        paper_trading: bool = False
    ) -> TradeRequest:
        """
        Add a new trade request.
        
        Args:
            trade_id: Unique trade identifier
            approval_code: Approval code for this request
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares
            order_type: MARKET, LIMIT, etc.
            price: Limit price if applicable
            expires_at: When the request expires
            forecast_id: Optional forecast ID
            trade_details: Optional additional details dict
            paper_trading: Whether this is paper trading
        
        Returns:
            Created TradeRequest
        """
        trade_request = TradeRequest(
            trade_id=trade_id,
            approval_code=approval_code,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            price=price,
            expires_at=expires_at,
            forecast_id=forecast_id,
            trade_details=json.dumps(trade_details) if trade_details else None,
            paper_trading=paper_trading,
            status="pending"
        )
        self.session.add(trade_request)
        self.session.commit()
        self.session.refresh(trade_request)
        return trade_request
    
    def list_pending_requests(
        self,
        paper_trading: Optional[bool] = None,
        include_expired: bool = False
    ) -> List[TradeRequest]:
        """
        List all pending trade requests.
        
        Args:
            paper_trading: Filter by paper trading (None = all)
            include_expired: Whether to include expired requests
        
        Returns:
            List of pending TradeRequest objects
        """
        query = self.session.query(TradeRequest).filter(TradeRequest.status == "pending")
        
        if paper_trading is not None:
            query = query.filter(TradeRequest.paper_trading == paper_trading)
        
        if not include_expired:
            now = datetime.utcnow()
            query = query.filter(
                (TradeRequest.expires_at.is_(None)) | (TradeRequest.expires_at > now)
            )
        
        return query.order_by(desc(TradeRequest.requested_at)).all()
    
    def get_by_trade_id(self, trade_id: str) -> Optional[TradeRequest]:
        """Get trade request by trade_id."""
        return self.session.query(TradeRequest).filter(TradeRequest.trade_id == trade_id).first()
    
    def get_by_approval_code(self, approval_code: str) -> Optional[TradeRequest]:
        """Get trade request by approval_code."""
        return self.session.query(TradeRequest).filter(TradeRequest.approval_code == approval_code).first()
    
    def update_request_status(
        self,
        trade_id: str,
        status: str,
        approval_code: Optional[str] = None
    ) -> Optional[TradeRequest]:
        """
        Update trade request status.
        
        Args:
            trade_id: Trade ID or approval code
            status: New status (approved, rejected, expired)
            approval_code: Optional approval code (for lookup if trade_id is approval_code)
        
        Returns:
            Updated TradeRequest or None if not found
        """
        # Try to find by trade_id first, then by approval_code
        trade_request = self.get_by_trade_id(trade_id)
        if not trade_request:
            if approval_code:
                trade_request = self.get_by_approval_code(approval_code)
            else:
                trade_request = self.get_by_approval_code(trade_id)
        
        if not trade_request:
            return None
        
        trade_request.status = status
        
        if status == "approved":
            trade_request.approved_at = datetime.utcnow()
        elif status == "rejected":
            trade_request.rejected_at = datetime.utcnow()
        elif status == "expired":
            # Expired timestamp already set via expires_at
            pass
        
        self.session.commit()
        self.session.refresh(trade_request)
        return trade_request
    
    def list_all(
        self,
        paper_trading: Optional[bool] = None,
        limit: int = 100
    ) -> List[TradeRequest]:
        """
        List all trade requests (not just pending).
        
        Args:
            paper_trading: Filter by paper trading (None = all)
            limit: Maximum number to return
        
        Returns:
            List of TradeRequest objects
        """
        query = self.session.query(TradeRequest)
        
        if paper_trading is not None:
            query = query.filter(TradeRequest.paper_trading == paper_trading)
        
        return query.order_by(desc(TradeRequest.requested_at)).limit(limit).all()


class TradeExecutionRepository:
    """Repository for managing trade executions."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def record_execution(
        self,
        trade_request_id: int,
        symbol: str,
        action: str,
        quantity: int,
        execution_price: float,
        status: str,
        order_id: Optional[str] = None,
        broker_response: Optional[Dict[str, Any]] = None,
        forecast_id: Optional[str] = None,
        paper_trading: bool = False,
        error_message: Optional[str] = None
    ) -> TradeExecution:
        """
        Record a trade execution.
        
        Args:
            trade_request_id: ID of the associated TradeRequest
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares executed
            execution_price: Price at which trade was executed
            status: Execution status (Filled, PartiallyFilled, etc.)
            order_id: Broker order ID
            broker_response: Optional full broker response dict
            forecast_id: Optional forecast ID
            paper_trading: Whether this is paper trading
            error_message: Optional error message
        
        Returns:
            Created TradeExecution
        """
        execution = TradeExecution(
            trade_request_id=trade_request_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            execution_price=execution_price,
            status=status,
            order_id=order_id,
            broker_response=json.dumps(broker_response) if broker_response else None,
            forecast_id=forecast_id,
            paper_trading=paper_trading,
            error_message=error_message
        )
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution
    
    def get_by_trade_request_id(self, trade_request_id: int) -> List[TradeExecution]:
        """Get all executions for a trade request."""
        return (
            self.session.query(TradeExecution)
            .filter(TradeExecution.trade_request_id == trade_request_id)
            .order_by(desc(TradeExecution.execution_time))
            .all()
        )
    
    def list_recent(
        self,
        paper_trading: Optional[bool] = None,
        limit: int = 100
    ) -> List[TradeExecution]:
        """
        List recent trade executions.
        
        Args:
            paper_trading: Filter by paper trading (None = all)
            limit: Maximum number to return
        
        Returns:
            List of TradeExecution objects
        """
        query = self.session.query(TradeExecution)
        
        if paper_trading is not None:
            query = query.filter(TradeExecution.paper_trading == paper_trading)
        
        return query.order_by(desc(TradeExecution.execution_time)).limit(limit).all()




