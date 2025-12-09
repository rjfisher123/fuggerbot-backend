# Streamlit dashboard to control FuggerBot

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Page config
from components.icon_display import get_icon_path_for_page_config

icon_path = get_icon_path_for_page_config()

# Debug output (will show in terminal when Streamlit starts)
if icon_path:
    print(f"✅ Using icon: {icon_path}")
else:
    print("⚠️  No image file found. To use your portrait:")
    print("   1. Save your image as: assets/fuggerbot_icon.png")
    print("   2. Restart Streamlit")

st.set_page_config(
    page_title="FuggerBot Dashboard",
    page_icon=icon_path if icon_path else "🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import components
from components.forecast_panel import render_forecast_panel
from components.trade_approval import render_trade_approval
from components.trigger_panel import render_trigger_panel
from components.asset_view import render_asset_view
from components.paper_trading_panel import render_paper_trading_panel
from components.icon_display import display_icon_in_sidebar

# Sidebar navigation with icon and title
icon_shown = display_icon_in_sidebar()
st.sidebar.title("FuggerBot")
if icon_shown:
    st.sidebar.markdown("")  # Small spacing between icon and title
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Forecast Analysis",
        "💰 Trade Approval",
        "🎯 Triggers",
        "📈 Portfolio",
        "📊 Paper Trading"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    "FuggerBot: Automated trading bot with AI-powered forecasting and trust filtering."
)

# Main content area
if page == "📊 Forecast Analysis":
    render_forecast_panel()
elif page == "💰 Trade Approval":
    render_trade_approval()
elif page == "🎯 Triggers":
    render_trigger_panel()
elif page == "📈 Portfolio":
    render_asset_view()
elif page == "📊 Paper Trading":
    render_paper_trading_panel()
