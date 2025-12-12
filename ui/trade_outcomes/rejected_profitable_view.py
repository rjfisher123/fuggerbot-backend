"""
Rejected Profitable View - "The FOMO Chart"

Shows trades the bot rejected that would have been profitable.
Critical for identifying overly conservative parameters.

Author: FuggerBot AI Team
Version: v2.7 - Trade Outcome Analysis
"""
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from pathlib import Path

# Config
st.set_page_config(page_title="FuggerBot FOMO Analysis", layout="wide")
st.title("😢 The FOMO Chart - Rejected Profitable Trades")
st.markdown("**Trades we killed that would have made money**")

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

# Filter to rejected trades with post_mortem
if 'post_mortem' not in df.columns:
    st.warning("No post-mortem data! Run reviewer daemon.")
    st.stop()

df_with_pm = df[df['post_mortem'].notna()].copy()

# Extract outcome category
df_with_pm['outcome_category'] = df_with_pm['post_mortem'].apply(
    lambda x: x.get('outcome_category', 'UNKNOWN') if isinstance(x, dict) else 'UNKNOWN'
)

# Filter to rejected trades that were actually profitable
# Outcome categories: CORRECT_REJECT, MISSED_OPPORTUNITY, MODEL_HALLUCINATION, SAVED_BY_REJECT
df_fomo = df_with_pm[
    (df_with_pm['decision'] == 'REJECT') & 
    (df_with_pm['outcome_category'] == 'MISSED_OPPORTUNITY')
].copy()

# Overview metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Rejected", (df['decision'] == 'REJECT').sum())
with col2:
    st.metric("Reviewed", len(df_with_pm))
with col3:
    fomo_count = len(df_fomo)
    st.metric("FOMO Cases", fomo_count, delta=None if fomo_count == 0 else "😢")
with col4:
    if len(df_with_pm) > 0:
        fomo_rate = fomo_count / len(df_with_pm)
        st.metric("FOMO Rate", f"{fomo_rate:.1%}")
    else:
        st.metric("FOMO Rate", "N/A")

st.markdown("---")

if df_fomo.empty:
    st.success("✅ No FOMO cases detected!")
    st.balloons()
    st.info("The bot's rejection logic appears sound. All rejected trades were indeed bad.")
    st.stop()

# === SECTION 1: FOMO Table ===
st.header(f"😢 {len(df_fomo)} Missed Opportunities")

# Extract useful columns
df_fomo['root_cause'] = df_fomo['post_mortem'].apply(
    lambda x: x.get('root_cause', 'Unknown') if isinstance(x, dict) else 'Unknown'
)
df_fomo['lesson_learned'] = df_fomo['post_mortem'].apply(
    lambda x: x.get('lesson_learned', 'No lesson') if isinstance(x, dict) else 'No lesson'
)
df_fomo['actual_outcome'] = df_fomo['post_mortem'].apply(
    lambda x: x.get('actual_outcome', 'Unknown') if isinstance(x, dict) else 'Unknown'
)

display_cols = ['timestamp', 'symbol', 'root_cause', 'actual_outcome']
if 'price' in df_fomo.columns:
    display_cols.insert(2, 'price')

fomo_display = df_fomo[display_cols].copy()
fomo_display['timestamp'] = pd.to_datetime(fomo_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')

st.dataframe(fomo_display, use_container_width=True, height=300)

st.markdown("---")

# === SECTION 2: Root Cause Analysis ===
st.header("🎯 Why Did We Reject These Winners?")

root_cause_counts = df_fomo['root_cause'].value_counts()

fig_causes = px.bar(
    x=root_cause_counts.index,
    y=root_cause_counts.values,
    labels={'x': 'Root Cause', 'y': 'Count'},
    title="Rejection Reasons for Profitable Trades"
)

st.plotly_chart(fig_causes, use_container_width=True)

# Show most common cause
most_common = root_cause_counts.index[0] if len(root_cause_counts) > 0 else "Unknown"
st.info(f"💡 **Most Common:** {most_common} ({root_cause_counts.iloc[0]} cases)")

st.markdown("---")

# === SECTION 3: Lessons Learned ===
st.header("📚 Lessons Learned")

st.subheader("Top Insights:")

lessons = df_fomo['lesson_learned'].value_counts()

for i, (lesson, count) in enumerate(lessons.head(5).items(), 1):
    st.markdown(f"**{i}.** {lesson} _({count} cases)_")

st.markdown("---")

# === SECTION 4: Estimated Lost PnL ===
st.header("💸 Estimated Lost Profit")

st.caption("⚠️ This is a rough estimate based on post-mortem analysis")

# Try to extract estimated PnL if available
if 'estimated_pnl' in df_fomo.columns or any('pnl' in str(pm).lower() for pm in df_fomo['post_mortem']):
    st.info("PnL estimation available in some cases")
else:
    st.warning("Detailed PnL estimation not yet implemented")

# Symbol breakdown
fomo_by_symbol = df_fomo['symbol'].value_counts()

fig_symbol = px.bar(
    x=fomo_by_symbol.index,
    y=fomo_by_symbol.values,
    labels={'x': 'Symbol', 'y': 'Missed Opportunities'},
    title="FOMO Cases by Symbol"
)

st.plotly_chart(fig_symbol, use_container_width=True)

st.markdown("---")

# === SECTION 5: Recommendations ===
st.header("💡 Recommendations to Reduce FOMO")

st.subheader("Based on root cause analysis:")

if 'trust' in most_common.lower() or 'Trust' in most_common:
    st.warning("🎯 **Lower Trust Threshold**")
    st.code("# Current params likely have trust_threshold too high\n# Try reducing by 0.05", language="python")

if 'confidence' in most_common.lower():
    st.warning("🎯 **Lower Min Confidence**")
    st.code("# Current params likely have min_confidence too high\n# Try reducing by 0.05", language="python")

if 'news' in most_common.lower():
    st.warning("🎯 **Reduce News Impact Weight**")
    st.code("# News may be too pessimistic\n# Consider ignoring low-impact news", language="python")

if fomo_rate > 0.30:
    st.error(f"🚨 **CRITICAL:** {fomo_rate:.0%} of reviewed trades are FOMO cases!")
    st.markdown("""
    **Immediate Actions:**
    1. 🔍 Enable Discovery Mode in adaptive_loader
    2. 📉 Lower trust_threshold and min_confidence by 0.10
    3. 🧪 Re-run War Games with looser parameters
    4. 📊 Compare results with current strategy
    """)

st.markdown("---")

# === SECTION 6: Case Study ===
with st.expander("📖 Case Study: Most Expensive Miss"):
    if not df_fomo.empty:
        # Show first case as example
        case = df_fomo.iloc[0]
        case_pm = case['post_mortem']
        
        st.markdown(f"**Symbol:** {case['symbol']}")
        st.markdown(f"**Date:** {case['timestamp'][:10]}")
        st.markdown(f"**Price:** ${case.get('price', 0):.2f}")
        st.markdown(f"**Root Cause:** {case_pm.get('root_cause', 'Unknown')}")
        st.markdown(f"**Actual Outcome:** {case_pm.get('actual_outcome', 'Unknown')}")
        st.markdown(f"**Lesson:** {case_pm.get('lesson_learned', 'No lesson')}")
        
        if 'llm_response' in case and case['llm_response']:
            st.json(case['llm_response'])

st.markdown("---")
st.caption(f"📁 Data Source: `{MEMORY_FILE}`")
st.caption("🔄 Auto-refreshes every 30 seconds")

