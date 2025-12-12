"""
Hallucination Debugger - FuggerBot Diagnostic Tool

Audits trades marked as "MODEL_HALLUCINATION" to identify patterns in LLM failures.
Helps refine prompts and improve reasoning quality.

Author: FuggerBot AI Team
Version: v2.7 - Diagnostic Tools
"""
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from pathlib import Path
from collections import Counter

# Config
st.set_page_config(page_title="FuggerBot Hallucination Audit", layout="wide")
st.title("🔍 Hallucination Debugger")
st.markdown("**Audit LLM reasoning failures to improve prompt quality**")

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
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(trades)

# Check for post_mortem column
if 'post_mortem' not in df.columns:
    st.warning("⚠️ No post-mortem data available!")
    st.info("Run the reviewer daemon to generate analysis:")
    st.code("python daemon/reviewer.py", language="bash")
    st.stop()

# Extract outcome categories
df_with_pm = df[df['post_mortem'].notna()].copy()

if df_with_pm.empty:
    st.warning("No trades have been reviewed yet!")
    st.stop()

# Extract outcome_category from post_mortem dict
df_with_pm['outcome_category'] = df_with_pm['post_mortem'].apply(
    lambda x: x.get('outcome_category', 'UNKNOWN') if isinstance(x, dict) else 'UNKNOWN'
)

# Filter to hallucinations
df_halluc = df_with_pm[df_with_pm['outcome_category'] == 'MODEL_HALLUCINATION'].copy()

# Overview metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Trades", len(df))
with col2:
    st.metric("Reviewed Trades", len(df_with_pm))
with col3:
    halluc_count = len(df_halluc)
    st.metric("Hallucinations", halluc_count)
with col4:
    if len(df_with_pm) > 0:
        halluc_rate = halluc_count / len(df_with_pm)
        st.metric("Hallucination Rate", f"{halluc_rate:.1%}")
    else:
        st.metric("Hallucination Rate", "N/A")

st.markdown("---")

# === SECTION 1: Outcome Distribution ===
st.header("📊 Outcome Category Distribution")

outcome_counts = df_with_pm['outcome_category'].value_counts()

fig_outcomes = px.pie(
    values=outcome_counts.values,
    names=outcome_counts.index,
    title="Trade Outcomes Distribution",
    hole=0.4
)

st.plotly_chart(fig_outcomes, use_container_width=True)

st.markdown("---")

# === SECTION 2: Hallucination Analysis ===
if not df_halluc.empty:
    st.header("🔴 Hallucination Deep Dive")
    
    st.subheader(f"Found {len(df_halluc)} Hallucination Cases")
    
    # Extract root causes
    df_halluc['root_cause'] = df_halluc['post_mortem'].apply(
        lambda x: x.get('root_cause', 'Unknown') if isinstance(x, dict) else 'Unknown'
    )
    
    # Root cause distribution
    root_causes = df_halluc['root_cause'].value_counts()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Root Cause Frequency")
        fig_causes = px.bar(
            x=root_causes.index,
            y=root_causes.values,
            labels={'x': 'Root Cause', 'y': 'Count'},
            title="Common Hallucination Patterns"
        )
        st.plotly_chart(fig_causes, use_container_width=True)
    
    with col2:
        st.subheader("Symbol Distribution")
        symbol_counts = df_halluc['symbol'].value_counts()
        fig_symbols = px.bar(
            x=symbol_counts.index,
            y=symbol_counts.values,
            labels={'x': 'Symbol', 'y': 'Hallucination Count'},
            title="Hallucinations by Symbol"
        )
        st.plotly_chart(fig_symbols, use_container_width=True)
    
    st.markdown("---")
    
    # === SECTION 3: Hallucination Table ===
    st.subheader("📋 Hallucination Cases")
    
    display_cols = ['timestamp', 'symbol', 'decision', 'root_cause']
    if 'price' in df_halluc.columns:
        display_cols.append('price')
    
    halluc_display = df_halluc[display_cols].copy()
    halluc_display['timestamp'] = pd.to_datetime(halluc_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    st.dataframe(halluc_display, use_container_width=True, height=300)
    
    st.markdown("---")
    
    # === SECTION 4: Detailed Case Analysis ===
    st.subheader("🔬 Case-by-Case Analysis")
    
    selected_halluc_idx = st.selectbox(
        "Select Hallucination Case:",
        range(len(df_halluc)),
        format_func=lambda x: f"{df_halluc.iloc[x]['timestamp'][:10]} | "
                              f"{df_halluc.iloc[x]['symbol']} | "
                              f"{df_halluc.iloc[x]['root_cause']}"
    )
    
    selected_halluc = df_halluc.iloc[selected_halluc_idx]
    selected_pm = selected_halluc['post_mortem']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Root Cause", selected_pm.get('root_cause', 'Unknown'))
        st.metric("Outcome Category", selected_pm.get('outcome_category', 'Unknown'))
        
    with col2:
        st.metric("Adjusted Confidence", f"{selected_pm.get('adjusted_confidence', 0):.2f}")
        st.metric("Actual Outcome", selected_pm.get('actual_outcome', 'Unknown'))
    
    st.text_area("Lesson Learned:", selected_pm.get('lesson_learned', 'No lesson recorded'), height=150)
    
    # Show LLM response if available
    if 'llm_response' in selected_halluc and selected_halluc['llm_response']:
        with st.expander("💬 Original LLM Response"):
            llm_resp = selected_halluc['llm_response']
            if isinstance(llm_resp, dict):
                st.json(llm_resp)
            else:
                st.text(str(llm_resp))
    
    # Show trade context if available
    if 'trade_context' in selected_halluc:
        with st.expander("📊 Trade Context"):
            st.json(selected_halluc['trade_context'])

else:
    st.success("✅ No hallucinations detected!")
    st.balloons()
    st.info("The LLM reasoning quality appears strong. Keep monitoring.")

st.markdown("---")

# === SECTION 5: Temporal Analysis ===
st.header("📈 Hallucination Trends Over Time")

if not df_halluc.empty and 'timestamp' in df_halluc.columns:
    df_halluc['date'] = pd.to_datetime(df_halluc['timestamp']).dt.date
    daily_halluc = df_halluc.groupby('date').size().reset_index(name='count')
    
    fig_trend = px.line(
        daily_halluc,
        x='date',
        y='count',
        title="Hallucinations Per Day",
        labels={'date': 'Date', 'count': 'Hallucination Count'}
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.caption("💡 **Insight**: Look for spikes that correlate with regime changes or news events.")

st.markdown("---")

# === SECTION 6: Recommendations ===
st.header("💡 Recommendations")

if not df_halluc.empty:
    # Analyze most common root cause
    most_common_cause = df_halluc['root_cause'].mode()[0] if len(df_halluc) > 0 else "Unknown"
    halluc_rate = len(df_halluc) / len(df_with_pm) if len(df_with_pm) > 0 else 0
    
    st.subheader("Suggested Improvements:")
    
    if halluc_rate > 0.20:
        st.warning(f"⚠️ High hallucination rate ({halluc_rate:.1%}). Consider:")
        st.markdown("""
        - 🔧 **Refine LLM Prompt:** Add more explicit constraints
        - 📊 **Increase Trust Threshold:** Filter low-quality forecasts earlier
        - 🧠 **Enable Critique Agent:** Add more validation layers
        - 📉 **Reduce Position Size:** Limit exposure to uncertain trades
        """)
    
    if 'overconfident' in most_common_cause.lower():
        st.info("📉 **Pattern Detected:** LLM overconfidence. Consider adding calibration layer.")
    
    if 'news' in most_common_cause.lower():
        st.info("📰 **Pattern Detected:** News-driven errors. Improve news digest quality.")
    
else:
    st.success("✅ No issues detected. System reasoning quality is strong!")

st.markdown("---")

# === SECTION 7: Raw Data Explorer ===
with st.expander("🔍 Raw Trade Data"):
    if not df_halluc.empty:
        st.json(df_halluc.iloc[0].to_dict())
    else:
        st.info("No hallucination data to display")

st.markdown("---")
st.caption(f"📁 Data Source: `{MEMORY_FILE}`")
st.caption("🔄 Auto-refreshes every 30 seconds")

