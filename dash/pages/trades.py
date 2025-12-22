"""
Diagnostic Dashboard - Trades View

Provides deep insight into trade performance, including rejected opportunities
and detailed debug metadata for "Forensic AI" analysis.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import json
import plotly.express as px
from datetime import datetime

# Page Config
st.set_page_config(page_title="Trade Diagnostics", page_icon="🕵️", layout="wide")

st.title("🕵️ Trade Diagnostics & Forensics")

@st.cache_data
def load_trm_memory():
    """Load TRM learner memory."""
    path = Path("data/trm_memory.jsonl")
    data = []
    if path.exists():
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    return pd.DataFrame(data)

@st.cache_data
def load_execution_history():
    """Load actual execution history (mock for now if DB not connected)."""
    # In reality, query DuckDB or TradeExecutionRepository
    # Placeholder
    return pd.DataFrame()

# Load Data
trm_df = load_trm_memory()

# Sidebar Filters
st.sidebar.header("Filters")
if not trm_df.empty:
    selected_regime = st.sidebar.selectbox("Regime", ["All"] + list(trm_df['regime'].unique()))
    selected_decision = st.sidebar.multiselect("Decision", trm_df['decision'].unique(), default=trm_df['decision'].unique())
    selected_outcome = st.sidebar.multiselect("Outcome", trm_df['outcome'].unique(), default=trm_df['outcome'].unique())

    # Apply Filters
    filtered_df = trm_df.copy()
    if selected_regime != "All":
        filtered_df = filtered_df[filtered_df['regime'] == selected_regime]
    
    filtered_df = filtered_df[filtered_df['decision'].isin(selected_decision)]
    filtered_df = filtered_df[filtered_df['outcome'].isin(selected_outcome)]

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Episodes", len(filtered_df))
    with col2:
        win_rate = len(filtered_df[filtered_df['outcome'] == 'PROFIT']) / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    with col3:
        avg_regret = filtered_df['regret'].mean() if 'regret' in filtered_df.columns else 0
        st.metric("Avg Regret", f"${avg_regret:.2f}")
    with col4:
        delusion_rate = len(filtered_df[filtered_df['meta'].apply(lambda x: x.get('delusion', False))])
        st.metric("Delusion Cases", delusion_rate)

    # Categories
    st.subheader("Analysis Categories")
    
    tab1, tab2, tab3, tab4 = st.tabs(["✅ Profitable & Approved", "❌ Approved but Loss", "🟡 Missed Opportunities", "🔍 Delusion Detected"])
    
    with tab1:
        st.write("Trades we took that made money.")
        good_trades = filtered_df[(filtered_df['decision'] == 'APPROVE') & (filtered_df['outcome'] == 'PROFIT')]
        st.dataframe(good_trades, use_container_width=True)
        
    with tab2:
        st.write("Trades we took that lost money (High Regret?).")
        bad_trades = filtered_df[(filtered_df['decision'] == 'APPROVE') & (filtered_df['outcome'] == 'LOSS')]
        st.dataframe(bad_trades.style.applymap(lambda x: 'background-color: #ffcdd2', subset=['pnl']), use_container_width=True)
        
    with tab3:
        st.write("Trades we rejected that would have profited.")
        missed = filtered_df[(filtered_df['decision'] == 'REJECT') & (filtered_df['regret'] > 0)]
        st.dataframe(missed, use_container_width=True)
        
    with tab4:
        st.write("Episodes marked as 'Delusion' (Simulated Hallucinations).")
        delusions = filtered_df[filtered_df['meta'].apply(lambda x: x.get('delusion', False))]
        st.dataframe(delusions, use_container_width=True)

    # Detailed View
    st.markdown("---")
    st.subheader("🔬 Micro-Analysis")
    
    if not filtered_df.empty:
        selected_idx = st.selectbox("Select Episode for Detail", filtered_df.index)
        episode = filtered_df.loc[selected_idx]
        
        c1, c2 = st.columns(2)
        with c1:
            st.json(episode.to_dict())
        with c2:
            st.markdown(f"**Confidence**: {episode['confidence']:.2f}")
            st.markdown(f"**Forecast**: {episode['forecast']:.2f}")
            st.markdown(f"**Regime**: {episode['regime']}")
            
            # Scatter Plot of Confidence vs PnL
            fig = px.scatter(
                filtered_df, 
                x="confidence", 
                y="pnl", 
                color="outcome", 
                hover_data=["regime", "decision"],
                title="Confidence vs PnL Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No TRM Memory data found. Run a simulation or wait for live trades.")
