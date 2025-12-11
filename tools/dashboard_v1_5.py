"""
FuggerBot v2.0 Metrics Dashboard.

Advanced metrics for multi-agent architecture with Level 2 Perception (News + Memory) 
and Level 4 Policy (Risk Veto) integration.
"""
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

# Config
st.set_page_config(page_title="FuggerBot v2.0 Metrics", layout="wide")
st.title("🚀 FuggerBot v2.0 - Multi-Layer TRM Architecture")

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

# Add refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


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
    
    # Extract post-mortem data
    postmortem_data = {}
    for trade in trades:
        if 'post_mortem' in trade and trade.get('post_mortem'):
            trade_id = trade.get('trade_id')
            pm = trade.get('post_mortem')
            if isinstance(pm, dict) and trade_id:
                postmortem_data[trade_id] = {
                    'outcome_category': pm.get('outcome_category'),
                    'root_cause': pm.get('root_cause'),
                    'lesson_learned': pm.get('lesson_learned'),
                }
    
    # Apply post-mortem data
    if postmortem_data:
        df['outcome_category'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('outcome_category'))
        df['root_cause'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('root_cause'))
        df['lesson_learned'] = df['trade_id'].map(lambda tid: postmortem_data.get(tid, {}).get('lesson_learned'))
    else:
        df['outcome_category'] = None
        df['root_cause'] = None
        df['lesson_learned'] = None
    
    # Extract adversarial metrics if available
    # Check if trades have proposer_confidence (from v1.5 adversarial engine)
    df['proposer_confidence'] = None
    df['final_confidence'] = None
    df['critique_flaws_count'] = None
    
    for trade in trades:
        trade_id = trade.get('trade_id')
        if trade_id and 'proposer_confidence' in trade:
            idx = df[df['trade_id'] == trade_id].index
            if len(idx) > 0:
                df.loc[idx[0], 'proposer_confidence'] = trade.get('proposer_confidence')
                df.loc[idx[0], 'final_confidence'] = trade.get('final_confidence', trade.get('confidence'))
                df.loc[idx[0], 'critique_flaws_count'] = trade.get('critique_flaws_count')
    
    # Convert to numeric
    df['proposer_confidence'] = pd.to_numeric(df['proposer_confidence'], errors='coerce')
    df['final_confidence'] = pd.to_numeric(df['final_confidence'], errors='coerce')
    df['critique_flaws_count'] = pd.to_numeric(df['critique_flaws_count'], errors='coerce')
    
    # Extract regime if available (prefer saved regime_id/regime_name, fallback to memory_summary)
    df['regime'] = None
    for trade in trades:
        trade_id = trade.get('trade_id')
        if trade_id:
            # First try saved regime fields (v1.5)
            regime = None
            if 'regime_id' in trade and trade.get('regime_id'):
                regime_id = str(trade.get('regime_id', '')).upper()
                # Extract regime type from ID (e.g., "INFLATIONARY_2022" -> "INFLATIONARY")
                if 'INFLATIONARY' in regime_id:
                    regime = 'INFLATIONARY'
                elif 'GOLDILOCKS' in regime_id:
                    regime = 'GOLDILOCKS'
                elif 'DEFLATIONARY' in regime_id:
                    regime = 'DEFLATIONARY'
                elif 'LIQUIDITY_CRISIS' in regime_id or 'CRISIS' in regime_id:
                    regime = 'LIQUIDITY_CRISIS'
                elif 'NEUTRAL' in regime_id:
                    regime = 'NEUTRAL'
            
            # Fallback to regime_name
            if not regime and 'regime_name' in trade and trade.get('regime_name'):
                regime_name = str(trade.get('regime_name', '')).upper()
                if 'INFLATIONARY' in regime_name:
                    regime = 'INFLATIONARY'
                elif 'GOLDILOCKS' in regime_name:
                    regime = 'GOLDILOCKS'
                elif 'DEFLATIONARY' in regime_name:
                    regime = 'DEFLATIONARY'
                elif 'LIQUIDITY' in regime_name or 'CRISIS' in regime_name:
                    regime = 'LIQUIDITY_CRISIS'
            
            # Last resort: parse memory_summary
            if not regime:
                memory_summary = trade.get('memory_summary', '')
                if 'INFLATIONARY' in memory_summary.upper():
                    regime = 'INFLATIONARY'
                elif 'GOLDILOCKS' in memory_summary.upper():
                    regime = 'GOLDILOCKS'
                elif 'DEFLATIONARY' in memory_summary.upper():
                    regime = 'DEFLATIONARY'
                elif 'LIQUIDITY_CRISIS' in memory_summary.upper():
                    regime = 'LIQUIDITY_CRISIS'
                else:
                    regime = 'NEUTRAL'  # Default fallback
            
            idx = df[df['trade_id'] == trade_id].index
            if len(idx) > 0:
                df.loc[idx[0], 'regime'] = regime
    
    return df


df = load_data(MEMORY_FILE)

if df.empty:
    st.warning(f"No data found in {MEMORY_FILE}. Run the bot to generate memory!")
    st.stop()

# --- METRIC 1: CRITIC EFFECTIVENESS ---
st.header("📊 Critic Effectiveness")

# Calculate: % of trades where Red Team lowered confidence
trades_with_critique = df[
    df['proposer_confidence'].notna() & 
    df['final_confidence'].notna()
].copy()

if not trades_with_critique.empty:
    # Calculate if confidence was lowered
    trades_with_critique['confidence_lowered'] = (
        trades_with_critique['final_confidence'] < trades_with_critique['proposer_confidence']
    )
    
    critic_effectiveness = (
        trades_with_critique['confidence_lowered'].sum() / len(trades_with_critique)
        if len(trades_with_critique) > 0 else 0.0
    )
    
    avg_confidence_delta = (
        (trades_with_critique['proposer_confidence'] - trades_with_critique['final_confidence']).mean()
        if len(trades_with_critique) > 0 else 0.0
    )
    
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Critic Effectiveness",
        f"{critic_effectiveness:.1%}",
        help="Percentage of trades where Red Team critique lowered confidence"
    )
    col2.metric(
        "Avg Confidence Reduction",
        f"{avg_confidence_delta:.3f}",
        help="Average reduction in confidence after critique"
    )
    col3.metric(
        "Trades with Critique",
        len(trades_with_critique),
        help="Total trades that went through adversarial critique"
    )
    
    # Visualization: Proposer vs Final Confidence
    if len(trades_with_critique) > 0:
        fig_critic = px.scatter(
            trades_with_critique,
            x='proposer_confidence',
            y='final_confidence',
            color='confidence_lowered',
            hover_data=['symbol', 'critique_flaws_count'],
            title="Proposer Confidence vs Final Confidence (After Critique)",
            labels={
                'proposer_confidence': 'Proposer Confidence',
                'final_confidence': 'Final Confidence',
                'confidence_lowered': 'Confidence Lowered'
            }
        )
        # Add diagonal line (y=x)
        fig_critic.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode='lines',
                name='No Change',
                line=dict(dash='dash', color='gray')
            )
        )
        st.plotly_chart(fig_critic, use_container_width=True)
else:
    st.info("💡 No adversarial critique data available yet. Trades need to go through v1.5 adversarial engine.")
    st.info("**To generate data:** Restart the bot (`run_bot.py`) - new trades will automatically use the adversarial critique loop.")

# --- METRIC 2: REGIME DELTA ---
st.header("🌍 Regime Delta Analysis")

# Calculate Hit Rate by Regime
trades_with_regime = df[df['regime'].notna() & df['pnl'].notna()].copy()

if not trades_with_regime.empty:
    # Calculate hit rate per regime
    regime_metrics = []
    for regime in trades_with_regime['regime'].unique():
        regime_trades = trades_with_regime[trades_with_regime['regime'] == regime]
        approved = regime_trades[regime_trades['decision'] == 'APPROVE']
        if not approved.empty:
            hit_rate = (approved['pnl'] > 0).sum() / len(approved)
            avg_pnl = approved['pnl'].mean()
            regime_metrics.append({
                'regime': regime,
                'hit_rate': hit_rate,
                'avg_pnl': avg_pnl,
                'total_trades': len(approved)
            })
    
    if regime_metrics:
        regime_df = pd.DataFrame(regime_metrics)
        
        # Compare INFLATIONARY vs GOLDILOCKS
        inflationary = regime_df[regime_df['regime'] == 'INFLATIONARY']
        goldilocks = regime_df[regime_df['regime'] == 'GOLDILOCKS']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not inflationary.empty:
                st.metric(
                    "INFLATIONARY Hit Rate",
                    f"{inflationary['hit_rate'].iloc[0]:.1%}",
                    f"{inflationary['total_trades'].iloc[0]} trades"
                )
            else:
                st.metric("INFLATIONARY Hit Rate", "N/A")
        
        with col2:
            if not goldilocks.empty:
                st.metric(
                    "GOLDILOCKS Hit Rate",
                    f"{goldilocks['hit_rate'].iloc[0]:.1%}",
                    f"{goldilocks['total_trades'].iloc[0]} trades"
                )
            else:
                st.metric("GOLDILOCKS Hit Rate", "N/A")
        
        # Calculate delta
        if not inflationary.empty and not goldilocks.empty:
            delta = goldilocks['hit_rate'].iloc[0] - inflationary['hit_rate'].iloc[0]
            st.metric(
                "Regime Delta (GOLDILOCKS - INFLATIONARY)",
                f"{delta:+.1%}",
                help="Positive = better performance in GOLDILOCKS regime"
            )
        
        # Bar chart of hit rates by regime
        fig_regime = px.bar(
            regime_df,
            x='regime',
            y='hit_rate',
            color='regime',
            title="Hit Rate by Market Regime",
            labels={'hit_rate': 'Hit Rate', 'regime': 'Regime'},
            text='hit_rate'
        )
        fig_regime.update_traces(texttemplate='%{text:.1%}', textposition='outside')
        st.plotly_chart(fig_regime, use_container_width=True)
        
        # Table of regime metrics
        st.dataframe(regime_df, use_container_width=True)
    else:
        st.info("No regime data available for approved trades.")
else:
    st.info("💡 No regime data available for approved trades.")
    st.info("**Note:** Regime detection requires trades to be processed with v1.5 orchestrator. Restart the bot to enable regime tracking.")

# --- METRIC 3: HALLUCINATION SELF-CORRECTION ---
st.header("🔍 Hallucination Self-Correction")

# Count MODEL_HALLUCINATION tags over time
trades_with_pm = df[df['outcome_category'].notna()].copy()

if not trades_with_pm.empty:
    # Filter for MODEL_HALLUCINATION
    hallucinations = trades_with_pm[trades_with_pm['outcome_category'] == 'MODEL_HALLUCINATION'].copy()
    
    if not hallucinations.empty and 'timestamp' in hallucinations.columns:
        hallucinations['timestamp'] = pd.to_datetime(hallucinations['timestamp'], errors='coerce')
        hallucinations = hallucinations.sort_values('timestamp')
        
        # Create time series
        hallucinations['date'] = hallucinations['timestamp'].dt.date
        daily_counts = hallucinations.groupby('date').size().reset_index(name='count')
        daily_counts['cumulative'] = daily_counts['count'].cumsum()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Total Hallucinations",
                len(hallucinations),
                help="Total trades tagged as MODEL_HALLUCINATION"
            )
        
        with col2:
            if len(trades_with_pm) > 0:
                hallucination_rate = len(hallucinations) / len(trades_with_pm)
                st.metric(
                    "Hallucination Rate",
                    f"{hallucination_rate:.1%}",
                    help="Percentage of reviewed trades that were hallucinations"
                )
        
        # Time series chart
        if len(daily_counts) > 0:
            fig_hallucination = go.Figure()
            
            # Daily count
            fig_hallucination.add_trace(
                go.Bar(
                    x=daily_counts['date'],
                    y=daily_counts['count'],
                    name='Daily Hallucinations',
                    marker_color='red'
                )
            )
            
            # Cumulative line
            fig_hallucination.add_trace(
                go.Scatter(
                    x=daily_counts['date'],
                    y=daily_counts['cumulative'],
                    mode='lines',
                    name='Cumulative',
                    line=dict(color='orange', width=2),
                    yaxis='y2'
                )
            )
            
            fig_hallucination.update_layout(
                title="Hallucination Detection Over Time",
                xaxis_title="Date",
                yaxis_title="Daily Count",
                yaxis2=dict(
                    title="Cumulative Count",
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_hallucination, use_container_width=True)
        
        # Show recent hallucinations
        if len(hallucinations) > 0:
            st.subheader("Recent Hallucinations")
            # Only include columns that exist
            available_cols = ['timestamp', 'symbol']
            if 'root_cause' in hallucinations.columns:
                available_cols.append('root_cause')
            if 'lesson_learned' in hallucinations.columns:
                available_cols.append('lesson_learned')
            recent = hallucinations[available_cols].tail(10)
            st.dataframe(recent, use_container_width=True)
    else:
        st.info("No timestamp data available for hallucinations.")
else:
    st.info("No post-mortem data available. Run the reviewer daemon to generate analysis.")

# --- SUMMARY STATS ---
st.header("🛡️ v2.0: TRM Policy Layer")

# Load raw trades to access trm_details
try:
    with open(MEMORY_FILE, 'r') as f:
        memory_data = json.load(f)
        trades_with_trm = [t for t in memory_data.get('trades', []) if t.get('trm_details')]
    
    if trades_with_trm:
        st.success(f"✅ Found {len(trades_with_trm)} trades with v2.0 TRM details")
        
        # Extract TRM metrics
        trm_vetoes = [t for t in trades_with_trm if t['trm_details'].get('policy_veto')]
        news_impacts = [t['trm_details']['news_impact'] for t in trades_with_trm if 'news_impact' in t['trm_details']]
        news_sentiments = [t['trm_details']['news_sentiment'] for t in trades_with_trm if 'news_sentiment' in t['trm_details']]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            veto_rate = len(trm_vetoes) / len(trades_with_trm) if trades_with_trm else 0
            st.metric("🚫 Policy Veto Rate", f"{veto_rate:.1%}")
            st.caption(f"{len(trm_vetoes)} trades vetoed by risk policy")
        
        with col2:
            if news_impacts:
                critical_news = sum(1 for n in news_impacts if n == 'CRITICAL')
                st.metric("🚨 Critical News Events", f"{critical_news}")
                st.caption(f"Out of {len(news_impacts)} analyzed")
        
        with col3:
            if news_sentiments:
                sentiment_counts = Counter(news_sentiments)
                dominant_sentiment = sentiment_counts.most_common(1)[0][0]
                st.metric("📰 Dominant Sentiment", dominant_sentiment)
                st.caption(f"{sentiment_counts[dominant_sentiment]}/{len(news_sentiments)} trades")
        
        # Show veto reasons
        if trm_vetoes:
            st.subheader("Recent Policy Vetoes")
            veto_df = pd.DataFrame([
                {
                    'Symbol': t['symbol'],
                    'Timestamp': t['timestamp'][:19],
                    'Veto Reason': t['trm_details']['policy_veto_reason'],
                    'News Impact': t['trm_details'].get('news_impact', 'N/A'),
                    'News Sentiment': t['trm_details'].get('news_sentiment', 'N/A')
                }
                for t in trm_vetoes[-10:]  # Last 10 vetoes
            ])
            st.dataframe(veto_df, use_container_width=True)
        
        # Waterfall visualization
        st.subheader("Confidence Waterfall (Last 10 Trades)")
        recent_trades = trades_with_trm[-10:]
        waterfall_data = []
        for t in recent_trades:
            steps = t['trm_details'].get('waterfall_steps', {})
            waterfall_data.append({
                'Symbol': t['symbol'],
                'Forecast': steps.get('forecast_confidence', 0),
                'Trust': steps.get('trust_score', 0),
                'LLM': steps.get('llm_confidence', 0),
                'Final': steps.get('final_confidence', 0)
            })
        
        if waterfall_data:
            waterfall_df = pd.DataFrame(waterfall_data)
            fig = go.Figure()
            for col in ['Forecast', 'Trust', 'LLM', 'Final']:
                fig.add_trace(go.Scatter(
                    x=waterfall_df['Symbol'],
                    y=waterfall_df[col],
                    mode='lines+markers',
                    name=col
                ))
            fig.update_layout(
                title="Confidence Waterfall: Forecast → Trust → LLM → Policy",
                yaxis_title="Confidence",
                xaxis_title="Symbol"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ No v2.0 TRM details found yet. Process a ticker with the updated orchestrator to see policy metrics.")
except Exception as e:
    st.error(f"Error loading TRM details: {e}")

st.header("📈 Summary Statistics")

col1, col2, col3, col4 = st.columns(4)

total_trades = len(df)
col1.metric("Total Trades", total_trades)

trades_with_critique_count = len(trades_with_critique) if not trades_with_critique.empty else 0
col2.metric("Trades with Critique", trades_with_critique_count)

trades_with_pm_count = len(trades_with_pm) if not trades_with_pm.empty else 0
col3.metric("Trades Reviewed", trades_with_pm_count)

unique_regimes = df['regime'].nunique() if 'regime' in df.columns else 0
col4.metric("Regimes Detected", unique_regimes)

