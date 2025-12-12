"""
Regime Parameter Viewer - FuggerBot Diagnostic Tool

Visualizes optimized_params.json to prove parameters exist and change across regimes.
Shows which strategies were selected by the optimizer for each Symbol+Regime combination.

Author: FuggerBot AI Team
Version: v2.7 - Diagnostic Tools
"""
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from pathlib import Path

# Config
st.set_page_config(page_title="FuggerBot Regime Params", layout="wide")
st.title("⚙️ Regime Parameter Viewer")
st.markdown("**Visualize optimized parameters across market regimes**")

# Load optimized parameters
PROJECT_ROOT = Path(__file__).parent.parent.parent
PARAMS_FILE = PROJECT_ROOT / "data" / "optimized_params.json"

@st.cache_data(ttl=60)
def load_optimized_params():
    """Load optimized parameters from JSON."""
    if not PARAMS_FILE.exists():
        return None
    
    try:
        with open(PARAMS_FILE, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error loading params: {e}")
        return None

params_data = load_optimized_params()

if params_data is None or len(params_data) == 0:
    st.warning("⚠️ No optimized parameters found!")
    st.info("Run the optimizer first:")
    st.code("python agents/trm/strategy_optimizer_agent.py", language="bash")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(params_data)

# Overview metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Configurations", len(df))
with col2:
    st.metric("Symbols Covered", df['symbol'].nunique())
with col3:
    st.metric("Regimes Covered", df['regime'].nunique())

st.markdown("---")

# === TASK C: PARAMETER DIVERSITY MONITOR ===
st.header("🏥 Configuration Health Check")
st.caption("Verifying that different assets use distinct strategies")

# Import adaptive loader to get current parameters
try:
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from config.adaptive_loader import AdaptiveParamLoader
    
    loader = AdaptiveParamLoader()
    
    # Get current regime (use first regime from data as proxy)
    current_regime = df['regime'].iloc[0] if len(df) > 0 else "Unknown"
    
    # Get params for BTC-USD and NVDA
    btc_params = loader.get_optimized_params("BTC-USD", current_regime)
    nvda_params = loader.get_optimized_params("NVDA", current_regime)
    
    # Compare parameters
    params_to_compare = ['trust_threshold', 'min_confidence', 'max_position_size', 'stop_loss', 'take_profit']
    
    differences = []
    for param in params_to_compare:
        btc_val = btc_params.get(param, 0)
        nvda_val = nvda_params.get(param, 0)
        if btc_val != nvda_val:
            differences.append(param)
    
    # Display health status
    if len(differences) >= 2:  # At least 2 params differ
        st.success(
            f"✅ **Adaptive Diversity Active:** BTC-USD and NVDA use distinct strategies "
            f"({len(differences)}/5 parameters differ)"
        )
    elif len(differences) == 0:
        st.error(
            "⚠️ **Diversity Warning:** BTC-USD and NVDA have IDENTICAL parameters! "
            "Possible fallback to defaults. Check optimizer output."
        )
    else:
        st.warning(
            f"⚙️ **Partial Diversity:** Only {len(differences)}/5 parameters differ. "
            "Consider re-running optimizer."
        )
    
    # Side-by-side comparison table
    st.subheader("📊 Parameter Comparison: BTC-USD vs NVDA")
    
    comparison_data = {
        'Parameter': params_to_compare,
        'BTC-USD': [btc_params.get(p, 0) for p in params_to_compare],
        'NVDA': [nvda_params.get(p, 0) for p in params_to_compare],
        'Difference': [abs(btc_params.get(p, 0) - nvda_params.get(p, 0)) for p in params_to_compare]
    }
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Highlight rows with differences
    def highlight_differences(row):
        if row['Difference'] > 0.01:  # Threshold for "different"
            return ['background-color: lightgreen'] * len(row)
        else:
            return ['background-color: lightyellow'] * len(row)
    
    styled_comparison = comparison_df.style.apply(highlight_differences, axis=1).format({
        'BTC-USD': '{:.3f}',
        'NVDA': '{:.3f}',
        'Difference': '{:.3f}'
    })
    
    st.dataframe(styled_comparison, use_container_width=True)
    
    st.caption("💡 **Green rows** = Parameters differ (good!), **Yellow rows** = Parameters identical (potential issue)")
    
except Exception as e:
    st.warning(f"Could not load adaptive loader: {e}")
    st.info("Skipping diversity check")

st.markdown("---")

# === SECTION 1: Parameter Heatmap ===
st.header("📊 Parameter Heatmap by Symbol + Regime")

# Extract parameters from best_params dict
df['trust_threshold'] = df['best_params'].apply(lambda x: x.get('trust_threshold', 0))
df['min_confidence'] = df['best_params'].apply(lambda x: x.get('min_confidence', 0))
df['max_position_size'] = df['best_params'].apply(lambda x: x.get('max_position_size', 0))
df['stop_loss'] = df['best_params'].apply(lambda x: x.get('stop_loss', 0))
df['take_profit'] = df['best_params'].apply(lambda x: x.get('take_profit', 0))

# Extract metrics
df['sharpe'] = df['metrics'].apply(lambda x: x.get('sharpe', 0))
df['return_pct'] = df['metrics'].apply(lambda x: x.get('return', 0))
df['drawdown'] = df['metrics'].apply(lambda x: x.get('drawdown', 0))
df['win_rate'] = df['metrics'].apply(lambda x: x.get('win_rate', 0))

# Select parameter to visualize
param_to_view = st.selectbox(
    "Select Parameter:",
    ["trust_threshold", "min_confidence", "max_position_size", "stop_loss", "take_profit"]
)

# Create pivot table for heatmap
pivot = df.pivot_table(
    values=param_to_view,
    index='symbol',
    columns='regime',
    aggfunc='first'
)

# Plot heatmap
fig_heatmap = px.imshow(
    pivot,
    labels=dict(x="Market Regime", y="Symbol", color=param_to_view),
    title=f"{param_to_view.replace('_', ' ').title()} Across Symbols and Regimes",
    color_continuous_scale='RdYlGn',
    aspect="auto"
)

st.plotly_chart(fig_heatmap, use_container_width=True)

st.caption(
    "💡 **Insight**: Warmer colors = higher values. "
    "Notice how parameters adapt to different market conditions."
)

st.markdown("---")

# === SECTION 2: Strategy Selection Table ===
st.header("🏆 Selected Strategies")

# Create display table
display_df = df[[
    'symbol', 
    'regime', 
    'best_strategy_name', 
    'score',
    'return_pct',
    'sharpe',
    'win_rate',
    'drawdown'
]].copy()

display_df.columns = [
    'Symbol', 
    'Regime', 
    'Strategy', 
    'Score',
    'Return %',
    'Sharpe',
    'Win Rate',
    'Max DD %'
]

# Style the dataframe
styled_df = display_df.style.format({
    'Score': '{:.1f}',
    'Return %': '{:+.1f}',
    'Sharpe': '{:.2f}',
    'Win Rate': '{:.1%}',
    'Max DD %': '{:.1f}'
}).background_gradient(subset=['Score'], cmap='RdYlGn')

st.dataframe(styled_df, use_container_width=True, height=400)

st.markdown("---")

# === SECTION 3: Parameter Distribution ===
st.header("📈 Parameter Distribution Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Trust Threshold Distribution")
    fig_trust = px.histogram(
        df,
        x='trust_threshold',
        nbins=20,
        title="Trust Threshold Frequency",
        labels={'trust_threshold': 'Trust Threshold', 'count': 'Frequency'}
    )
    st.plotly_chart(fig_trust, use_container_width=True)

with col2:
    st.subheader("Min Confidence Distribution")
    fig_conf = px.histogram(
        df,
        x='min_confidence',
        nbins=20,
        title="Min Confidence Frequency",
        labels={'min_confidence': 'Min Confidence', 'count': 'Frequency'}
    )
    st.plotly_chart(fig_conf, use_container_width=True)

st.caption("💡 **Insight**: Distribution shows parameter diversity across strategies.")

st.markdown("---")

# === SECTION 4: Regime Comparison ===
st.header("🌍 Regime-Specific Parameters")

selected_symbol = st.selectbox("Select Symbol:", df['symbol'].unique())

symbol_data = df[df['symbol'] == selected_symbol]

st.subheader(f"Parameters for {selected_symbol} Across Regimes")

# Create comparison table
comparison = symbol_data[[
    'regime',
    'trust_threshold',
    'min_confidence',
    'max_position_size',
    'return_pct',
    'score'
]].copy()

comparison.columns = ['Regime', 'Trust', 'Confidence', 'Position Size', 'Return %', 'Score']

st.dataframe(
    comparison.style.format({
        'Trust': '{:.2f}',
        'Confidence': '{:.2f}',
        'Position Size': '{:.1%}',
        'Return %': '{:+.1f}',
        'Score': '{:.1f}'
    }).background_gradient(subset=['Score'], cmap='RdYlGn'),
    use_container_width=True
)

# Bar chart comparison
fig_comparison = px.bar(
    symbol_data,
    x='regime',
    y=['trust_threshold', 'min_confidence'],
    barmode='group',
    title=f"{selected_symbol}: Trust vs Confidence by Regime",
    labels={'value': 'Threshold', 'regime': 'Market Regime'}
)

st.plotly_chart(fig_comparison, use_container_width=True)

st.caption(
    f"💡 **Insight**: Notice how {selected_symbol} requires different thresholds "
    "in different market conditions."
)

st.markdown("---")

# === SECTION 5: Raw JSON Explorer ===
with st.expander("🔍 Raw JSON Explorer"):
    selected_config = st.selectbox(
        "Select Configuration:",
        range(len(params_data)),
        format_func=lambda x: f"{params_data[x]['symbol']} - {params_data[x]['regime'][:40]}"
    )
    
    st.json(params_data[selected_config])

st.markdown("---")
st.caption(f"📁 Data Source: `{PARAMS_FILE}`")
st.caption(f"🔄 Auto-refreshes every 60 seconds")

