"""
Trade service for managing trade approvals and execution.

This service handles trade confirmation, approval, rejection, and history.
It coordinates between IBKR client and trade confirmation system.
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime

from core.ibkr_trader import TradeConfirmation, get_live_trading_trader, get_paper_trading_trader
from services.ibkr_client import get_ibkr_client
from persistence.db import SessionLocal
from persistence.repositories_trades import TradeRequestRepository, TradeExecutionRepository
from persistence.models_trades import TradeRequest
from core.logger import logger
from core.logging import log_trade_event


class TradeService:
    """Service for managing trades and approvals."""
    
    def __init__(self, paper_trading: bool = False):
        """
        Initialize trade service.
        
        Args:
            paper_trading: If True, use paper trading account, else live trading
        """
        self.paper_trading = paper_trading
        self.confirmation = TradeConfirmation()
        self.ibkr_client = get_ibkr_client(paper_trading=paper_trading)
        logger.info(f"TradeService initialized (paper_trading={paper_trading})")
    
    def get_connection_status(self) -> Dict:
        """
        Get IBKR connection status.
        
        Returns:
            Dict with connection status
        """
        return self.ibkr_client.get_connection_status()
    
    def connect(self) -> bool:
        """
        Connect to IBKR.
        
        Returns:
            True if connected successfully, False otherwise
        """
        return self.ibkr_client.connect()
    
    def list_pending_trades(self) -> List[Dict]:
        """
        List all pending trade approvals.
        
        Returns:
            List of dicts with pending trade information
        """
        try:
            confirmations = self.confirmation._load_confirmations()
            
            # Filter pending confirmations
            pending = []
            for code, conf in confirmations.items():
                if conf.get("status") == "pending":
                    trade_details = conf.get("trade_details", {})
                    requested_at = conf.get("requested_at", "")
                    expires_at = conf.get("expires_at", "")
                    
                    # Check expiration
                    try:
                        exp_time = datetime.fromisoformat(expires_at)
                        if datetime.now() > exp_time:
                            continue  # Skip expired
                    except Exception:
                        pass  # Include if we can't parse date
                    
                    pending.append({
                        "trade_id": conf.get("trade_id", code),
                        "approval_code": code,
                        "symbol": trade_details.get("symbol", "UNKNOWN"),
                        "action": trade_details.get("action", "UNKNOWN"),
                        "quantity": trade_details.get("quantity", 0),
                        "order_type": trade_details.get("order_type", "MARKET"),
                        "price": trade_details.get("price", 0),
                        "requested_at": requested_at,
                        "expires_at": expires_at,
                        "trade_details": trade_details
                    })
            
            return pending
        except Exception as e:
            logger.error(f"Error listing pending trades: {e}", exc_info=True)
            return []
    
    def approve_trade(self, trade_id: str, approval_code: Optional[str] = None) -> Dict:
        """
        Approve a pending trade and execute it.
        
        Args:
            trade_id: Trade ID to approve (can be approval_code for legacy)
            approval_code: Optional approval code (for backward compatibility)
        
        Returns:
            Dict with trade execution result
        """
        try:
            # Get the appropriate trader instance
            if self.paper_trading:
                trader = get_paper_trading_trader()
            else:
                trader = get_live_trading_trader()
            
            # Ensure connected
            if not trader.connected:
                if not self.connect():
                    return {
                        "success": False,
                        "message": "Not connected to IBKR. Please connect first."
                    }
            
            # Use approval_code if provided, otherwise use trade_id
            code_to_use = approval_code or trade_id
            
            # Check SMS for approval (if no code provided) or verify code
            if not code_to_use:
                # Check SMS for approval
                result = trader.approve_and_execute()
            else:
                # Use approval code
                result = trader.approve_and_execute(code_to_use)
            
            return result
        except Exception as e:
            logger.error(f"Error approving trade {trade_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error approving trade: {str(e)}"
            }
    
    def reject_trade(self, trade_id: str) -> Dict:
        """
        Reject a pending trade (mark as rejected, don't execute).
        
        Args:
            trade_id: Trade ID to reject
        
        Returns:
            Dict with rejection result
        """
        try:
            confirmations = self.confirmation._load_confirmations()
            
            # Find the trade by trade_id or approval_code
            found = False
            for code, conf in confirmations.items():
                if conf.get("trade_id") == trade_id or code == trade_id:
                    if conf.get("status") == "pending":
                        conf["status"] = "rejected"
                        conf["rejected_at"] = datetime.now().isoformat()
                        self.confirmation._save_confirmation(code, conf)
                        found = True
                        trade_details = conf.get("trade_details", {})
                        log_trade_event(
                            event_type="rejected",
                            symbol=trade_details.get("symbol", "UNKNOWN"),
                            action=trade_details.get("action", "UNKNOWN"),
                            quantity=trade_details.get("quantity", 0),
                            price=trade_details.get("price"),
                            trade_id=trade_id,
                            status="rejected"
                        )
                        logger.info(f"Trade {trade_id} rejected")
                        break
            
            if not found:
                return {
                    "success": False,
                    "message": f"Trade {trade_id} not found or already processed"
                }
            
            return {
                "success": True,
                "message": f"Trade {trade_id} rejected successfully"
            }
        except Exception as e:
            logger.error(f"Error rejecting trade {trade_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error rejecting trade: {str(e)}"
            }
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """
        Get recent trade history.
        
        Args:
            limit: Maximum number of trades to return
        
        Returns:
            List of trade history dicts
        """
        try:
            if self.paper_trading:
                trader = get_paper_trading_trader()
            else:
                trader = get_live_trading_trader()
            
            return trader.get_trade_history(limit=limit)
        except Exception as e:
            logger.error(f"Error getting trade history: {e}", exc_info=True)
            return []
    
    def get_account_summary(self) -> Optional[Dict]:
        """
        Get account summary information.
        
        Returns:
            Dict with account information, None if error
        """
        return self.ibkr_client.get_account_summary()
    
    def submit_order(self, trade_request: TradeRequest) -> Dict:
        """
        Submit a trade request to IBKR and update database.
        
        Args:
            trade_request: TradeRequest model from database
        
        Returns:
            Dict with order result: {
                "success": bool,
                "order_id": Optional[str],
                "status": str,
                "message": str,
                "execution_id": Optional[int]
            }
        """
        try:
            # Validate trade request status
            if trade_request.status != "pending" and trade_request.status != "approved":
                return {
                    "success": False,
                    "message": f"Cannot submit trade with status: {trade_request.status}. Must be 'pending' or 'approved'."
                }
            
            # Place order via IBKR client
            logger.info(f"Submitting order for trade request {trade_request.trade_id}: {trade_request.symbol} {trade_request.action} {trade_request.quantity}")
            
            log_trade_event(
                event_type="submitted",
                symbol=trade_request.symbol,
                action=trade_request.action,
                quantity=trade_request.quantity,
                price=trade_request.price,
                trade_id=trade_request.trade_id,
                status="submitted",
                order_type=trade_request.order_type,
                paper_trading=trade_request.paper_trading
            )
            
            order_result = self.ibkr_client.place_order(
                symbol=trade_request.symbol,
                action=trade_request.action,
                quantity=trade_request.quantity,
                order_type=trade_request.order_type,
                limit_price=trade_request.price
            )
            
            # Update database
            with SessionLocal() as session:
                request_repo = TradeRequestRepository(session)
                exec_repo = TradeExecutionRepository(session)
                
                # Record execution (success or failure)
                execution_id = None
                if order_result.get("success"):
                    # Order was successfully placed - update status to "submitted"
                    updated_request = request_repo.update_request_status(
                        trade_request.trade_id,
                        "submitted"
                    )
                    
                    if not updated_request:
                        logger.warning(f"Could not update trade request {trade_request.trade_id} status")
                    order_id = order_result.get("order_id")
                    status = order_result.get("status", "Submitted")
                    
                    # Get execution price if available
                    execution_price = trade_request.price if trade_request.price else 0.0
                    if "execution_price" in order_result:
                        execution_price = order_result["execution_price"]
                    
                    # Create execution record
                    execution = exec_repo.record_execution(
                        trade_request_id=trade_request.id,
                        symbol=trade_request.symbol,
                        action=trade_request.action,
                        quantity=trade_request.quantity,
                        execution_price=execution_price,
                        status=status,
                        order_id=str(order_id) if order_id else None,
                        broker_response=order_result,
                        forecast_id=trade_request.forecast_id,
                        paper_trading=trade_request.paper_trading,
                        error_message=None if order_result.get("success") else order_result.get("message")
                    )
                    execution_id = execution.id
                    logger.info(f"Trade execution recorded: execution_id={execution_id}, order_id={order_id}")
                    
                    log_trade_event(
                        event_type="executed",
                        symbol=trade_request.symbol,
                        action=trade_request.action,
                        quantity=trade_request.quantity,
                        price=execution_price,
                        trade_id=trade_request.trade_id,
                        status=status,
                        order_id=str(order_id) if order_id else None,
                        execution_id=execution_id,
                        paper_trading=trade_request.paper_trading
                    )
                else:
                    # Order failed - record execution with error but keep status as pending
                    error_msg = order_result.get("message", "Unknown error")
                    execution = exec_repo.record_execution(
                        trade_request_id=trade_request.id,
                        symbol=trade_request.symbol,
                        action=trade_request.action,
                        quantity=trade_request.quantity,
                        execution_price=0.0,
                        status="Rejected",
                        order_id=None,
                        broker_response=order_result,
                        forecast_id=trade_request.forecast_id,
                        paper_trading=trade_request.paper_trading,
                        error_message=error_msg
                    )
                    execution_id = execution.id
                    logger.warning(f"Order submission failed, execution recorded with error: {error_msg}")
                    # Status remains "pending" - can retry later
            
            # Return result with execution_id
            result = {
                **order_result,
                "execution_id": execution_id
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error submitting order for trade request {trade_request.trade_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error submitting order: {str(e)}",
                "execution_id": None
            }


# Global service instances
_live_trade_service: Optional[TradeService] = None
_paper_trade_service: Optional[TradeService] = None


def get_trade_service(paper_trading: bool = False) -> TradeService:
    """
    Get or create trade service instance.
    
    Args:
        paper_trading: If True, return paper trading service, else live trading
    
    Returns:
        TradeService instance
    """
    global _live_trade_service, _paper_trade_service
    
    if paper_trading:
        if _paper_trade_service is None:
            _paper_trade_service = TradeService(paper_trading=True)
        return _paper_trade_service
    else:
        if _live_trade_service is None:
            _live_trade_service = TradeService(paper_trading=False)
        return _live_trade_service

