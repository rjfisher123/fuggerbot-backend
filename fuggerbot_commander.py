"""
FuggerBot Commander - Unified Navigation Interface

A single Streamlit app with categorized navigation to all diagnostic tools.
Replaces the need to run 8 separate Streamlit instances on different ports.

Author: FuggerBot AI Team
Version: v2.8 - Unified Navigation
"""
import streamlit as st

# Page Configuration must be the first Streamlit command
st.set_page_config(page_title="FuggerBot Commander", layout="wide", page_icon="🤖")

# Define the Page Map
# We point directly to the existing files you have already built.
pages = {
    "Mission Control": [
        st.Page("tools/dashboard.py", title="Main Operations", icon="🚀"),
        st.Page("ui/diagnostics/macro_dashboard.py", title="Macro God View", icon="🌍"),
    ],
    "Deep Diagnostics": [
        st.Page("ui/diagnostics/agent_chain_debugger.py", title="Agent Brain Scan", icon="🧠"),
        st.Page("ui/diagnostics/hallucination_debugger.py", title="Hallucination Auditor", icon="😵‍💫"),
        st.Page("ui/diagnostics/regime_param_view.py", title="Regime Parameters", icon="⚙️"),
    ],
    "Trade Forensics": [
        st.Page("ui/trade_outcomes/rejected_profitable_view.py", title="FOMO Analysis (Missed Wins)", icon="📈"),
        st.Page("ui/trade_outcomes/approved_lossmaking_view.py", title="Pain Analysis (Bad Calls)", icon="📉"),
        st.Page("ui/trade_outcomes/wouldve_hit_view.py", title="What-If Simulator", icon="🔮"),
    ]
}

# Sidebar branding
st.sidebar.title("🤖 FuggerBot v2.8")
st.sidebar.info("System Status: 🟢 ONLINE")

st.sidebar.markdown("---")
st.sidebar.caption("**Unified Command Interface**")
st.sidebar.caption("Navigate using the menu above ☝️")

# Run the Navigation
pg = st.navigation(pages)
pg.run()





