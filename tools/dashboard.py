import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

# Config
st.set_page_config(page_title="FuggerBot Brain Scan", layout="wide")
st.title("🧠 FuggerBot Reasoning State")

# --- SIDEBAR CONFIG ---
st.sidebar.header("Configuration")
data_source = st.sidebar.radio(
    "Select Memory Source:",
    ("Live Production", "War Games Simulation"),
    index=0
)

# Map selection to filename
if data_source == "Live Production":
    MEMORY_FILE = project_root / "data" / "trade_memory.json"
else:
    MEMORY_FILE = project_root / "data" / "test_memory_wargames.json"

st.sidebar.info(f"Reading from: `{MEMORY_FILE}`")


@st.cache_data(ttl=5)
def load_data(filepath):
    """Load trade memory data from JSON file."""
    filepath = Path(filepath)
    if not filepath.exists():
        return pd.DataFrame()
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()
    
    if not data or 'trades' not in data:
        return pd.DataFrame()
    
    trades = data.get('trades', [])
    if not trades:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(trades)
    
    # Ensure numeric columns
    if 'confidence' in df.columns:
        df['llm_confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    if 'pnl' in df.columns:
        # Convert pnl to numeric, handling None/null values
        df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce')
        # Replace NaN with None for proper null checking
        df['pnl'] = df['pnl'].where(pd.notna(df['pnl']), None)
    if 'forecast_confidence' in df.columns:
        df['forecast_confidence'] = pd.to_numeric(df['forecast_confidence'], errors='coerce')
    if 'trust_score' in df.columns:
        df['trust_score'] = pd.to_numeric(df['trust_score'], errors='coerce')
    
    # Extract outcome type
    if 'outcome' in df.columns:
        df['outcome_type'] = df['outcome']
    elif 'regret' in df.columns:
        df['outcome_type'] = df['regret'].apply(lambda x: 'MISSED_OP' if x == 'MISSED_OP' else 'NORMAL')
    else:
        df['outcome_type'] = None
    
    return df


df = load_data(MEMORY_FILE)

if df.empty:
    st.warning(f"No data found in {MEMORY_FILE}. Run the bot to generate memory!")
    st.stop()

# --- KPI ROW ---
col1, col2, col3, col4 = st.columns(4)

# Calculate Metrics
approvals = df[df['decision'] == "APPROVE"] if 'decision' in df.columns else pd.DataFrame()
rejections = df[df['decision'] == "REJECT"] if 'decision' in df.columns else pd.DataFrame()

# Hit Rate (Requires PnL to be populated)
# Check if we have any non-null PnL values
has_pnl = 'pnl' in df.columns and df['pnl'].notna().any()

if has_pnl:
    # Filter approvals that have PnL values
    approvals_with_pnl = approvals[approvals['pnl'].notna()]
    if not approvals_with_pnl.empty:
        hit_rate = len(approvals_with_pnl[approvals_with_pnl['pnl'] > 0]) / len(approvals_with_pnl)
        avg_pnl = approvals_with_pnl['pnl'].sum()
    else:
        hit_rate = 0
        avg_pnl = 0
    
    # Filter rejections that have PnL values (for regret tracking)
    rejections_with_pnl = rejections[rejections['pnl'].notna()]
    if not rejections_with_pnl.empty:
        regret_count = len(rejections_with_pnl[rejections_with_pnl['pnl'] > 0])
        regret_rate = regret_count / len(rejections_with_pnl)
    else:
        regret_rate = 0
else:
    hit_rate = 0
    regret_rate = 0
    avg_pnl = 0

col1.metric("Hit Rate (Precision)", f"{hit_rate:.1%}" if has_pnl else "N/A", delta_color="normal")
col2.metric("Regret Rate (FOMO)", f"{regret_rate:.1%}" if has_pnl else "N/A", delta_color="inverse")
col3.metric("Total System PnL", f"${avg_pnl:.2f}" if has_pnl else "N/A")
col4.metric("Total Trades", len(df))

# --- CHARTS ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("Decision Boundary")
    if 'trust_score' in df.columns and 'llm_confidence' in df.columns:
        # Filter out NaN values
        plot_df = df[df['trust_score'].notna() & df['llm_confidence'].notna()].copy()
        
        if not plot_df.empty:
            # Scatter plot: Trust Score vs LLM Confidence, colored by Outcome
            fig = px.scatter(
                plot_df, 
                x="trust_score", 
                y="llm_confidence", 
                color="decision",
                symbol="outcome_type" if 'outcome_type' in plot_df.columns and plot_df['outcome_type'].notna().any() else None,
                hover_data=["symbol", "rationale"] if 'rationale' in plot_df.columns else ["symbol"],
                title="Did the LLM agree with the Trust Score?",
                color_discrete_map={"APPROVE": "green", "REJECT": "red", "WAIT": "orange"}
            )
            fig.add_hline(y=0.75, line_dash="dash", annotation_text="Confidence Threshold", line_color="gray")
            fig.add_vline(x=0.6, line_dash="dash", annotation_text="Trust Threshold", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Insufficient data for scatter plot (missing trust_score or llm_confidence).")
    else:
        st.info("Insufficient data for scatter plot.")

with c2:
    st.subheader("Recent Activity")
    if not approvals.empty and 'llm_confidence' in approvals.columns:
        # Get recent approvals
        recent_approvals = approvals.head(20).copy()
        if 'timestamp' in recent_approvals.columns:
            recent_approvals['timestamp'] = pd.to_datetime(recent_approvals['timestamp'], errors='coerce')
            recent_approvals = recent_approvals.sort_values('timestamp', ascending=False)
        
        fig2 = px.bar(
            recent_approvals, 
            x="symbol" if 'symbol' in recent_approvals.columns else recent_approvals.index, 
            y="llm_confidence", 
            color="symbol" if 'symbol' in recent_approvals.columns else None,
            title="Recent Approved Trades Confidence",
            labels={"llm_confidence": "LLM Confidence", "symbol": "Symbol"}
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No approvals yet or missing confidence data.")

# --- RAW DATA ---
st.subheader("Reasoning Logs")
cols_to_show = ['timestamp', 'symbol', 'decision', 'llm_confidence', 'trust_score', 'rationale']
available_cols = [col for col in cols_to_show if col in df.columns]

if has_pnl and 'pnl' in df.columns:
    if 'pnl' not in available_cols:
        available_cols.insert(5, 'pnl')

# Sort by timestamp if available
sort_col = 'timestamp' if 'timestamp' in df.columns else None
if sort_col:
    df_display = df[available_cols].sort_values('timestamp', ascending=False)
else:
    df_display = df[available_cols]

st.dataframe(
    df_display,
    use_container_width=True
)

