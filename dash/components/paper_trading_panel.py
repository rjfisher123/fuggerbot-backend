"""Streamlit component for paper trading simulation."""
import streamlit as st
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from models.paper_trading import PaperTradingEngine
from models.forecast_metadata import ForecastMetadata
from dash.utils.price_feed import get_price
from execution.ibkr import get_paper_trading_trader
from core.logger import logger


def render_paper_trading_panel():
    """Render the paper trading panel."""
    st.subheader("📊 Paper Trading Simulation")
    
    # Initialize paper trading engine (with session state)
    if "paper_trader" not in st.session_state:
        st.session_state.paper_trader = PaperTradingEngine(initial_capital=100000.0)
    
    paper_trader = st.session_state.paper_trader
    
    # Portfolio Summary
    st.markdown("---")
    st.subheader("💰 Portfolio Summary")
    
    summary = paper_trader.get_portfolio_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Initial Capital", f"${summary['initial_capital']:,.2f}")
    with col2:
        total_return = summary['total_return_pct']
        st.metric("Total Return", f"{total_return:.2f}%",
                 delta=f"${summary['total_capital'] - summary['initial_capital']:,.2f}")
    with col3:
        st.metric("Win Rate", f"{summary['win_rate']:.1f}%")
    with col4:
        st.metric("Closed Trades", summary['closed_trades'])
    
    # Open Positions
    if summary['open_positions'] > 0:
        st.markdown("---")
        st.subheader("📈 Open Positions")
        
        positions_data = []
        for symbol, position in paper_trader.positions.items():
            current_price = get_price(symbol) or position['entry_price']
            current_value = position['shares'] * current_price
            unrealized_pnl = current_value - position['position_value']
            unrealized_pnl_pct = (unrealized_pnl / position['position_value']) * 100
            
            positions_data.append({
                "Symbol": symbol,
                "Entry Price": f"${position['entry_price']:.2f}",
                "Current Price": f"${current_price:.2f}",
                "Shares": f"{position['shares']:.2f}",
                "Position Value": f"${position['position_value']:,.2f}",
                "Unrealized P/L": f"${unrealized_pnl:.2f}",
                "Unrealized P/L %": f"{unrealized_pnl_pct:.2f}%",
                "Forecast ID": position['forecast_id'][:8]
            })
        
        st.dataframe(pd.DataFrame(positions_data), use_container_width=True)
        
        # Close position controls
        st.markdown("**Close Positions:**")
        for symbol in paper_trader.positions.keys():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{symbol}**")
            with col2:
                if st.button(f"Close {symbol}", key=f"close_{symbol}"):
                    current_price = get_price(symbol)
                    if current_price:
                        result = paper_trader.close_position(symbol, current_price, "manual")
                        if "error" not in result:
                            st.success(f"✅ Closed {symbol}: P/L ${result['pnl']:.2f} ({result['pnl_pct']:.2f}%)")
                            # Mark position closed - UI will update on next rerun
                            st.session_state[f"position_closed_{symbol}"] = True
                    else:
                        st.error(f"Could not get price for {symbol}")
    
    # Trade History
    if summary['closed_trades'] > 0:
        st.markdown("---")
        st.subheader("📜 Trade History")
        
        history_data = []
        for trade in paper_trader.trade_history[-20:]:  # Last 20 trades
            history_data.append({
                "Symbol": trade['symbol'],
                "Entry": f"${trade['entry_price']:.2f}",
                "Exit": f"${trade['exit_price']:.2f}",
                "P/L": f"${trade['pnl']:.2f}",
                "P/L %": f"{trade['pnl_pct']:.2f}%",
                "Exit Reason": trade['exit_reason'],
                "Holding Days": trade['holding_period_days']
            })
        
        st.dataframe(pd.DataFrame(history_data), use_container_width=True)
    
    # IBKR Paper Trading Integration
    st.markdown("---")
    st.subheader("🔗 IBKR Paper Trading Integration")
    
    try:
        ibkr_paper_trader = get_paper_trading_trader()
        if ibkr_paper_trader.connected:
            st.success(f"✅ Connected to IBKR Paper Trading (Port {ibkr_paper_trader.port})")
            
            # Option to execute paper trades through IBKR
            with st.expander("📤 Execute Paper Trade via IBKR"):
                st.info("💡 This will execute a trade in your IBKR **paper trading account** (not real money).")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    # Initialize symbol in session_state if not present
                    if "ibkr_paper_symbol" not in st.session_state:
                        st.session_state["ibkr_paper_symbol"] = "AAPL"
                    ibkr_symbol = st.text_input("Symbol", key="ibkr_paper_symbol").upper()
                with col2:
                    ibkr_action = st.selectbox("Action", ["BUY", "SELL"], key="ibkr_paper_action")
                with col3:
                    ibkr_quantity = st.number_input("Quantity", min_value=1, value=1, step=1, key="ibkr_paper_quantity")
                
                if st.button("📤 Execute IBKR Paper Trade", key="ibkr_paper_execute"):
                    try:
                        result = ibkr_paper_trader.execute_trade(
                            symbol=ibkr_symbol,
                            action=ibkr_action,
                            quantity=ibkr_quantity,
                            order_type="MARKET",
                            require_confirmation=False  # Paper trading - no approval needed
                        )
                        
                        if result.get("success"):
                            st.success(f"✅ Paper trade executed: {ibkr_action} {ibkr_quantity} {ibkr_symbol}")
                            
                            # Also add to paper trading engine for tracking
                            entry_price = result.get("avg_fill_price", 0)
                            if entry_price:
                                position = paper_trader.open_position(
                                    symbol=ibkr_symbol,
                                    forecast_id="IBKR_PAPER",
                                    entry_price=entry_price,
                                    forecast_data={},
                                    regime_data={"regime": "normal"},
                                    position_size_pct=2.0
                                )
                                st.info(f"📊 Position also added to paper trading portfolio for tracking")
                            # Mark trade executed - UI will update on next rerun
                            st.session_state["ibkr_paper_trade_executed"] = True
                        else:
                            st.error(f"❌ Trade failed: {result.get('message', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        logger.error(f"IBKR paper trade error: {e}", exc_info=True)
        else:
            st.info("💡 Connect to IBKR Paper Trading to execute trades in your paper account. This uses IBKR's paper trading API (port 7497).")
            if st.button("🔌 Connect to IBKR Paper Trading"):
                with st.spinner("Connecting to IBKR Paper Trading..."):
                    if ibkr_paper_trader.connect():
                        st.success("✅ Connected to IBKR Paper Trading!")
                        # Mark connection status - will update on next natural rerun
                        st.session_state["ibkr_paper_connected"] = True
                    else:
                        st.error("❌ Failed to connect. Make sure IB Gateway is running in paper trading mode.")
    except Exception as e:
        st.warning(f"⚠️ IBKR Paper Trading not available: {str(e)}")
    
    # Virtual Paper Trading (simulation)
    st.markdown("---")
    st.subheader("🆕 Open New Position (Virtual Simulation)")
    st.info("💡 **Virtual Paper Trading**: This is a pure simulation - no IBKR connection required. Use this to test strategies risk-free without any broker connection.")
    
    with st.form("open_position_form"):
        # Initialize symbol in session_state if not present
        if "paper_symbol" not in st.session_state:
            st.session_state["paper_symbol"] = "AAPL"
        symbol = st.text_input("Symbol", key="paper_symbol").upper()
        forecast_id = st.text_input("Forecast ID (optional)", key="paper_forecast_id")
        entry_price = st.number_input("Entry Price", min_value=0.01, step=0.01, key="paper_entry_price")
        position_size_pct = st.number_input("Position Size (%)", min_value=0.1, max_value=10.0, value=2.0, step=0.1, key="paper_size")
        
        submitted = st.form_submit_button("Open Position")
        
        if submitted:
            if not symbol:
                st.error("Please enter a symbol")
            elif entry_price <= 0:
                st.error("Please enter a valid entry price")
            else:
                # Load forecast if ID provided
                forecast_data = {}
                regime_data = {"regime": "normal", "regime_label": "Normal Regime"}
                
                if forecast_id:
                    metadata = ForecastMetadata()
                    snapshot = metadata.load_forecast_snapshot(forecast_id)
                    if snapshot:
                        forecast_data = snapshot
                        regime_data = snapshot.get("trust_evaluation", {}).get("regime", regime_data)
                
                try:
                    position = paper_trader.open_position(
                        symbol=symbol,
                        forecast_id=forecast_id or "MANUAL",
                        entry_price=entry_price,
                        forecast_data=forecast_data,
                        regime_data=regime_data,
                        position_size_pct=position_size_pct
                    )
                    st.success(f"✅ Opened position: {symbol} @ ${entry_price:.2f}")
                    # Mark position opened - UI will update on next rerun
                    st.session_state["paper_position_opened"] = True
                except Exception as e:
                    st.error(f"❌ Error opening position: {str(e)}")
                    logger.error(f"Paper trading error: {e}", exc_info=True)
    
    # Portfolio Actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Trade History"):
            filepath = paper_trader.save_trade_history()
            st.success(f"✅ Saved to: {filepath}")
    
    with col2:
        if st.button("🔄 Reset Portfolio"):
            if st.session_state.get("confirm_reset"):
                st.session_state.paper_trader = PaperTradingEngine(initial_capital=100000.0)
                st.success("✅ Portfolio reset")
                # Clear confirmation flag
                del st.session_state.confirm_reset
                # Mark reset - UI will update on next rerun
                st.session_state["portfolio_reset"] = True
            else:
                st.session_state.confirm_reset = True
                st.warning("Click again to confirm reset")
    
    with col3:
        if st.button("📊 Export Report"):
            summary = paper_trader.get_portfolio_summary()
            st.json(summary)

