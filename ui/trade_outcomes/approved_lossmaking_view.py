"""
Approved Lossmaking View - "The Pain Chart"

Shows trades the bot approved that lost money.
Critical for identifying flawed reasoning patterns and improving the LLM.

Author: FuggerBot AI Team  
Version: v2.7 - Trade Outcome Analysis
"""
import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Config
st.set_page_config(page_title="FuggerBot Pain Analysis", layout="wide")
st.title("💔 The Pain Chart - Approved Losing Trades")
st.markdown("**Trades we approved that lost money**")

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

df = pd.DataFrame(trades)

# Filter to approved trades with post_mortem
if 'post_mortem' not in df.columns:
    st.warning("No post-mortem data! Run reviewer daemon.")
    st.stop()

df_with_pm = df[df['post_mortem'].notna()].copy()

if df_with_pm.empty:
    st.warning("No trades have been reviewed yet!")
    st.stop()

# Extract outcome category
df_with_pm['outcome_category'] = df_with_pm['post_mortem'].apply(
    lambda x: x.get('outcome_category', 'UNKNOWN') if isinstance(x, dict) else 'UNKNOWN'
)

# Filter to approved trades that lost money
# Outcome categories we want: MODEL_HALLUCINATION (approved but wrong)
# Or any approved trade with negative outcome
df_pain = df_with_pm[
    (df_with_pm['decision'] == 'APPROVE') & 
    (
        (df_with_pm['outcome_category'] == 'MODEL_HALLUCINATION') |
        (df_with_pm['outcome_category'].str.contains('LOSS', case=False, na=False))
    )
].copy()

# Overview metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Approved", (df['decision'] == 'APPROVE').sum())
with col2:
    st.metric("Reviewed", len(df_with_pm))
with col3:
    pain_count = len(df_pain)
    st.metric("Loss Cases", pain_count, delta=None if pain_count == 0 else "💔")
with col4:
    if len(df_with_pm) > 0:
        pain_rate = pain_count / len(df_with_pm)
        st.metric("Loss Rate", f"{pain_rate:.1%}")
    else:
        st.metric("Loss Rate", "N/A")

st.markdown("---")

if df_pain.empty:
    st.success("✅ No painful losses detected!")
    st.balloons()
    st.info("All approved trades were profitable or pending. Excellent decision quality!")
    st.stop()

# === SECTION 1: Pain Table ===
st.header(f"💔 {len(df_pain)} Approved Losing Trades")

# Extract useful columns
df_pain['root_cause'] = df_pain['post_mortem'].apply(
    lambda x: x.get('root_cause', 'Unknown') if isinstance(x, dict) else 'Unknown'
)
df_pain['lesson_learned'] = df_pain['post_mortem'].apply(
    lambda x: x.get('lesson_learned', 'No lesson') if isinstance(x, dict) else 'No lesson'
)
df_pain['actual_outcome'] = df_pain['post_mortem'].apply(
    lambda x: x.get('actual_outcome', 'Unknown') if isinstance(x, dict) else 'Unknown'
)

display_cols = ['timestamp', 'symbol', 'root_cause', 'actual_outcome']
if 'price' in df_pain.columns:
    display_cols.insert(2, 'price')

pain_display = df_pain[display_cols].copy()
pain_display['timestamp'] = pd.to_datetime(pain_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')

st.dataframe(pain_display, use_container_width=True, height=300)

st.markdown("---")

# === SECTION 2: Root Cause Analysis ===
st.header("🎯 Why Did We Approve These Losers?")

root_cause_counts = df_pain['root_cause'].value_counts()

fig_causes = px.bar(
    x=root_cause_counts.index,
    y=root_cause_counts.values,
    labels={'x': 'Root Cause', 'y': 'Count'},
    title="Approval Reasons for Losing Trades",
    color=root_cause_counts.values,
    color_continuous_scale='Reds'
)

st.plotly_chart(fig_causes, use_container_width=True)

# Show most common failure mode
most_common = root_cause_counts.index[0] if len(root_cause_counts) > 0 else "Unknown"
st.error(f"💔 **Most Common Failure:** {most_common} ({root_cause_counts.iloc[0]} cases)")

st.markdown("---")

# === SECTION 3: Symbol Analysis ===
st.header("📊 Pain by Symbol")

symbol_pain = df_pain['symbol'].value_counts()

fig_symbol = px.bar(
    x=symbol_pain.index,
    y=symbol_pain.values,
    labels={'x': 'Symbol', 'y': 'Loss Count'},
    title="Which Symbols Cause the Most Pain?"
)

st.plotly_chart(fig_symbol, use_container_width=True)

st.caption("💡 **Insight**: Symbols with high loss counts may need tighter filters.")

st.markdown("---")

# === SECTION 4: Confidence Analysis ===
st.header("📉 Confidence vs Outcome")

# Extract LLM confidence if available
if 'llm_response' in df_pain.columns:
    df_pain['llm_confidence'] = df_pain['llm_response'].apply(
        lambda x: x.get('confidence', 0) if isinstance(x, dict) else 0
    )
    
    if df_pain['llm_confidence'].notna().any():
        fig_conf = px.histogram(
            df_pain,
            x='llm_confidence',
            nbins=20,
            title="LLM Confidence Distribution for Losing Trades",
            labels={'llm_confidence': 'LLM Confidence', 'count': 'Count'}
        )
        
        st.plotly_chart(fig_conf, use_container_width=True)
        
        avg_conf = df_pain['llm_confidence'].mean()
        st.warning(f"⚠️ Average LLM Confidence for losers: {avg_conf:.2f}")
        
        if avg_conf > 0.75:
            st.error("🚨 **CRITICAL:** LLM is overconfident in bad trades!")
            st.markdown("""
            **Suggested Fixes:**
            - 🔧 Add confidence calibration layer
            - 📊 Increase minimum confidence threshold
            - 🧠 Enhance critique agent to catch overconfidence
            - 🛡️ Add risk policy rules for high-confidence trades
            """)

st.markdown("---")

# === SECTION 5: Temporal Trends ===
st.header("📈 Pain Trends Over Time")

if 'timestamp' in df_pain.columns:
    df_pain['date'] = pd.to_datetime(df_pain['timestamp']).dt.date
    daily_pain = df_pain.groupby('date').size().reset_index(name='count')
    
    fig_trend = px.line(
        daily_pain,
        x='date',
        y='count',
        title="Losing Trades Per Day",
        labels={'date': 'Date', 'count': 'Loss Count'}
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)
    
    st.caption("💡 **Insight**: Spikes may correlate with regime changes or model degradation.")

st.markdown("---")

# === SECTION 6: Detailed Case Analysis ===
st.header("🔬 Case-by-Case Analysis")

selected_pain_idx = st.selectbox(
    "Select Case for Detailed Analysis:",
    range(len(df_pain)),
    format_func=lambda x: f"{df_pain.iloc[x]['timestamp'][:10]} | "
                          f"{df_pain.iloc[x]['symbol']} | "
                          f"{df_pain.iloc[x]['root_cause']}"
)

selected_pain = df_pain.iloc[selected_pain_idx]
selected_pm = selected_pain['post_mortem']

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Symbol", selected_pain['symbol'])
    st.metric("Price", f"${selected_pain.get('price', 0):.2f}")

with col2:
    st.metric("Root Cause", selected_pm.get('root_cause', 'Unknown'))
    st.metric("Actual Outcome", selected_pm.get('actual_outcome', 'Unknown'))

with col3:
    if 'llm_response' in selected_pain and isinstance(selected_pain['llm_response'], dict):
        llm_conf = selected_pain['llm_response'].get('confidence', 0)
        st.metric("LLM Confidence", f"{llm_conf:.2f}")
    
    adjusted_conf = selected_pm.get('adjusted_confidence', 0)
    st.metric("Adjusted Confidence", f"{adjusted_conf:.2f}")

st.text_area("Lesson Learned:", selected_pm.get('lesson_learned', 'No lesson recorded'), height=150)

# Show LLM reasoning if available
if 'llm_response' in selected_pain and selected_pain['llm_response']:
    with st.expander("💬 LLM Reasoning (Why we approved this loser)"):
        llm_resp = selected_pain['llm_response']
        if isinstance(llm_resp, dict):
            reasoning = llm_resp.get('reasoning', 'No reasoning recorded')
            st.text_area("LLM Reasoning:", reasoning, height=200)
            st.json(llm_resp)
        else:
            st.text(str(llm_resp))

st.markdown("---")

# === SECTION 7: Recommendations ===
st.header("🎯 Action Items")

pain_rate = len(df_pain) / len(df_with_pm) if len(df_with_pm) > 0 else 0

if pain_rate < 0.10:
    st.success(f"✅ Loss rate is acceptable ({pain_rate:.1%})")
    st.info("Continue monitoring. Some losses are expected in trading.")

elif pain_rate < 0.25:
    st.warning(f"⚠️ Moderate loss rate ({pain_rate:.1%})")
    st.markdown("""
    **Suggested Actions:**
    - 📊 Review most common root causes
    - 🔧 Adjust parameters for problematic symbols
    - 🧪 Test stricter filters in War Games
    """)

else:
    st.error(f"🚨 High loss rate ({pain_rate:.1%})!")
    st.markdown("""
    **IMMEDIATE ACTIONS REQUIRED:**
    1. 🛑 **Pause live trading** until fixed
    2. 🔍 **Analyze top 3 failure patterns**
    3. 🔧 **Update LLM prompt** to address common errors
    4. 🧪 **Re-run War Games** with stricter parameters
    5. 📊 **Monitor improvements** before resuming
    """)

st.markdown("---")
st.caption(f"📁 Data Source: `{MEMORY_FILE}`")
st.caption("🔄 Auto-refreshes every 30 seconds")

