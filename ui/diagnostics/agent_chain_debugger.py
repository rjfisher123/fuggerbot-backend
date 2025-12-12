"""
Agent Chain Debugger - FuggerBot Diagnostic Tool

Visualizes the TRM decision waterfall showing how confidence evolves through each agent:
Forecast → Trust → News → Memory → Critique → Policy → Final Verdict

Shows why trades get rejected at each stage.

Author: FuggerBot AI Team
Version: v2.7 - Diagnostic Tools
"""
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

# Config
st.set_page_config(page_title="FuggerBot Agent Chain", layout="wide")
st.title("🔗 Agent Chain Debugger")
st.markdown("**Waterfall analysis: How confidence evolves through the TRM pipeline**")

# Load trade memory
PROJECT_ROOT = Path(__file__).parent.parent.parent
MEMORY_FILE = PROJECT_ROOT / "data" / "trade_memory.json"

@st.cache_data(ttl=30)
def load_trade_memory():
    """Load trade memory data."""
    if not MEMORY_FILE.exists():
        return None
    
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = json.load(f)
        return data.get('trades', [])
    except Exception as e:
        st.error(f"Error loading trade memory: {e}")
        return None

trades = load_trade_memory()

if not trades:
    st.warning("⚠️ No trade data found!")
    st.info("Run the trading bot to generate memory:")
    st.code("python run_bot.py", language="bash")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(trades)

# Filter to trades with TRM details
if 'trm_details' in df.columns:
    df_with_trm = df[df['trm_details'].notna()].copy()
else:
    st.error("No TRM details found in trade memory!")
    st.info("TRM details require FuggerBot v2.0+")
    st.stop()

if df_with_trm.empty:
    st.warning("No trades with TRM details yet!")
    st.stop()

# === TASK A: CALCULATE CRITIC ACTIVITY ===
# Extract proposer and final confidence for critic analysis
df_with_trm['proposer_confidence'] = df_with_trm['trm_details'].apply(
    lambda x: x.get('waterfall_steps', {}).get('llm_confidence', 0) if isinstance(x, dict) else 0
)
df_with_trm['final_confidence'] = df_with_trm['trm_details'].apply(
    lambda x: x.get('waterfall_steps', {}).get('final_confidence', 0) if isinstance(x, dict) else 0
)
df_with_trm['critic_delta'] = df_with_trm['proposer_confidence'] - df_with_trm['final_confidence']
df_with_trm['critic_active'] = df_with_trm['critic_delta'] > 0.1

# Calculate critic activity metrics
critic_active_count = df_with_trm['critic_active'].sum()
critic_activity_rate = critic_active_count / len(df_with_trm) if len(df_with_trm) > 0 else 0

# Overview metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Trades", len(df))
with col2:
    st.metric("With TRM Details", len(df_with_trm))
with col3:
    approved = (df['decision'] == 'APPROVE').sum()
    st.metric("Approved Rate", f"{approved/len(df):.1%}")
with col4:
    st.metric("Critic Active", critic_active_count, delta=f"{critic_activity_rate:.1%}")

# === ACTIVE CRITIC ALERT ===
if critic_active_count > 0:
    avg_critic_delta = df_with_trm[df_with_trm['critic_active']]['critic_delta'].mean()
    st.info(
        f"💡 **Critic Active:** {critic_active_count} trades where Critic adjusted confidence by "
        f">{0.1:.0%} (Avg adjustment: {avg_critic_delta:.1%})"
    )

st.markdown("---")

# === SECTION 1: Select Trade for Analysis ===
st.header("🔍 Trade Selection")

# Create trade selector
trade_options = df_with_trm.apply(
    lambda row: f"{row['timestamp'][:10]} | {row['symbol']} | {row['decision']} | "
                f"${row.get('price', 0):.2f}",
    axis=1
).tolist()

selected_idx = st.selectbox(
    "Select Trade to Analyze:",
    range(len(df_with_trm)),
    format_func=lambda x: trade_options[x]
)

trade = df_with_trm.iloc[selected_idx]
trm = trade.get('trm_details', {})

# === CRITIC ACTIVITY ALERT FOR THIS TRADE ===
if trade.get('critic_active', False):
    critic_delta = trade.get('critic_delta', 0)
    st.warning(
        f"🧠 **CRITIC WAS ACTIVE ON THIS TRADE!** Reduced confidence by {critic_delta:.1%} "
        f"(Proposer: {trade.get('proposer_confidence', 0):.2f} → "
        f"Final: {trade.get('final_confidence', 0):.2f})"
    )

# Display trade overview
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Symbol", trade['symbol'])
with col2:
    st.metric("Decision", trade['decision'])
with col3:
    st.metric("Price", f"${trade.get('price', 0):.2f}")
with col4:
    st.metric("Timestamp", trade['timestamp'][:10])

st.markdown("---")

# === SECTION 2: Confidence Waterfall ===
st.header("🌊 Confidence Waterfall")
st.caption("Shows how confidence changes at each TRM stage")

# Extract waterfall data
waterfall_steps = trm.get('waterfall_steps', {})

if waterfall_steps:
    stages = [
        ('Forecast', waterfall_steps.get('forecast_confidence', 0)),
        ('Trust Filter', waterfall_steps.get('trust_score', 0)),
        ('LLM Decision', waterfall_steps.get('llm_confidence', 0)),
        ('Final Verdict', waterfall_steps.get('final_confidence', 0))
    ]
    
    # Create waterfall chart
    stage_names = [s[0] for s in stages]
    values = [s[1] for s in stages]
    
    # Calculate deltas
    deltas = [values[0]]  # First value is absolute
    for i in range(1, len(values)):
        deltas.append(values[i] - values[i-1])
    
    # Create figure
    fig = go.Figure(go.Waterfall(
        name="Confidence",
        orientation="v",
        measure=["absolute"] + ["relative"] * (len(stages) - 1),
        x=stage_names,
        y=deltas,
        text=[f"{v:.2f}" for v in values],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(
        title="Confidence Evolution Through TRM Pipeline",
        yaxis_title="Confidence Score",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show adjustment
    adjustment = waterfall_steps.get('confidence_adjustment', 0)
    if adjustment < 0:
        st.error(f"⚠️ Confidence reduced by {abs(adjustment):.1%} through pipeline")
    else:
        st.success(f"✅ Confidence improved by {adjustment:.1%} through pipeline")

else:
    st.warning("No waterfall data available for this trade")

st.markdown("---")

# === SECTION 3: Agent Impact Analysis ===
st.header("🎯 Agent Impact Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("News Impact")
    news_impact = trm.get('news_impact', 'UNKNOWN')
    news_sentiment = trm.get('news_sentiment', 'NEUTRAL')
    news_summary = trm.get('news_summary', 'No news data')
    
    st.metric("Impact Level", news_impact)
    st.metric("Sentiment", news_sentiment)
    st.text_area("Summary", news_summary, height=100)

with col2:
    st.subheader("Memory Analysis")
    mem_win_rate = trm.get('memory_win_rate', 0)
    mem_halluc_rate = trm.get('memory_hallucination_rate', 0)
    
    st.metric("Historical Win Rate", f"{mem_win_rate:.1%}")
    st.metric("Hallucination Rate", f"{mem_halluc_rate:.1%}")

st.markdown("---")

# === SECTION 4: Policy Decisions ===
st.header("🛡️ Policy Layer Analysis")

policy_veto = trm.get('policy_veto', False)
veto_reason = trm.get('policy_veto_reason', 'N/A')
override_reason = trm.get('override_reason', 'N/A')

col1, col2 = st.columns(2)

with col1:
    if policy_veto:
        st.error("❌ VETOED by Policy Layer")
        st.text_area("Veto Reason:", veto_reason, height=100)
    else:
        st.success("✅ Passed Policy Layer")

with col2:
    st.text_area("Override Reason:", override_reason, height=100)

# Critic analysis
critic_flaws = trm.get('critic_flaws', 0)
critic_confidence = trm.get('critic_confidence', 0)

col1, col2 = st.columns(2)
with col1:
    st.metric("Critic Flaws Found", critic_flaws)
with col2:
    st.metric("Critic Confidence", f"{critic_confidence:.2f}")

st.markdown("---")

# === SECTION 5: Rejection Analysis ===
if trade['decision'] == 'REJECT':
    st.header("🔴 Rejection Analysis")
    
    rejection_stage = trade.get('stage', 'unknown')
    rejection_reason = trade.get('reason', 'No reason provided')
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Rejected At", rejection_stage.upper())
    with col2:
        st.text_area("Reason:", rejection_reason, height=80)
    
    # Show what would have changed decision
    st.subheader("💡 What Would Have Approved This Trade?")
    
    if 'Trust' in rejection_reason or rejection_stage == 'trust':
        st.info(
            f"✅ Lower trust_threshold from {waterfall_steps.get('trust_score', 0):.2f} "
            f"to {waterfall_steps.get('trust_score', 0) * 0.9:.2f}"
        )
    
    if 'confidence' in rejection_reason.lower() or rejection_stage == 'llm':
        st.info(
            f"✅ Lower min_confidence from {waterfall_steps.get('llm_confidence', 0):.2f} "
            f"to {waterfall_steps.get('llm_confidence', 0) * 0.9:.2f}"
        )
    
    if 'News' in rejection_reason or 'news' in rejection_stage.lower():
        st.info("✅ Enable 'Ignore News' mode or wait for sentiment to improve")

st.markdown("---")

# === SECTION 6: Raw TRM Data ===
with st.expander("🔍 Raw TRM Details"):
    st.json(trm)

st.markdown("---")
st.caption(f"📁 Data Source: `{MEMORY_FILE}`")
st.caption("🔄 Auto-refreshes every 30 seconds")

