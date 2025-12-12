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

# === TASK B: ERROR TAXONOMY ===
# Extract outcome_category and error type from post_mortem dict
df_with_pm['outcome_category'] = df_with_pm['post_mortem'].apply(
    lambda x: x.get('outcome_category', 'UNKNOWN') if isinstance(x, dict) else 'UNKNOWN'
)

# Detect infrastructure failures from rationale
df_with_pm['error_type'] = 'NONE'
if 'llm_response' in df.columns:
    df_with_pm['error_type'] = df_with_pm['llm_response'].apply(
        lambda x: 'INFRASTRUCTURE' if isinstance(x, dict) and '[INFRASTRUCTURE_FAIL]' in str(x.get('rationale', ''))
        else 'COGNITIVE' if isinstance(x, dict) and '[LOGIC_FAIL]' in str(x.get('rationale', ''))
        else 'NONE'
    )

# Filter to failures
df_halluc_all = df_with_pm[df_with_pm['outcome_category'] == 'MODEL_HALLUCINATION'].copy()

# Split into infrastructure vs cognitive failures
df_infrastructure = df_halluc_all[df_halluc_all['error_type'] == 'INFRASTRUCTURE'].copy()
df_cognitive = df_halluc_all[df_halluc_all['error_type'] == 'COGNITIVE'].copy()

# Overview metrics (exclude infrastructure from hallucination rate)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Trades", len(df))
with col2:
    st.metric("Reviewed Trades", len(df_with_pm))
with col3:
    cognitive_count = len(df_cognitive)
    st.metric("Cognitive Failures", cognitive_count, help="True LLM hallucinations")
with col4:
    if len(df_with_pm) > 0:
        # Exclude infrastructure failures from hallucination rate
        true_halluc_rate = cognitive_count / len(df_with_pm)
        st.metric("True Hallucination Rate", f"{true_halluc_rate:.1%}", 
                 help="Excludes infrastructure failures")
    else:
        st.metric("True Hallucination Rate", "N/A")

# Show infrastructure failure count separately
if len(df_infrastructure) > 0:
    st.warning(f"⚠️ **{len(df_infrastructure)} Infrastructure Failures** detected (API errors, auth issues, timeouts)")
else:
    st.success("✅ No infrastructure failures detected")

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

# === SECTION 2: Failure Analysis (SPLIT INTO TABS) ===
if not df_halluc_all.empty:
    st.header("🔴 Failure Analysis")
    
    # Create tabs for different failure types
    tab1, tab2, tab3 = st.tabs([
        f"🧠 Cognitive Failures ({len(df_cognitive)})",
        f"🔧 Infrastructure Failures ({len(df_infrastructure)})",
        "📊 Combined Analysis"
    ])
    
    # === TAB 1: COGNITIVE FAILURES (True LLM Hallucinations) ===
    with tab1:
        if not df_cognitive.empty:
            st.subheader(f"True LLM Hallucinations ({len(df_cognitive)} cases)")
            st.caption("These are actual model failures, not infrastructure issues")
            
            # Extract root causes
            df_cognitive['root_cause'] = df_cognitive['post_mortem'].apply(
                lambda x: x.get('root_cause', 'Unknown') if isinstance(x, dict) else 'Unknown'
            )
            
            # Root cause distribution
            root_causes = df_cognitive['root_cause'].value_counts()
            
            fig_causes = px.bar(
                x=root_causes.index,
                y=root_causes.values,
                labels={'x': 'Root Cause', 'y': 'Count'},
                title="Cognitive Failure Patterns"
            )
            st.plotly_chart(fig_causes, use_container_width=True)
            
            # Table
            display_cols = ['timestamp', 'symbol', 'decision', 'root_cause']
            if 'price' in df_cognitive.columns:
                display_cols.append('price')
            
            cog_display = df_cognitive[display_cols].copy()
            cog_display['timestamp'] = pd.to_datetime(cog_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(cog_display, use_container_width=True, height=250)
        else:
            st.success("✅ No cognitive failures detected! LLM reasoning quality is strong.")
    
    # === TAB 2: INFRASTRUCTURE FAILURES ===
    with tab2:
        if not df_infrastructure.empty:
            st.subheader(f"Infrastructure Issues ({len(df_infrastructure)} cases)")
            st.caption("API errors, auth failures, timeouts - not model quality issues")
            
            # Extract error types from rationale
            if 'llm_response' in df_infrastructure.columns:
                df_infrastructure['error_detail'] = df_infrastructure['llm_response'].apply(
                    lambda x: str(x.get('rationale', 'Unknown'))[:100] if isinstance(x, dict) else 'Unknown'
                )
            
            # Table
            display_cols = ['timestamp', 'symbol']
            if 'error_detail' in df_infrastructure.columns:
                display_cols.append('error_detail')
            
            infra_display = df_infrastructure[display_cols].copy()
            infra_display['timestamp'] = pd.to_datetime(infra_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(infra_display, use_container_width=True, height=250)
            
            st.info("💡 **Action:** Check API keys, rate limits, and network connectivity")
        else:
            st.success("✅ No infrastructure failures! API and authentication working correctly.")
    
    # === TAB 3: COMBINED ANALYSIS ===
    with tab3:
        st.subheader("All Failures Combined")
        
        # Combined table
        df_halluc_all['root_cause'] = df_halluc_all['post_mortem'].apply(
            lambda x: x.get('root_cause', 'Unknown') if isinstance(x, dict) else 'Unknown'
        )
        
        display_cols = ['timestamp', 'symbol', 'error_type', 'root_cause']
        if 'price' in df_halluc_all.columns:
            display_cols.append('price')
        
        all_display = df_halluc_all[display_cols].copy()
        all_display['timestamp'] = pd.to_datetime(all_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(all_display, use_container_width=True, height=300)
    
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

