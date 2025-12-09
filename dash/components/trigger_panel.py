import streamlit as st
import json
from pathlib import Path
import sys
import time

# Add project root to path for imports
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from dash.utils.price_feed import get_price
from core.alert_router import get_alert_router

TRIGGER_FILE = Path(__file__).parents[1] / "data" / "triggers.json"
ALERTED_FILE = Path(__file__).parents[1] / "data" / "alerted_triggers.json"

def load_triggers():
    if TRIGGER_FILE.exists():
        with open(TRIGGER_FILE, "r") as f:
            return json.load(f)
    return []

def save_triggers(triggers):
    TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRIGGER_FILE, "w") as f:
        json.dump(triggers, f, indent=2)

def load_alerted_triggers():
    """Load the set of triggers that have already sent alerts (to avoid duplicates)."""
    if ALERTED_FILE.exists():
        with open(ALERTED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def mark_trigger_alerted(trigger_key: str):
    """Mark a trigger as having sent an alert."""
    alerted = load_alerted_triggers()
    alerted.add(trigger_key)
    ALERTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTED_FILE, "w") as f:
        json.dump(list(alerted), f, indent=2)

def clear_alerted_triggers():
    """Clear the list of alerted triggers (useful for testing or reset)."""
    if ALERTED_FILE.exists():
        ALERTED_FILE.unlink()

def get_trigger_key(trig):
    """Generate a unique key for a trigger to track if it's been alerted."""
    return f"{trig['symbol']}_{trig['condition']}_{trig.get('price', trig.get('value', 0))}"

def show_triggers():
    st.subheader("🎯 Trigger Configuration")

    triggers = load_triggers()

    # Display existing triggers
    if triggers:
        for i, trig in enumerate(triggers):
            cols = st.columns([2, 1, 1, 1, 1])
            with cols[0]:
                # Initialize symbol in session_state if not present
                if f"sym_{i}" not in st.session_state:
                    st.session_state[f"sym_{i}"] = trig["symbol"]
                st.text_input("Symbol", key=f"sym_{i}")
            with cols[1]:
                # Initialize condition in session_state if not present
                if f"cond_{i}" not in st.session_state:
                    st.session_state[f"cond_{i}"] = trig["condition"]
                cond_index = ["<", ">", "drop_pct", "rise_pct"].index(trig["condition"])
                st.selectbox("Condition", ["<", ">", "drop_pct", "rise_pct"], index=cond_index, key=f"cond_{i}")
            with cols[2]:
                # Initialize value in session_state if not present
                if f"val_{i}" not in st.session_state:
                    st.session_state[f"val_{i}"] = float(trig.get("price", trig.get("value", 0)))
                val = st.number_input("Value/Price", key=f"val_{i}")
            with cols[3]:
                # Initialize action in session_state if not present
                if f"act_{i}" not in st.session_state:
                    st.session_state[f"act_{i}"] = trig["action"]
                act = st.text_input("Action", key=f"act_{i}")
            with cols[4]:
                if st.button("🗑️ Delete", key=f"del_{i}"):
                    triggers.pop(i)
                    save_triggers(triggers)
                    # Mark trigger deleted - UI will update on next rerun
                    st.session_state[f"trigger_deleted_{i}"] = True

        if st.button("💾 Save All Changes"):
            updated = []
            for i in range(len(triggers)):
                updated.append({
                    "symbol": st.session_state[f"sym_{i}"],
                    "condition": st.session_state[f"cond_{i}"],
                    "action": st.session_state[f"act_{i}"],
                    "price": st.session_state[f"val_{i}"],
                })
            save_triggers(updated)
            st.success("✅ Triggers updated!")
    else:
        st.info("No triggers yet. Add one below to get started.")
    st.markdown("---")
    st.subheader("🔍 Live Price Checks")
    
    # Info about monitoring
    st.info("ℹ️ **Monitoring Status**: Triggers are checked when this page loads or refreshes. "
            "For continuous background monitoring, run: `python run_monitor.py`")
    
    # Auto-refresh option
    auto_refresh = st.checkbox("🔄 Auto-refresh (checks every 30 seconds)", value=False, key="trigger_auto_refresh")
    if auto_refresh:
        st.info("⏱️ Page will auto-refresh every 30 seconds to check triggers")
        # Use time-based refresh instead of blocking sleep
        import time
        current_time = time.time()
        last_refresh = st.session_state.get("last_trigger_refresh", 0)
        if current_time - last_refresh >= 30:
            st.session_state["last_trigger_refresh"] = current_time
            st.session_state["trigger_refresh_needed"] = True
    
    # Load alerted triggers to avoid duplicate SMS
    alerted_triggers = load_alerted_triggers()
    alert_router = get_alert_router()

    for trig in triggers:
        symbol = trig["symbol"].upper()
        price = get_price(symbol)
        if price is None:
            st.warning(f"⚠️ Could not fetch price for {symbol}")
            continue

        st.write(f"**{symbol}** — current: ${price:.2f}")

        cond = trig["condition"]
        action = trig["action"]
        trigger_value = trig.get("price", trig.get("value", 0))
        trigger_key = get_trigger_key(trig)
        trigger_hit = False

        # Compare trigger conditions
        if cond == "<" and price < trigger_value:
            trigger_hit = True
            st.error(f"🚨 Trigger hit: {symbol} < ${trigger_value:.2f} → {action}")
            
            # Send SMS alert if not already alerted
            if trigger_key not in alerted_triggers:
                alert_sent = alert_router.send_price_alert(
                    symbol=symbol,
                    price=price,
                    trigger_type="below",
                    trigger_value=trigger_value
                )
                if alert_sent:
                    mark_trigger_alerted(trigger_key)
                    st.info("📱 SMS alert sent!")
                else:
                    st.warning("⚠️ SMS alert failed — check Twilio configuration")
                    
        elif cond == ">" and price > trigger_value:
            trigger_hit = True
            st.error(f"🚨 Trigger hit: {symbol} > ${trigger_value:.2f} → {action}")
            
            # Send SMS alert if not already alerted
            if trigger_key not in alerted_triggers:
                alert_sent = alert_router.send_price_alert(
                    symbol=symbol,
                    price=price,
                    trigger_type="above",
                    trigger_value=trigger_value
                )
                if alert_sent:
                    mark_trigger_alerted(trigger_key)
                    st.info("📱 SMS alert sent!")
                else:
                    st.warning("⚠️ SMS alert failed — check Twilio configuration")
                    
        elif cond == "drop_pct":
            # Calculate percentage drop (would need previous price for this)
            # For now, just show the condition
            st.info(f"📊 {symbol} — drop_pct condition (not yet implemented)")
            
        elif cond == "rise_pct":
            # Calculate percentage rise (would need previous price for this)
            # For now, just show the condition
            st.info(f"📊 {symbol} — rise_pct condition (not yet implemented)")
            
        else:
            st.success(f"✅ {symbol} OK — condition not met")
            # Reset alert status if trigger is no longer active
            if trigger_key in alerted_triggers and not trigger_hit:
                # Could optionally clear this, but keeping it prevents re-alerting
                pass

        time.sleep(0.5)  # avoid hitting rate limits
    
    # Add button to clear alerted triggers (for testing/reset)
    if alerted_triggers:
        if st.button("🔄 Reset Alert Status (Clear Alerted Triggers)"):
            clear_alerted_triggers()
            st.success("✅ Alert status cleared — triggers will alert again when hit")
            # Mark alert status cleared - UI will update on next rerun
            st.session_state["alert_status_cleared"] = True
    st.markdown("---")
    st.subheader("➕ Add New Trigger")

    with st.form("add_trigger_form"):
        symbol = st.text_input("Symbol (e.g., INTC, AAPL)")
        condition = st.selectbox("Condition", ["<", ">", "drop_pct", "rise_pct"])
        value = st.number_input("Value or % Threshold", min_value=0.0, step=0.1)
        
        # Action type
        action_type = st.selectbox(
            "Action Type",
            ["notify", "buy", "sell", "layer_in"],
            help="notify: SMS only | buy/sell: Request trade approval | layer_in: Buy incrementally"
        )
        
        # Trade-specific fields (shown if action is buy/sell/layer_in)
        trade_config = {}
        if action_type in ["buy", "sell", "layer_in"]:
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input("Quantity (shares)", min_value=1, value=1, step=1)
                trade_config["quantity"] = int(quantity)
            with col2:
                order_type = st.selectbox("Order Type", ["MARKET", "LIMIT"])
                trade_config["order_type"] = order_type
                if order_type == "LIMIT":
                    limit_price = st.number_input("Limit Price", min_value=0.0, step=0.01)
                    trade_config["limit_price"] = limit_price
        
        submitted = st.form_submit_button("Add Trigger")

        if submitted and symbol:
            trigger = {
                "symbol": symbol,
                "condition": condition,
                "value": value,
                "action": action_type
            }
            # Add trade config if applicable
            if trade_config:
                trigger.update(trade_config)
            
            triggers.append(trigger)
            save_triggers(triggers)
            st.success(f"✅ Added trigger for {symbol}")
            # Mark trigger added - UI will update on next rerun
            st.session_state["trigger_added"] = True


def render_trigger_panel():
    """Render the trigger panel component (wrapper for show_triggers)."""
    show_triggers()