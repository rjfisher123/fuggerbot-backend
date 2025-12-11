"""Interactive Brokers (IBKR) trading module for FuggerBot."""
import os
import sys
import json
import time
import random
from typing import Optional, Dict, List, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

# Lazy import for ib_insync to avoid event loop issues in Streamlit
IBKR_AVAILABLE = False
_ib_insync_imported = False

def _import_ib_insync():
    """Lazy import of ib_insync to avoid event loop issues."""
    global IBKR_AVAILABLE, _ib_insync_imported
    if _ib_insync_imported:
        return IBKR_AVAILABLE
    
    try:
        # Set up event loop if needed (for Streamlit compatibility)
        import asyncio
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except (ImportError, RuntimeError):
            # nest_asyncio not available or already applied, try to get/create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in this thread, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        
        from ib_insync import IB, Stock, MarketOrder, LimitOrder, Order, Contract
        IBKR_AVAILABLE = True
        _ib_insync_imported = True
        return True
    except ImportError:
        IBKR_AVAILABLE = False
        _ib_insync_imported = True
        return False
    except (RuntimeError, Exception) as e:
        # Handle event loop errors gracefully
        logger.warning(f"Could not import ib_insync due to event loop issue: {e}")
        IBKR_AVAILABLE = False
        _ib_insync_imported = True
        return False

from core.logger import logger
from core.sms_notifier import get_sms_notifier

# Load environment variables
load_dotenv()


class TradeConfirmation:
    """Handles trade confirmation requests via SMS."""
    
    def __init__(self, confirmation_file: Path = None):
        """
        Initialize trade confirmation system.
        
        Args:
            confirmation_file: Path to store pending confirmations (defaults to data/trade_confirmations.json)
        """
        if confirmation_file is None:
            confirmation_file = Path(__file__).parent.parent / "data" / "trade_confirmations.json"
        self.confirmation_file = confirmation_file
        self.confirmation_file.parent.mkdir(parents=True, exist_ok=True)
        self.sms_notifier = get_sms_notifier()
    
    def generate_approval_code(self) -> str:
        """Generate a 6-digit approval code."""
        return f"{random.randint(100000, 999999)}"
    
    def generate_trade_id(self) -> str:
        """Generate a unique trade ID."""
        import uuid
        return str(uuid.uuid4())[:8].upper()  # 8 character unique ID
    
    def request_confirmation(self, trade_details: Dict) -> Optional[str]:
        """
        Request trade confirmation via SMS. User replies "approve" to execute.
        
        Args:
            trade_details: Dict with keys: symbol, action, quantity, price, order_type
            
        Returns:
            Trade request ID if SMS sent successfully, None otherwise
        """
        if not self.sms_notifier.is_available():
            logger.error("SMS notifier not available - cannot request trade confirmation")
            return None
        
        # Generate a unique trade ID for this specific trade
        trade_id = self.generate_trade_id()
        
        # Format trade details message
        symbol = trade_details.get("symbol", "UNKNOWN")
        action = trade_details.get("action", "UNKNOWN").upper()
        quantity = trade_details.get("quantity", 0)
        price = trade_details.get("price", 0)
        order_type = trade_details.get("order_type", "MARKET")
        
        message = f"🚨 FUGGERBOT TRADE REQUEST\n"
        message += f"Trade ID: {trade_id}\n"
        message += f"Symbol: {symbol}\n"
        message += f"Action: {action}\n"
        message += f"Quantity: {quantity}\n"
        message += f"Order Type: {order_type}\n"
        if price > 0:
            message += f"Price: ${price:.2f}\n"
        message += f"\nReply 'APPROVE {trade_id}' to execute.\n"
        message += f"Or reply 'APPROVE' (expires in 15 min)."
        
        # Send SMS
        if self.sms_notifier.send(message):
            # Store confirmation request with unique trade ID
            confirmation = {
                "trade_id": trade_id,
                "request_id": trade_id,  # Keep for backward compatibility
                "trade_details": trade_details,
                "requested_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat(),
                "status": "pending"
            }
            
            # Save using trade_id as key
            self._save_confirmation(trade_id, confirmation)
            logger.info(f"Trade confirmation requested: {symbol} {action} {quantity} shares - Trade ID: {trade_id}")
            return trade_id
        else:
            logger.error("Failed to send trade confirmation SMS")
            return None
    
    def _save_confirmation(self, approval_code: str, confirmation: Dict):
        """Save confirmation request to file."""
        confirmations = self._load_confirmations()
        confirmations[approval_code] = confirmation
        with open(self.confirmation_file, "w") as f:
            json.dump(confirmations, f, indent=2)
    
    def _load_confirmations(self) -> Dict:
        """Load all confirmation requests."""
        if self.confirmation_file.exists():
            with open(self.confirmation_file, "r") as f:
                return json.load(f)
        return {}
    
    def verify_approval(self, approval_code: str) -> Optional[Dict]:
        """
        Verify an approval code and return trade details if valid.
        
        Args:
            approval_code: The 6-digit approval code
            
        Returns:
            Trade details dict if code is valid and not expired, None otherwise
        """
        confirmations = self._load_confirmations()
        
        if approval_code not in confirmations:
            logger.warning(f"Invalid approval code: {approval_code}")
            return None
        
        confirmation = confirmations[approval_code]
        
        # Check expiration
        expires_at = datetime.fromisoformat(confirmation["expires_at"])
        if datetime.now() > expires_at:
            logger.warning(f"Approval code expired: {approval_code}")
            # Clean up expired confirmation
            del confirmations[approval_code]
            with open(self.confirmation_file, "w") as f:
                json.dump(confirmations, f, indent=2)
            return None
        
        # Check if already used
        if confirmation.get("status") == "approved":
            logger.warning(f"Approval code already used: {approval_code}")
            return None
        
        # Mark as approved
        confirmation["status"] = "approved"
        confirmation["approved_at"] = datetime.now().isoformat()
        self._save_confirmation(approval_code, confirmation)
        
        logger.info(f"Trade approved: {approval_code}")
        return confirmation["trade_details"]
    
    def check_sms_for_approval(self) -> Optional[Dict]:
        """
        Check for "approve" replies in incoming SMS messages.
        
        Returns:
            Trade details dict if approval found, None otherwise
        """
        if not self.sms_notifier.is_available():
            logger.warning("SMS notifier not available - cannot check for approvals")
            return None
        
        # Get all pending confirmations first
        confirmations = self._load_confirmations()
        pending = [
            (code, conf) 
            for code, conf in confirmations.items() 
            if conf.get("status") == "pending"
        ]
        
        if not pending:
            logger.info("No pending trade confirmations to check")
            return None
        
        # Sort by requested_at (most recent first)
        pending.sort(
            key=lambda x: x[1].get("requested_at", ""), 
            reverse=True
        )
        
        # Get the most recent pending trade
        request_id, confirmation = pending[0]
        trade_id = confirmation.get("trade_id", request_id)  # Use trade_id if available
        
        # Check if not expired
        expires_at = datetime.fromisoformat(confirmation["expires_at"])
        if datetime.now() > expires_at:
            logger.warning(f"Most recent trade request {trade_id} has expired")
            return None
        
        # Get recent incoming messages (sent TO our Twilio number)
        logger.info(f"Checking SMS for approval reply to trade request {trade_id}...")
        logger.info(f"Trade request was sent at: {confirmation['requested_at']}")
        messages = self.sms_notifier.get_recent_messages(limit=20)
        
        if not messages:
            logger.warning("No recent SMS messages found from Twilio")
            return None
        
        logger.info(f"Found {len(messages)} recent SMS messages to check")
        
        # Check each message for approval keywords
        approval_keywords = ["approve", "yes", "execute", "confirm"]
        
        request_time = datetime.fromisoformat(confirmation["requested_at"])
        
        for msg in messages:
            body = msg.get('body', '').strip()
            body_lower = body.lower()
            from_number = msg.get('from', '')
            date_sent = msg.get('date_sent')
            
            logger.info(f"Checking SMS from {from_number} at {date_sent}: '{body[:50]}...'")
            
            # Check if message contains approval keyword
            if any(keyword in body_lower for keyword in approval_keywords):
                logger.info(f"✅ Found approval keyword in SMS: '{body[:50]}...'")
                
                # STRICT MATCHING: Check if SMS contains the trade ID
                # This ensures approvals only match the specific trade
                body_upper = body.upper()
                if trade_id.upper() in body_upper:
                    logger.info(f"✅✅ Trade ID {trade_id} found in SMS - exact match!")
                elif len(pending) == 1:
                    # Only one pending trade - allow generic APPROVE
                    logger.info(f"⚠️ Generic APPROVE detected, but only 1 pending trade - allowing (Trade ID: {trade_id})")
                else:
                    # Multiple pending trades - require trade ID
                    logger.warning(f"❌ Multiple pending trades ({len(pending)}), but SMS doesn't contain Trade ID {trade_id} - REJECTING")
                    logger.warning(f"   SMS content: '{body[:50]}...'")
                    logger.warning(f"   Expected Trade ID: {trade_id}")
                    continue  # Skip this message
                
                # CRITICAL: Check if this message was sent AFTER the trade request
                # This prevents old "APPROVE" messages from executing new trades
                if date_sent:
                    try:
                        # Parse message time (handle different formats)
                        msg_time_str = str(date_sent)
                        # Handle timezone-aware and naive datetimes
                        if 'T' in msg_time_str:
                            if msg_time_str.endswith('Z'):
                                msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00'))
                            elif '+' in msg_time_str or msg_time_str.count('-') > 2:
                                msg_time = datetime.fromisoformat(msg_time_str)
                            else:
                                # Naive datetime - assume UTC
                                msg_time = datetime.fromisoformat(msg_time_str)
                                # Make it timezone-aware (UTC)
                                from datetime import timezone
                                msg_time = msg_time.replace(tzinfo=timezone.utc)
                        else:
                            # Fallback parsing
                            msg_time = datetime.fromisoformat(msg_time_str)
                        
                        # Make request_time timezone-aware if msg_time is
                        if msg_time.tzinfo and not request_time.tzinfo:
                            from datetime import timezone
                            request_time = request_time.replace(tzinfo=timezone.utc)
                        elif not msg_time.tzinfo and request_time.tzinfo:
                            msg_time = msg_time.replace(tzinfo=request_time.tzinfo)
                        
                        # Only approve if SMS was sent AFTER the trade request
                        # Add 5 second buffer to account for clock differences and SMS delivery delays
                        time_diff = (msg_time - request_time).total_seconds()
                        
                        logger.info(f"⏰ SMS time check: message sent {time_diff:.1f}s after trade request (request: {request_time.isoformat()}, SMS: {msg_time.isoformat()})")
                        
                        if time_diff >= -5:  # Allow 5 second buffer for clock sync and delivery delays
                            # Mark as approved
                            confirmation["status"] = "approved"
                            confirmation["approved_at"] = datetime.now().isoformat()
                            confirmation["approved_via"] = "sms_reply"
                            confirmation["approval_sms_sid"] = msg.get('sid')
                            confirmation["approval_time_diff"] = time_diff
                            self._save_confirmation(trade_id, confirmation)
                            
                            logger.info(f"✅✅ Trade {trade_id} approved via SMS reply: {request_id} (SMS from {from_number}, sent {time_diff:.1f}s after request)")
                            return confirmation["trade_details"]
                        else:
                            logger.warning(f"⚠️ SMS approval found but was sent {abs(time_diff):.1f}s BEFORE trade request - ignoring (likely old message)")
                    except Exception as e:
                        logger.error(f"Error parsing SMS date: {e}", exc_info=True)
                        logger.error(f"Message date_sent: {date_sent}, type: {type(date_sent)}")
                        # Don't approve if we can't verify timing - too risky
                        logger.warning(f"⚠️ Cannot verify SMS timing - skipping approval to prevent accidental execution")
                else:
                    logger.warning(f"⚠️ SMS has no date_sent - cannot verify timing - skipping approval")
            else:
                logger.debug(f"No approval keyword found in SMS: '{body[:50]}...'")
        
        logger.warning(f"❌ No valid approval found in {len(messages)} recent SMS messages")
        return None
        
        logger.info("No approval found in recent SMS messages")
        return None


class IBKRTrader:
    """Interactive Brokers trading interface."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1, auto_connect: bool = True):
        """
        Initialize IBKR trader.
        
        Args:
            host: TWS/IB Gateway host (default: 127.0.0.1)
            port: TWS/IB Gateway port (7497 for paper, 7496 for live)
            client_id: Client ID for connection
            auto_connect: If True, automatically connect on initialization (default: True)
        """
        # Lazy import ib_insync
        if not _import_ib_insync():
            raise ImportError("ib_insync not installed. Install with: pip install ib_insync")
        
        # Now safe to import
        from ib_insync import IB
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.auto_connect = auto_connect
        self.ib = IB()
        self.connected = False
        self.confirmation = TradeConfirmation()
        
        # Determine if this is paper trading or live trading based on port
        # IBKR standard: 7497 = paper trading, 7496 = live trading
        self.is_paper_trading = (port == 7497)
        
        # Auto-connect if enabled
        if auto_connect:
            try:
                self.connect()
            except Exception as e:
                logger.warning(f"Auto-connect failed (TWS/IB Gateway may not be running): {e}")
                logger.info("You can manually connect later or ensure TWS/IB Gateway is running")
    
    def connect(self, retry: bool = True, max_retries: int = 3) -> bool:
        """
        Connect to TWS or IB Gateway.
        
        Args:
            retry: If True, retry connection on failure
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if connected successfully, False otherwise
        """
        if not _import_ib_insync():
            logger.error("ib_insync not available - cannot connect")
            return False
        
        # Ensure we have an IB instance
        if self.ib is None:
            from ib_insync import IB
            self.ib = IB()
        
        # Check if already connected
        try:
            if self.ib.isConnected():
                self.connected = True
                logger.info(f"Already connected to IBKR at {self.host}:{self.port}")
                return True
        except:
            pass
        
        # Try to connect with retries
        for attempt in range(max_retries if retry else 1):
            try:
                # Set up event loop if needed (for Streamlit compatibility)
                try:
                    import asyncio
                    import nest_asyncio
                    try:
                        nest_asyncio.apply()
                    except:
                        pass
                    # Ensure we have an event loop
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except Exception as loop_error:
                    logger.debug(f"Event loop setup note: {loop_error}")
                
                # Check if already connected
                try:
                    if self.ib.isConnected():
                        self.connected = True
                        logger.info(f"Already connected to IBKR at {self.host}:{self.port}")
                        return True
                except:
                    pass
                
                # Try to connect with timeout
                if attempt > 0:
                    wait_time = attempt * 2  # Exponential backoff: 2s, 4s, 6s
                    logger.info(f"Retry {attempt}/{max_retries-1}: Attempting to connect to IBKR at {self.host}:{self.port}...")
                    time.sleep(wait_time)
                else:
                    logger.info(f"Attempting to connect to IBKR at {self.host}:{self.port}...")
                
                self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=10)
                self.connected = True
                logger.info(f"✅ Successfully connected to IBKR at {self.host}:{self.port}")
                return True
            except Exception as e:
                error_msg = str(e) if str(e) else repr(e)
                error_type = type(e).__name__
                
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"Connection attempt {attempt + 1} failed: {error_msg}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    logger.error(f"Failed to connect to IBKR after {max_retries} attempts ({error_type}): {error_msg}")
                    
                    # Provide helpful error messages
                    if not error_msg or error_msg == "None":
                        logger.error(f"  → Empty error - check IB Gateway is running and API is enabled")
                        logger.error(f"  → Port {self.port} should be listening (check with: lsof -i :{self.port})")
                    elif "Connect call failed" in error_msg or "Connection refused" in error_msg or "ConnectionRefusedError" in error_type:
                        logger.error(f"  → Make sure IB Gateway is running on port {self.port}")
                        logger.error(f"  → Check API is enabled in IB Gateway: File > Global Configuration > API > Settings")
                        logger.error(f"  → Verify 'Enable ActiveX and Socket Clients' is checked")
                    elif "timeout" in error_msg.lower():
                        logger.error(f"  → Connection timeout - IB Gateway may be slow to respond")
                    
                    self.connected = False
                    return False
        
        return False
    
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.connected:
            try:
                self.ib.disconnect()
                self.connected = False
                logger.info("Disconnected from IBKR")
            except Exception as e:
                logger.error(f"Error disconnecting from IBKR: {e}")
    
    def get_contract(self, symbol: str, exchange: str = "SMART", currency: str = "USD") -> Optional['Contract']:
        """
        Get IBKR contract for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL", "INTC")
            exchange: Exchange (default: "SMART")
            currency: Currency (default: "USD")
            
        Returns:
            Contract object if found, None otherwise
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return None
        
        if not _import_ib_insync():
            logger.error("ib_insync not available - cannot get contract")
            return None
        
        from ib_insync import Stock
        
        try:
            contract = Stock(symbol, exchange, currency)
            logger.info(f"Creating contract object for {symbol} (exchange {exchange})")
            return contract
        except Exception as e:
            logger.error(f"Error creating contract for {symbol}: {e}", exc_info=True)
            return None
    
    def get_market_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price if available, None otherwise
        """
        contract = self.get_contract(symbol)
        if not contract:
            return None
        
        try:
            ticker = self.ib.reqMktData(contract, '', False, False)
            # Wait for market data with timeout
            self.ib.sleep(3)  # Wait up to 3 seconds for market data
            
            if ticker.marketPrice():
                return ticker.marketPrice()
            elif ticker.last:
                return ticker.last
            else:
                logger.warning(f"No market price available for {symbol} - may be delayed data")
                # Return None but don't fail - we can proceed without price
                return None
        except Exception as e:
            logger.error(f"Error getting market price for {symbol}: {e}")
            return None
    
    def get_account_summary(self) -> Optional[Dict]:
        """
        Get account summary information.
        
        Returns:
            Dict with account information, None if error
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return None
        
        if not IBKR_AVAILABLE:
            return None
        
        try:
            account_values = self.ib.accountValues()
            summary = {}
            for av in account_values:
                if av.tag in ['NetLiquidation', 'TotalCashValue', 'BuyingPower', 'GrossPositionValue']:
                    summary[av.tag] = {
                        'value': av.value,
                        'currency': av.currency
                    }
            return summary if summary else None
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return None
    
    def execute_trade(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        require_confirmation: bool = True,
        timeout: int = 30,
        poll_for_approval: bool = False,
        poll_timeout: int = 300  # 5 minutes default
    ) -> Dict:
        """
        Execute a trade with optional confirmation.
        
        Args:
            symbol: Stock symbol
            action: "BUY" or "SELL"
            quantity: Number of shares
            order_type: "MARKET" or "LIMIT"
            limit_price: Limit price (required if order_type is "LIMIT")
            require_confirmation: If True, request SMS confirmation before executing
            
        Returns:
            Dict with trade result: {"success": bool, "order_id": str, "message": str}
        """
        logger.info(f"execute_trade called: {symbol} {action} {quantity} {order_type} limit={limit_price}")
        
        if not self.connected:
            logger.error("Not connected to IBKR")
            return {"success": False, "message": "Not connected to IBKR"}
        
        if action.upper() not in ["BUY", "SELL"]:
            return {"success": False, "message": f"Invalid action: {action}. Must be BUY or SELL"}
        
        if order_type == "LIMIT" and limit_price is None:
            return {"success": False, "message": "limit_price required for LIMIT orders"}
        
        # For LIMIT orders, use the provided price immediately (skip market lookup)
        # For MARKET orders, we'll use 0 as placeholder since we're requesting confirmation
        price = limit_price if (limit_price or order_type == "LIMIT") else 0
        
        logger.info(f"Using price: {price} for {symbol} ({order_type} order)")
        
        trade_details = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "order_type": order_type,
            "price": price or 0
        }
        
        # Request confirmation if required
        if require_confirmation:
            logger.info(f"Requesting trade confirmation for {symbol} {action} {quantity}...")
            try:
                # Request confirmation (SMS should be fast, but log timing)
                import time
                start_time = time.time()
                approval_code = self.confirmation.request_confirmation(trade_details)
                elapsed = time.time() - start_time
                logger.info(f"Confirmation request took {elapsed:.2f} seconds")
                
                if not approval_code:
                    logger.error("Failed to get approval code from confirmation system")
                    return {
                        "success": False,
                        "message": "Failed to send confirmation request - check SMS configuration",
                        "approval_code": None
                    }
                
                logger.info(f"Trade confirmation requested successfully - Request ID: {approval_code}")
                
                # If polling is enabled, wait for approval
                if poll_for_approval:
                    logger.info(f"Polling for SMS approval (timeout: {poll_timeout}s)...")
                    result = self._poll_for_approval_and_execute(poll_timeout, trade_details)
                    return result
                
                return {
                    "success": True,  # Request successful, waiting for approval
                    "pending_approval": True,
                    "message": "Trade request sent via SMS. Reply 'APPROVE' to execute.",
                    "request_id": approval_code,
                    "trade_details": trade_details
                }
            except Exception as e:
                logger.error(f"Error requesting confirmation: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"Error requesting confirmation: {str(e)}",
                    "approval_code": None
                }
        
        # Execute trade directly (no confirmation)
        return self._execute_order(symbol, action, quantity, order_type, limit_price)
    
    def approve_and_execute(self, approval_code: Optional[str] = None) -> Dict:
        """
        Approve a pending trade and execute it.
        Can be called with an approval code (legacy) or check SMS for approval.
        
        Args:
            approval_code: Optional approval code (for backward compatibility). 
                          If None, checks SMS for "APPROVE" reply.
            
        Returns:
            Dict with trade result
        """
        trade_details = None
        
        # If approval code provided, use legacy method
        if approval_code:
            trade_details = self.confirmation.verify_approval(approval_code)
        else:
            # Check SMS for approval reply
            trade_details = self.confirmation.check_sms_for_approval()
        
        if not trade_details:
            if approval_code:
                return {"success": False, "message": "Invalid or expired approval code"}
            else:
                return {"success": False, "message": "No pending trade approval found in SMS. Make sure you replied 'APPROVE' to the trade request SMS."}
        
        symbol = trade_details["symbol"]
        action = trade_details["action"]
        quantity = trade_details["quantity"]
        order_type = trade_details["order_type"]
        limit_price = trade_details.get("price") if order_type == "LIMIT" else None
        
        # Check connection status
        if not self.connected:
            logger.warning("Not connected when approving trade")
            # Try to connect, but if it fails due to client ID conflict, that's OK if we're already connected elsewhere
            try:
                if not self.connect():
                    # If connection fails, check if we're actually connected via another instance
                    # This can happen if Streamlit has the connection
                    logger.warning("Connection attempt failed - may already be connected via another instance")
            except Exception as e:
                logger.warning(f"Connection error (may be OK if already connected): {e}")
        
        # Final check - if still not connected, we can't proceed
        if not self.connected:
            return {
                "success": False,
                "message": "Not connected to IBKR. Please ensure IB Gateway is running and connected in the dashboard."
            }
        
        logger.info(f"Executing approved trade: {symbol} {action} {quantity} shares")
        result = self._execute_order(symbol, action, quantity, order_type, limit_price)
        
        # Send confirmation SMS
        self._send_trade_confirmation_sms(result, symbol, action, quantity, order_type, limit_price)
        
        return result
    
    def _send_trade_confirmation_sms(self, result: Dict, symbol: str, action: str, quantity: int, order_type: str, limit_price: Optional[float]):
        """Send confirmation SMS after trade execution."""
        if not self.confirmation.sms_notifier.is_available():
            return
        
        if result.get("success"):
            # Success message
            message = f"✅ TRADE EXECUTED\n"
            message += f"Symbol: {symbol}\n"
            message += f"Action: {action}\n"
            message += f"Quantity: {quantity}\n"
            message += f"Order Type: {order_type}\n"
            if limit_price:
                message += f"Limit Price: ${limit_price:.2f}\n"
            message += f"Status: {result.get('status', 'N/A')}\n"
            message += f"Order ID: {result.get('order_id', 'N/A')}\n"
            if result.get('note'):
                message += f"\nNote: {result.get('note')}"
        else:
            # Error message
            message = f"❌ TRADE FAILED\n"
            message += f"Symbol: {symbol}\n"
            message += f"Action: {action}\n"
            message += f"Quantity: {quantity}\n"
            message += f"Error: {result.get('message', 'Unknown error')}\n"
            if result.get('error'):
                message += f"Details: {result.get('error')}"
        
        self.confirmation.sms_notifier.send(message)
    
    def _send_trade_confirmation_sms(self, result: Dict, symbol: str, action: str, quantity: int, order_type: str, limit_price: Optional[float]):
        """Send confirmation SMS after trade execution."""
        if not self.confirmation.sms_notifier.is_available():
            return
        
        if result.get("success"):
            # Success message
            message = f"✅ TRADE EXECUTED\n"
            message += f"Symbol: {symbol}\n"
            message += f"Action: {action}\n"
            message += f"Quantity: {quantity}\n"
            message += f"Order Type: {order_type}\n"
            if limit_price:
                message += f"Limit Price: ${limit_price:.2f}\n"
            message += f"Status: {result.get('status', 'N/A')}\n"
            message += f"Order ID: {result.get('order_id', 'N/A')}\n"
            if result.get('note'):
                message += f"\nNote: {result.get('note')}"
        else:
            # Error message
            message = f"❌ TRADE FAILED\n"
            message += f"Symbol: {symbol}\n"
            message += f"Action: {action}\n"
            message += f"Quantity: {quantity}\n"
            message += f"Error: {result.get('message', 'Unknown error')}\n"
            if result.get('error'):
                message += f"Details: {result.get('error')}"
        
        self.confirmation.sms_notifier.send(message)
    
    def _poll_for_approval_and_execute(self, timeout: int, trade_details: Dict) -> Dict:
        """
        Poll Twilio API for SMS approval and execute trade when approved.
        
        Args:
            timeout: Maximum time to wait in seconds
            trade_details: Trade details to execute
            
        Returns:
            Dict with trade result
        """
        import time
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        # Get the request time to ensure we only accept approvals sent AFTER this request
        request_time = datetime.fromisoformat(trade_details.get("requested_at", datetime.now().isoformat()))
        logger.info(f"Starting SMS approval polling (will check every {check_interval}s for up to {timeout}s)")
        logger.info(f"Trade request time: {request_time.isoformat()} - only accepting SMS approvals sent AFTER this time")
        
        check_count = 0
        while (time.time() - start_time) < timeout:
            check_count += 1
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            
            # Only log every 5th check to avoid spam, or if it's the first few checks
            if check_count <= 3 or check_count % 5 == 0:
                logger.info(f"Polling check #{check_count} (elapsed: {int(elapsed)}s, remaining: {int(remaining)}s)")
            
            # Check for approval
            trade_details_found = self.confirmation.check_sms_for_approval()
            
            if trade_details_found:
                # Approval found, execute trade
                symbol = trade_details_found["symbol"]
                action = trade_details_found["action"]
                quantity = trade_details_found["quantity"]
                order_type = trade_details_found["order_type"]
                limit_price = trade_details_found.get("price") if order_type == "LIMIT" else None
                
                logger.info(f"✅ Approval received via SMS! Executing trade: {symbol} {action} {quantity}")
                
                # Ensure connected
                if not self.connected:
                    if not self.connect():
                        return {
                            "success": False,
                            "message": "Not connected to IBKR. Please connect first."
                        }
                
                # Execute trade
                result = self._execute_order(symbol, action, quantity, order_type, limit_price)
                
                # Send confirmation SMS
                self._send_trade_confirmation_sms(result, symbol, action, quantity, order_type, limit_price)
                
                return result
            
            # Wait before next check
            if remaining > check_interval:
                logger.info(f"No approval yet, waiting {check_interval}s before next check...")
                time.sleep(check_interval)
            else:
                break
        
        # Timeout - no approval received
        logger.warning(f"SMS approval polling timed out after {timeout}s")
        return {
            "success": False,
            "pending_approval": True,
            "message": f"Trade request sent via SMS, but no approval received within {timeout}s. Reply 'APPROVE' to the SMS to execute.",
            "timeout": True
        }
    
    def _execute_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: str,
        limit_price: Optional[float]
    ) -> Dict:
        """Internal method to execute an order."""
        # Ensure connected
        if not self.connected:
            logger.warning("Not connected when trying to execute order, attempting to connect...")
            if not self.connect():
                return {"success": False, "message": "Not connected to IBKR and connection failed"}
        
        logger.info(f"Getting contract for {symbol}...")
        try:
            contract = self.get_contract(symbol)
            if not contract:
                logger.error(f"Could not get contract for {symbol}")
                return {"success": False, "message": f"Could not get contract for {symbol}. Check symbol is valid and IBKR is connected."}
            logger.info(f"Contract obtained: {contract.symbol} on {contract.exchange}")
        except Exception as e:
            logger.error(f"Error getting contract: {e}", exc_info=True)
            return {"success": False, "message": f"Error getting contract: {str(e)}"}
        
        if not _import_ib_insync():
            return {"success": False, "message": "ib_insync not available - cannot execute order"}
        
        from ib_insync import MarketOrder, LimitOrder
        
        try:
            # Create order
            logger.info(f"Creating {order_type} order: {action} {quantity} shares of {symbol}")
            if order_type == "MARKET":
                order = MarketOrder(action.upper(), quantity)
            elif order_type == "LIMIT":
                order = LimitOrder(action.upper(), quantity, limit_price)
                logger.info(f"Limit order price: ${limit_price:.2f}")
            else:
                return {"success": False, "message": f"Unsupported order type: {order_type}"}
            
            # Place order
            logger.info(f"Placing order with IBKR...")
            trade = self.ib.placeOrder(contract, order)
            logger.info(f"Order placed, waiting for confirmation...")
            self.ib.sleep(3)  # Wait for order submission and status update
            
            # Check order status
            order_status = trade.orderStatus.status
            order_id = trade.order.orderId if trade.order else None
            
            logger.info(f"Order status: {order_status}, Order ID: {order_id}")
            
            # PendingSubmit is a valid intermediate state - order is being processed
            if order_status in ["Submitted", "PreSubmitted", "Filled", "PartiallyFilled", "PendingSubmit"]:
                # Save to trade history
                self._save_trade_history({
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "order_type": order_type,
                    "limit_price": limit_price,
                    "status": order_status,
                    "executed_at": datetime.now().isoformat(),
                    "success": True
                })
                
                if order_status == "PendingSubmit":
                    logger.info(f"✅ Order submitted (pending): {symbol} {action} {quantity} - Status: {order_status}, Order ID: {order_id}")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "status": order_status,
                        "message": f"Order submitted successfully (pending confirmation): {symbol} {action} {quantity} shares. Order ID: {order_id}",
                        "symbol": symbol,
                        "action": action,
                        "quantity": quantity,
                        "note": "Order is pending submission to exchange. Check TWS/IB Gateway for final status."
                    }
                else:
                    logger.info(f"✅ Order placed successfully: {symbol} {action} {quantity} - Status: {order_status}")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "status": order_status,
                        "message": f"Order {order_status}: {symbol} {action} {quantity} shares",
                        "symbol": symbol,
                        "action": action,
                        "quantity": quantity
                    }
            else:
                error_msg = trade.orderStatus.why if hasattr(trade.orderStatus, 'why') and trade.orderStatus.why else "Unknown error"
                logger.error(f"❌ Order failed: {symbol} {action} {quantity} - Status: {order_status}, Error: {error_msg}")
                return {
                    "success": False,
                    "order_id": order_id,
                    "status": order_status,
                    "message": f"Order {order_status}: {symbol} {action} {quantity} shares. {error_msg}",
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Error executing order: {e}", exc_info=True)
            return {"success": False, "message": f"Error executing order: {str(e)}"}
    
    def _save_trade_history(self, trade_data: Dict):
        """Save executed trade to history file."""
        try:
            history_file = Path(__file__).parents[1] / "data" / "trade_history.json"
            history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing history
            if history_file.exists():
                with open(history_file, "r") as f:
                    history = json.load(f)
            else:
                history = []
            
            # Add new trade (most recent first)
            history.insert(0, trade_data)
            
            # Keep only last 1000 trades
            history = history[:1000]
            
            # Save
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get recent trade history."""
        try:
            history_file = Path(__file__).parents[1] / "data" / "trade_history.json"
            if not history_file.exists():
                return []
            
            with open(history_file, "r") as f:
                history = json.load(f)
            
            return history[:limit]
        except Exception as e:
            logger.error(f"Error loading trade history: {e}")
            return []


# Global instance
_ibkr_trader: Optional[IBKRTrader] = None


def get_ibkr_trader(host: str = None, port: int = None, client_id: int = None, force_new: bool = False, auto_connect: bool = True, paper_trading: bool = None) -> IBKRTrader:
    """
    Get or create global IBKR trader instance.
    
    Args:
        host: TWS/IB Gateway host (defaults to env var or 127.0.0.1)
        port: TWS/IB Gateway port (defaults to env var or 7497 for paper, 7496 for live)
        client_id: Client ID (defaults to env var or 1)
        force_new: If True, create a new instance even if one exists (useful for Streamlit)
        auto_connect: If True, automatically connect on initialization (default: True)
        paper_trading: If True, use paper trading port (7497), if False use live (7496). 
                      If None, uses IBKR_PORT env var or defaults to paper (7497)
        
    Returns:
        IBKRTrader instance
    """
    global _ibkr_trader
    
    # Check if we should auto-connect from environment variable
    auto_connect_env = os.getenv("IBKR_AUTO_CONNECT", "true").lower() == "true"
    auto_connect = auto_connect and auto_connect_env
    
    # Determine port based on paper_trading flag
    if port is None:
        # First check for specific port, then fall back to IBKR_PORT, then defaults
        if paper_trading is True:
            port = int(os.getenv("IBKR_PAPER_PORT") or os.getenv("IBKR_PORT", "7497"))
        elif paper_trading is False:
            port = int(os.getenv("IBKR_LIVE_PORT") or os.getenv("IBKR_PORT", "7496"))
        else:
            # Default to paper trading if not specified
            port = int(os.getenv("IBKR_PORT", "7497"))
    
    if _ibkr_trader is None or force_new:
        if host is None:
            host = os.getenv("IBKR_HOST", "127.0.0.1")
        if client_id is None:
            client_id = int(os.getenv("IBKR_CLIENT_ID", "1"))
        
        if force_new and _ibkr_trader is not None:
            # Disconnect old instance
            try:
                _ibkr_trader.disconnect()
            except:
                pass
        
        _ibkr_trader = IBKRTrader(host, port, client_id, auto_connect=auto_connect)
    elif auto_connect and not _ibkr_trader.connected:
        # If instance exists but not connected, try to connect
        try:
            _ibkr_trader.connect()
        except Exception as e:
            logger.warning(f"Auto-connect failed: {e}")
    
    return _ibkr_trader


def get_paper_trading_trader() -> IBKRTrader:
    """
    Get IBKR trader instance configured for paper trading.
    
    Returns:
        IBKRTrader instance connected to paper trading account (port 7497)
    """
    # Use different client ID for paper trading to avoid conflicts
    paper_client_id = int(os.getenv("IBKR_PAPER_CLIENT_ID") or os.getenv("IBKR_CLIENT_ID", "1"))
    return get_ibkr_trader(paper_trading=True, force_new=True, client_id=paper_client_id)


def get_live_trading_trader() -> IBKRTrader:
    """
    Get IBKR trader instance configured for live trading.
    
    Returns:
        IBKRTrader instance connected to live trading account (port 7496)
    """
    # Use different client ID for live trading to avoid conflicts
    live_client_id = int(os.getenv("IBKR_LIVE_CLIENT_ID") or os.getenv("IBKR_CLIENT_ID", "2"))
    return get_ibkr_trader(paper_trading=False, force_new=True, client_id=live_client_id)

