"""
Global Data Lake & TRM Context Dashboard.

A diagnostic tool to visualize market context, correlations, and volatility regimes
that the Memory Summarizer agent uses to inform the LLM.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional
import logging

from agents.trm.memory_summarizer import MemorySummarizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="FuggerBot - Macro Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize MemorySummarizer
@st.cache_resource
def get_memory_summarizer():
    """Initialize and cache the Memory Summarizer agent."""
    return MemorySummarizer()


def get_db_connection(db_path: Path = Path("data/market_history.duckdb")) -> Optional[duckdb.DuckDBPyConnection]:
    """Get DuckDB connection."""
    try:
        return duckdb.connect(str(db_path), read_only=True)
    except Exception as e:
        st.error(f"Failed to connect to DuckDB: {e}")
        return None


def fetch_ohlcv(conn: duckdb.DuckDBPyConnection, symbol: str, days: int = 90) -> pd.DataFrame:
    """
    Fetch OHLCV data for a symbol from DuckDB.
    
    Args:
        conn: DuckDB connection
        symbol: Trading symbol
        days: Number of days to fetch
        
    Returns:
        DataFrame with OHLCV data
    """
    query = f"""
        SELECT date, close, volume
        FROM ohlcv_history
        WHERE symbol = '{symbol}'
        ORDER BY date DESC
        LIMIT {days}
    """
    
    try:
        df = conn.execute(query).fetchdf()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


def calculate_rolling_correlation(
    df1: pd.DataFrame, 
    df2: pd.DataFrame, 
    window: int = 30
) -> pd.Series:
    """
    Calculate rolling correlation between two price series.
    
    Args:
        df1: DataFrame with 'date' and 'close' columns
        df2: DataFrame with 'date' and 'close' columns
        window: Rolling window size (days)
        
    Returns:
        Series of rolling correlations
    """
    # Merge on date
    merged = pd.merge(df1, df2, on='date', suffixes=('_1', '_2'))
    
    # Calculate returns
    merged['return_1'] = merged['close_1'].pct_change()
    merged['return_2'] = merged['close_2'].pct_change()
    
    # Calculate rolling correlation
    rolling_corr = merged['return_1'].rolling(window=window).corr(merged['return_2'])
    
    return pd.DataFrame({
        'date': merged['date'],
        'correlation': rolling_corr
    })


def calculate_volatility(df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """
    Calculate rolling volatility.
    
    Args:
        df: DataFrame with 'date' and 'close' columns
        window: Rolling window size (days)
        
    Returns:
        DataFrame with volatility metrics
    """
    df = df.copy()
    df['return'] = df['close'].pct_change()
    df['volatility'] = df['return'].rolling(window=window).std()
    df['vol_mean'] = df['volatility'].mean()
    df['vol_1_5x'] = df['vol_mean'] * 1.5
    
    return df


# === MAIN APP ===

st.title("🌍 FuggerBot - Global Data Lake Diagnostics")
st.markdown("**Real-time view of the market context that the LLM receives from the Perception Layer**")

# Sidebar - Asset Selection
st.sidebar.title("🎯 Asset Selector")

# Get available symbols from DuckDB
conn = get_db_connection()
if conn is None:
    st.error("Cannot connect to Global Data Lake. Check if data/market_history.duckdb exists.")
    st.stop()

try:
    symbols_query = "SELECT DISTINCT symbol FROM ohlcv_history ORDER BY symbol"
    available_symbols = conn.execute(symbols_query).fetchdf()['symbol'].tolist()
except Exception as e:
    st.error(f"Failed to load symbols: {e}")
    available_symbols = ["BTC-USD"]

# Default symbol
default_symbol = "BTC-USD" if "BTC-USD" in available_symbols else available_symbols[0]
selected_symbol = st.sidebar.selectbox(
    "Select Symbol:",
    options=available_symbols,
    index=available_symbols.index(default_symbol) if default_symbol in available_symbols else 0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Data Lake Stats")

# Get row count
try:
    total_rows = conn.execute("SELECT COUNT(*) FROM ohlcv_history").fetchone()[0]
    st.sidebar.metric("Total Rows", f"{total_rows:,}")
except:
    st.sidebar.metric("Total Rows", "N/A")

# Get date range
try:
    date_range = conn.execute(
        "SELECT MIN(date) as min_date, MAX(date) as max_date FROM ohlcv_history"
    ).fetchdf()
    st.sidebar.metric("Date Range", f"{date_range['min_date'][0]} to {date_range['max_date'][0]}")
except:
    st.sidebar.metric("Date Range", "N/A")

st.sidebar.markdown("---")

# === SECTION 1: THE NARRATIVE VIEW ===

st.header("📝 Section 1: The Narrative View")
st.markdown("**This is the exact context string that the LLM reads during the Perception Layer.**")

memory_summarizer = get_memory_summarizer()

with st.spinner(f"Generating market context for {selected_symbol}..."):
    try:
        market_narrative = memory_summarizer.get_market_context(selected_symbol, days=30)
        
        st.code(market_narrative, language="text")
        
        # Parse key metrics from narrative for display
        col1, col2, col3 = st.columns(3)
        
        # Extract beta values (simple parsing)
        if "β=" in market_narrative:
            tech_beta = market_narrative.split("β=")[1].split(")")[0] if "Tech" in market_narrative else "N/A"
            col1.metric("β to Tech/Equities", tech_beta)
        
        if "volatility" in market_narrative.lower():
            vol_text = "Normal" if "Normal volatility" in market_narrative else "High"
            col2.metric("Volatility Regime", vol_text)
        
        if "trend:" in market_narrative.lower():
            trend = market_narrative.split("trend:")[1].split("\n")[0].strip() if "trend:" in market_narrative else "N/A"
            col3.metric("30-Day Trend", trend)
            
    except Exception as e:
        st.error(f"Failed to generate market narrative: {e}")
        st.exception(e)

st.markdown("---")

# === SECTION 2: CORRELATION LAB ===

st.header("📈 Section 2: Correlation Lab")
st.markdown("**How does the selected asset correlate with S&P 500 (Tech) and Gold over time?**")

# Fetch data for correlation analysis
with st.spinner("Fetching 90-day correlation data..."):
    symbol_df = fetch_ohlcv(conn, selected_symbol, days=90)
    sp500_df = fetch_ohlcv(conn, "^GSPC", days=90)
    gold_df = fetch_ohlcv(conn, "GC=F", days=90)
    
    if symbol_df.empty or sp500_df.empty or gold_df.empty:
        st.warning("Insufficient data for correlation analysis. Check if data exists for all symbols.")
    else:
        # Calculate rolling correlations
        corr_sp500 = calculate_rolling_correlation(symbol_df, sp500_df, window=30)
        corr_gold = calculate_rolling_correlation(symbol_df, gold_df, window=30)
        
        # Plot correlations
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=corr_sp500['date'],
            y=corr_sp500['correlation'],
            mode='lines',
            name='β to S&P 500 (Tech)',
            line=dict(color='#00D9FF', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=corr_gold['date'],
            y=corr_gold['correlation'],
            mode='lines',
            name='β to Gold',
            line=dict(color='#FFD700', width=2)
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title=f"Rolling 30-Day Correlation: {selected_symbol}",
            xaxis_title="Date",
            yaxis_title="Correlation (β)",
            yaxis_range=[-1, 1],
            template="plotly_dark",
            hovermode="x unified",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display current correlation values
        col1, col2 = st.columns(2)
        
        latest_sp500_corr = corr_sp500['correlation'].iloc[-1]
        latest_gold_corr = corr_gold['correlation'].iloc[-1]
        
        col1.metric(
            "Current β to S&P 500",
            f"{latest_sp500_corr:.2f}",
            delta=f"{latest_sp500_corr - corr_sp500['correlation'].iloc[-10]:.2f} (10d)" if len(corr_sp500) > 10 else None
        )
        
        col2.metric(
            "Current β to Gold",
            f"{latest_gold_corr:.2f}",
            delta=f"{latest_gold_corr - corr_gold['correlation'].iloc[-10]:.2f} (10d)" if len(corr_gold) > 10 else None
        )
        
        # Interpretation
        st.markdown("### 🧠 Interpretation")
        
        if abs(latest_sp500_corr) < 0.3:
            st.info(f"🔵 **Decoupled from Tech**: {selected_symbol} is moving independently of the S&P 500.")
        elif latest_sp500_corr > 0.6:
            st.success(f"🟢 **Risk-On Asset**: {selected_symbol} is strongly correlated with Tech/Equities.")
        elif latest_sp500_corr < -0.6:
            st.warning(f"🔴 **Inverse to Tech**: {selected_symbol} moves opposite to the S&P 500 (possible hedge).")
        
        if latest_gold_corr > 0.6:
            st.info(f"🟡 **Safe Haven Behavior**: {selected_symbol} correlates with Gold (inflation hedge).")

st.markdown("---")

# === SECTION 3: VOLATILITY REGIME ===

st.header("⚡ Section 3: Volatility Regime")
st.markdown("**Is the current volatility normal, or are we in a danger zone?**")

with st.spinner("Analyzing volatility regime..."):
    if symbol_df.empty:
        st.warning("Insufficient data for volatility analysis.")
    else:
        # Calculate volatility
        vol_df = calculate_volatility(symbol_df, window=30)
        
        # Create figure
        fig = go.Figure()
        
        # Add volatility line
        fig.add_trace(go.Scatter(
            x=vol_df['date'],
            y=vol_df['volatility'],
            mode='lines',
            name='30-Day Rolling Volatility',
            line=dict(color='#FF6B6B', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 107, 107, 0.2)'
        ))
        
        # Add average line
        fig.add_trace(go.Scatter(
            x=vol_df['date'],
            y=vol_df['vol_mean'],
            mode='lines',
            name='Historical Average',
            line=dict(color='#4ECDC4', width=2, dash='dash')
        ))
        
        # Add 1.5x danger zone
        fig.add_trace(go.Scatter(
            x=vol_df['date'],
            y=vol_df['vol_1_5x'],
            mode='lines',
            name='1.5x Avg (Danger Zone)',
            line=dict(color='#FFE66D', width=2, dash='dot')
        ))
        
        # Highlight danger zones
        danger_zones = vol_df[vol_df['volatility'] > vol_df['vol_1_5x']]
        if not danger_zones.empty:
            fig.add_trace(go.Scatter(
                x=danger_zones['date'],
                y=danger_zones['volatility'],
                mode='markers',
                name='Danger Zone',
                marker=dict(color='red', size=8, symbol='x')
            ))
        
        fig.update_layout(
            title=f"Volatility Regime: {selected_symbol}",
            xaxis_title="Date",
            yaxis_title="Volatility (Std Dev of Returns)",
            template="plotly_dark",
            hovermode="x unified",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        current_vol = vol_df['volatility'].iloc[-1]
        avg_vol = vol_df['vol_mean'].iloc[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
        danger_days = len(danger_zones)
        
        col1.metric("Current Volatility", f"{current_vol:.4f}")
        col2.metric("Historical Avg", f"{avg_vol:.4f}")
        col3.metric("Volatility Ratio", f"{vol_ratio:.2f}x", delta=f"{vol_ratio - 1:.2f}x vs avg")
        col4.metric("Danger Days (90d)", f"{danger_days}", delta=f"{danger_days / len(vol_df) * 100:.1f}% of days")
        
        # Interpretation
        st.markdown("### 🧠 Volatility Assessment")
        
        if vol_ratio < 0.8:
            st.success(f"🟢 **Low Volatility**: {selected_symbol} is quieter than usual. Good conditions for entry.")
        elif vol_ratio <= 1.2:
            st.info(f"🔵 **Normal Volatility**: {selected_symbol} is trading within historical norms.")
        elif vol_ratio <= 1.5:
            st.warning(f"🟡 **Elevated Volatility**: {selected_symbol} is more volatile than usual. Exercise caution.")
        else:
            st.error(f"🔴 **DANGER ZONE**: {selected_symbol} volatility is {vol_ratio:.1f}x historical average. High risk!")

st.markdown("---")

# === FOOTER ===

st.markdown("### 🛠️ Technical Details")

with st.expander("📊 Data Sources & Calculations"):
    st.markdown("""
    **Data Source**: `data/market_history.duckdb`
    
    **Correlation Calculation**:
    - Rolling 30-day correlation between daily returns
    - β > 0.6: Strong positive correlation (moves together)
    - β < -0.6: Strong negative correlation (inverse relationship)
    - |β| < 0.3: Decoupled (independent movement)
    
    **Volatility Calculation**:
    - Rolling 30-day standard deviation of daily returns
    - Volatility Ratio = Current Vol / Historical Avg
    - Danger Zone = 1.5x historical average
    
    **Market Context Generation**:
    - Generated by `MemorySummarizer.get_market_context()`
    - Uses last 30 days of data
    - Calculates β to S&P 500 and Gold
    - Analyzes volatility regime
    - Detects price trends
    """)

with st.expander("🔍 How to Use This Dashboard"):
    st.markdown("""
    1. **Select a symbol** from the sidebar
    2. **Read the narrative** in Section 1 - this is what the LLM sees
    3. **Analyze correlations** in Section 2 - understand market relationships
    4. **Check volatility** in Section 3 - assess risk conditions
    
    **Use Cases**:
    - Debug LLM decisions by seeing exact market context
    - Understand why certain trades were approved/rejected
    - Identify regime shifts before they impact performance
    - Validate Global Data Lake data quality
    """)

st.markdown("---")
st.caption("FuggerBot v2.0 - Global Data Lake Diagnostics | Powered by DuckDB + Streamlit")







