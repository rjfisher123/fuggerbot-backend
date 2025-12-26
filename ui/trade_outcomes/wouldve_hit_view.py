"""
Would've Hit View - "What If?" Simulator

Interactive slider to simulate: "What if Trust Threshold was 0.60 instead of 0.65?"
Shows how many rejected trades would have been approved with different parameters.
Estimates potential PnL impact of parameter changes.

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
st.set_page_config(page_title="FuggerBot What-If Simulator", layout="wide")
st.title("🎚️ What-If Parameter Simulator")
st.markdown("**Simulate how parameter changes would affect trade decisions**")

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

# Extract trust scores and confidence from trades
if 'trust_evaluation' in df.columns:
    df['trust_score'] = df['trust_evaluation'].apply(
        lambda x: x.get('metrics', {}).get('overall_trust_score', 0) if isinstance(x, dict) else 0
    )
else:
    st.warning("Trust scores not available in trade data")
    st.stop()

if 'llm_response' in df.columns:
    df['llm_confidence'] = df['llm_response'].apply(
        lambda x: x.get('confidence', 0) if isinstance(x, dict) else 0
    )
else:
    df['llm_confidence'] = 0

# Overview metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Signals", len(df))
with col2:
    approved = (df['decision'] == 'APPROVE').sum()
    st.metric("Currently Approved", approved)
with col3:
    rejected = (df['decision'] == 'REJECT').sum()
    st.metric("Currently Rejected", rejected)
with col4:
    if approved > 0:
        st.metric("Approval Rate", f"{approved/len(df):.1%}")
    else:
        st.metric("Approval Rate", "0%")

st.markdown("---")

# === SECTION 1: Interactive Parameter Sliders ===
st.header("🎚️ Adjust Parameters")

col1, col2 = st.columns(2)

with col1:
    trust_threshold = st.slider(
        "Trust Threshold",
        min_value=0.30,
        max_value=0.90,
        value=0.65,
        step=0.05,
        help="Minimum trust score to consider a trade"
    )

with col2:
    min_confidence = st.slider(
        "Min LLM Confidence",
        min_value=0.40,
        max_value=0.95,
        value=0.75,
        step=0.05,
        help="Minimum LLM confidence to approve a trade"
    )

st.markdown("---")

# === SECTION 2: Simulation Results ===
st.header("📊 Simulation Results")

# Simulate what would have been approved with new params
df['would_approve'] = (
    (df['trust_score'] >= trust_threshold) &
    (df['llm_confidence'] >= min_confidence)
)

new_approved = df['would_approve'].sum()
current_approved = (df['decision'] == 'APPROVE').sum()
delta = new_approved - current_approved

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Current Approved", current_approved)

with col2:
    st.metric("Would Be Approved", new_approved, delta=f"{delta:+d}")

with col3:
    if new_approved > 0:
        st.metric("New Approval Rate", f"{new_approved/len(df):.1%}")
    else:
        st.metric("New Approval Rate", "0%")

# Show impact
if delta > 0:
    st.info(f"💡 **{delta} more trades** would be approved with these parameters")
elif delta < 0:
    st.warning(f"⚠️ **{abs(delta)} fewer trades** would be approved with these parameters")
else:
    st.success("✅ No change in trade count")

st.markdown("---")

# === SECTION 3: Flip Analysis ===
st.header("🔄 Decision Flips")

# Identify trades that would flip
df['flipped'] = df['would_approve'] != (df['decision'] == 'APPROVE')
df['flip_type'] = df.apply(
    lambda row: 
        'NEW_APPROVE' if row['flipped'] and row['would_approve'] else
        'NEW_REJECT' if row['flipped'] and not row['would_approve'] else
        'NO_CHANGE',
    axis=1
)

new_approvals = df[df['flip_type'] == 'NEW_APPROVE']
new_rejections = df[df['flip_type'] == 'NEW_REJECT']

col1, col2 = st.columns(2)

with col1:
    st.metric("Would Newly Approve", len(new_approvals), delta="📈")
    if not new_approvals.empty:
        st.dataframe(
            new_approvals[['timestamp', 'symbol', 'trust_score', 'llm_confidence']].head(5),
            use_container_width=True
        )

with col2:
    st.metric("Would Newly Reject", len(new_rejections), delta="📉")
    if not new_rejections.empty:
        st.dataframe(
            new_rejections[['timestamp', 'symbol', 'trust_score', 'llm_confidence']].head(5),
            use_container_width=True
        )

st.markdown("---")

# === SECTION 4: Score Distribution Scatter ===
st.header("📊 Trust vs Confidence Scatter")

# Create decision zones
df['current_decision_color'] = df['decision'].map({
    'APPROVE': 'green',
    'REJECT': 'red'
})

fig_scatter = px.scatter(
    df,
    x='trust_score',
    y='llm_confidence',
    color='decision',
    symbol='flip_type',
    hover_data=['symbol', 'timestamp'],
    title="Trust Score vs LLM Confidence",
    labels={
        'trust_score': 'Trust Score',
        'llm_confidence': 'LLM Confidence'
    },
    color_discrete_map={'APPROVE': 'green', 'REJECT': 'red'}
)

# Add threshold lines
fig_scatter.add_hline(
    y=min_confidence,
    line_dash="dash",
    line_color="blue",
    annotation_text=f"Min Confidence: {min_confidence}"
)

fig_scatter.add_vline(
    x=trust_threshold,
    line_dash="dash",
    line_color="orange",
    annotation_text=f"Trust Threshold: {trust_threshold}"
)

st.plotly_chart(fig_scatter, use_container_width=True)

st.caption(
    "💡 **Insight**: Trades in top-right quadrant (above both lines) would be approved. "
    "Circles = NEW decisions after parameter change."
)

st.markdown("---")

# === SECTION 5: Estimated PnL Impact ===
st.header("💰 Estimated PnL Impact")

st.caption("⚠️ This is speculative - actual results may vary")

# If we have post_mortem data with actual outcomes
if 'post_mortem' in df.columns:
    df_with_pm = df[df['post_mortem'].notna()].copy()
    
    if not df_with_pm.empty:
        # Extract outcome categories
        df_with_pm['outcome_category'] = df_with_pm['post_mortem'].apply(
            lambda x: x.get('outcome_category', 'UNKNOWN') if isinstance(x, dict) else 'UNKNOWN'
        )
        
        # Estimate impact for NEW approvals
        new_approvals_with_pm = df_with_pm[df_with_pm['flip_type'] == 'NEW_APPROVE']
        
        if not new_approvals_with_pm.empty:
            profitable = (new_approvals_with_pm['outcome_category'] == 'MISSED_OPPORTUNITY').sum()
            losing = (new_approvals_with_pm['outcome_category'].isin(['MODEL_HALLUCINATION', 'LOSS'])).sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Would-Be Winners", profitable, delta="💚")
            with col2:
                st.metric("Would-Be Losers", losing, delta="💔")
            with col3:
                if profitable + losing > 0:
                    win_rate = profitable / (profitable + losing)
                    st.metric("Estimated Win Rate", f"{win_rate:.1%}")
            
            if win_rate > 0.55:
                st.success(f"✅ **RECOMMENDATION:** These parameters may improve performance!")
            elif win_rate < 0.45:
                st.error(f"⚠️ **WARNING:** These parameters may reduce performance!")
            else:
                st.info("📊 Neutral impact. Further testing recommended.")

st.markdown("---")

# === SECTION 6: Recommendations ===
st.header("💡 Recommended Next Steps")

st.subheader("Based on simulation:")

if delta > 10:
    st.info(f"📈 **{delta} more trades** with new params")
    st.markdown("""
    **Test Approach:**
    1. 🧪 Run War Games with these parameters
    2. 📊 Check simulated performance
    3. ✅ If positive, deploy to optimized_params.json
    4. 🔄 Let adaptive loader pick them up
    """)

elif delta < -10:
    st.warning(f"📉 **{abs(delta)} fewer trades** with new params")
    st.markdown("""
    **Consider:**
    - May reduce risk but also reduce opportunities
    - Check if current params are too aggressive
    - Verify if fewer trades = better quality
    """)

else:
    st.success("✅ Minimal impact on trade count")
    st.info("Parameters are likely well-calibrated")

st.markdown("---")

# === SECTION 7: Export Simulation ===
with st.expander("📥 Export Simulation Results"):
    st.subheader("Export Candidates for Testing")
    
    if not new_approvals.empty:
        export_data = new_approvals[['timestamp', 'symbol', 'trust_score', 'llm_confidence']].copy()
        export_json = export_data.to_json(orient='records', indent=2)
        
        st.download_button(
            label="Download New Approvals (JSON)",
            data=export_json,
            file_name="simulated_new_approvals.json",
            mime="application/json"
        )

st.markdown("---")
st.caption(f"📁 Data Source: `{MEMORY_FILE}`")
st.caption("🔄 Auto-refreshes every 30 seconds")






