"""Streamlit component for approving pending trades."""
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from services.trade_service import get_trade_service
from core.logger import logger


def render_trade_approval():
    """Render the trade approval panel."""
    st.subheader("💰 Trade Approval")
    st.info("💡 **Live Trading**: This panel is for approving and executing **real trades** through IBKR's **live trading API** (port 7496). For paper trading, use the **📊 Paper Trading** tab which connects to IBKR's paper trading API (port 7497).")
    
    try:
        # Get trade service (live trading)
        trade_service = get_trade_service(paper_trading=False)
        
        # Get pending trades
        pending_trades = trade_service.list_pending_trades()
        
        if not pending_trades:
            st.info("✅ No pending trade approvals")
        else:
            st.warning(f"⚠️ {len(pending_trades)} pending trade approval(s)")
            
            for trade in pending_trades:
                approval_code = trade.get("approval_code", "")
                trade_id = trade.get("trade_id", approval_code)
                symbol = trade.get("symbol", "UNKNOWN")
                requested_at = trade.get("requested_at", "")
                expires_at = trade.get("expires_at", "")
                
                # Parse timestamps
                try:
                    req_time = datetime.fromisoformat(requested_at)
                    exp_time = datetime.fromisoformat(expires_at)
                    time_remaining = exp_time - datetime.now()
                    
                    if time_remaining.total_seconds() <= 0:
                        st.error(f"❌ Trade {trade_id} has EXPIRED")
                        continue
                except Exception as time_parse_error:
                    logger.warning(f"Could not parse timestamp for trade {trade_id}: {time_parse_error}")
                    time_remaining = None
                
                # Display trade details
                with st.expander(f"Trade Request: {symbol} - ID: {trade_id}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Symbol:** {symbol}")
                        st.write(f"**Action:** {trade.get('action', 'N/A')}")
                        st.write(f"**Quantity:** {trade.get('quantity', 0)}")
                    
                    with col2:
                        st.write(f"**Order Type:** {trade.get('order_type', 'N/A')}")
                        if trade.get('price'):
                            st.write(f"**Price:** ${trade.get('price', 0):.2f}")
                        if time_remaining:
                            st.write(f"**Time Remaining:** {int(time_remaining.total_seconds() / 60)} minutes")
                    
                    st.write(f"**Requested:** {requested_at}")
                    st.write(f"**Expires:** {expires_at}")
                    
                    # Action buttons
                    col_approve, col_reject = st.columns(2)
                    with col_approve:
                        if st.button(f"✅ Approve {trade_id}", key=f"approve_{trade_id}"):
                            with st.spinner("Approving and executing trade..."):
                                result = trade_service.approve_trade(trade_id, approval_code)
                                if result.get("success"):
                                    st.success("✅ Trade executed successfully!")
                                    st.json(result)
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                                    st.json(result)
                    with col_reject:
                        if st.button(f"❌ Reject {trade_id}", key=f"reject_{trade_id}"):
                            result = trade_service.reject_trade(trade_id)
                            if result.get("success"):
                                st.success(f"✅ Trade {trade_id} rejected")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to reject: {result.get('message', 'Unknown error')}")
        
        st.markdown("---")
        st.subheader("Manual Trade Approval")
        
        st.info("💡 **Automatic Approval:** When you request a trade, the system automatically polls for your 'APPROVE' SMS reply. Use this section only if you need to manually check for approvals.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📱 Check SMS & Execute", type="secondary"):
                try:
                    # Ensure connected
                    if not trade_service.connect():
                        st.error("❌ Failed to connect to IBKR. Make sure TWS/IB Gateway is running.")
                        st.info("💡 If you see 'client id already in use', the connection is active - try refreshing the page.")
                        st.stop()
                    
                    # Check SMS for approval and execute
                    with st.spinner("Checking SMS for approval and executing trade (this may take 10-15 seconds)..."):
                        import time
                        start_time = time.time()
                        result = trade_service.approve_trade(None)  # None = check SMS
                        elapsed = time.time() - start_time
                        logger.info(f"Trade execution took {elapsed:.2f} seconds")
                    
                    if result.get("success"):
                        st.success(f"✅ Trade executed successfully!")
                        st.json(result)
                        st.balloons()
                        st.info("📱 Check your phone for confirmation SMS with trade details.")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {result.get('message', 'Unknown error')}")
                        if "No pending trade" in result.get('message', ''):
                            st.info("💡 Make sure you replied 'APPROVE' to the SMS trade request.")
                        st.json(result)
                        # Show more details if available
                        if "order_id" in result:
                            st.info(f"Order ID: {result.get('order_id')}")
                        if "status" in result:
                            st.info(f"Status: {result.get('status')}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    logger.error(f"Trade approval error: {e}", exc_info=True)
        
        with col2:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        # Legacy approval code entry (for backward compatibility)
        with st.expander("🔧 Legacy: Manual Approval Code Entry"):
            st.info("💡 This is for backward compatibility. The new workflow uses SMS replies.")
            approval_code_input = st.text_input(
                "Enter Approval Code (legacy)",
                placeholder="123456",
                max_chars=6,
                key="legacy_code"
            )
            
            if st.button("✅ Approve with Code (Legacy)", key="legacy_approve"):
                if not approval_code_input or len(approval_code_input) != 6:
                    st.error("Please enter a valid 6-digit approval code")
                else:
                    try:
                        if not trade_service.connect():
                            st.error("❌ Failed to connect to IBKR.")
                            st.stop()
                        
                        with st.spinner("Executing trade..."):
                            result = trade_service.approve_trade(approval_code_input, approval_code_input)
                        
                        if result.get("success"):
                            st.success(f"✅ Trade executed successfully!")
                            st.json(result)
                            st.rerun()
                        else:
                            st.error(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        st.markdown("---")
        st.subheader("📜 Trade History")
        
        try:
            history = trade_service.get_trade_history(limit=20)
            
            if history:
                st.info(f"Showing {len(history)} most recent executed trades")
                
                for trade in history:
                    with st.expander(f"{trade.get('symbol', 'N/A')} {trade.get('action', 'N/A')} {trade.get('quantity', 0)} - {trade.get('status', 'N/A')} (Order ID: {trade.get('order_id', 'N/A')})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Symbol:** {trade.get('symbol', 'N/A')}")
                            st.write(f"**Action:** {trade.get('action', 'N/A')}")
                            st.write(f"**Quantity:** {trade.get('quantity', 0)}")
                            st.write(f"**Order Type:** {trade.get('order_type', 'N/A')}")
                        
                        with col2:
                            if trade.get('limit_price'):
                                st.write(f"**Limit Price:** ${trade.get('limit_price', 0):.2f}")
                            st.write(f"**Status:** {trade.get('status', 'N/A')}")
                            st.write(f"**Order ID:** {trade.get('order_id', 'N/A')}")
                            if trade.get('executed_at'):
                                executed_time = datetime.fromisoformat(trade['executed_at'])
                                st.write(f"**Executed:** {executed_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.info("No trade history yet. Execute a trade to see it here.")
        except Exception as e:
            st.warning(f"⚠️ Could not load trade history: {str(e)}")
        
        st.markdown("---")
        st.subheader("IBKR Connection Status")
        
        try:
            # Get connection status
            status = trade_service.get_connection_status()
            
            if status.get("connected"):
                trading_mode = "Paper Trading" if status.get("paper_trading") else "Live Trading"
                st.success(f"✅ Connected to IBKR {trading_mode} (Port {status.get('port', 'N/A')})")
                
                # Show account summary if connected
                account_summary = trade_service.get_account_summary()
                if account_summary:
                    with st.expander("Account Summary"):
                        for key, value in account_summary.items():
                            st.write(f"**{key}**: {value['value']} {value['currency']}")
            else:
                st.warning("⚠️ Not connected to IBKR")
                st.info("💡 **To connect:**\n"
                        "1. Start TWS or IB Gateway\n"
                        "2. Enable API in TWS: File > Global Configuration > API > Settings\n"
                        "3. Uncheck 'Read-Only API' (if you want to trade)\n"
                        "4. Set Socket Port (check your IB Gateway settings - yours is 4002)\n"
                        "5. Click 'Connect to IBKR' below")
                
                if st.button("🔌 Connect to IBKR"):
                    with st.spinner("Connecting to IBKR (this may take a few seconds)..."):
                        import time
                        try:
                            # Small delay to ensure UI updates
                            time.sleep(0.1)
                            
                            # Try connection
                            connection_result = trade_service.connect()
                            
                            if connection_result:
                                st.success("✅ Connected to IBKR!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Connection failed")
                                st.info("**Troubleshooting:**\n"
                                        "- Make sure TWS/IB Gateway is running\n"
                                        "- Check API is enabled in TWS settings\n"
                                        "- Verify port number matches your IB Gateway (yours is 4002)\n"
                                        "- Check your .env file has correct IBKR_HOST and IBKR_PORT\n"
                                        "- Make sure 'Read-Only API' is unchecked if you want to trade\n"
                                        "- Try refreshing the page and connecting again")
                                st.info("💡 **Tip:** Check the terminal/logs for detailed error messages")
                        except Exception as e:
                            error_msg = str(e) if str(e) else repr(e)
                            st.error(f"❌ Connection error: {error_msg}")
                            st.exception(e)  # Show full traceback in expandable section
                            if "Connect call failed" in error_msg or "Connection refused" in error_msg:
                                st.info("This usually means TWS/IB Gateway is not running or API is not enabled.")
                            elif "event loop" in error_msg.lower():
                                st.info("Event loop issue - try refreshing the page.")
        except ImportError as e:
            st.error(f"IBKR not available: {str(e)}")
            st.info("💡 Install ib_insync: `pip install ib_insync`")
            st.info("💡 **If you just installed it, restart Streamlit:** `pkill -f streamlit` then `streamlit run dash/streamlit_app.py`")
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"Trade approval panel error: {e}")
    
    except Exception as e:
        st.error(f"Error loading trade approvals: {e}")
        logger.error(f"Trade approval panel error: {e}")

