"""
Technical Analysis Indicators for FuggerBot v2.1.

Provides calculation functions for common technical indicators:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Volume Analysis
- Trend Analysis

Author: FuggerBot AI Team
Version: Phase 3 - Signal Quality Enhancement
"""
import pandas as pd
import numpy as np
from typing import Optional


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    RSI measures the magnitude of recent price changes to evaluate
    overbought or oversold conditions.
    
    Args:
        series: Price series (typically close prices)
        period: RSI period (default: 14)
        
    Returns:
        RSI values (0-100)
        
    Interpretation:
        RSI > 70: Overbought (potential reversal down)
        RSI < 30: Oversold (potential reversal up)
        RSI 40-60: Neutral range
    """
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    MACD shows the relationship between two moving averages of prices.
    
    Args:
        series: Price series (typically close prices)
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
        
    Returns:
        DataFrame with columns: macd_line, macd_signal, macd_hist
        
    Interpretation:
        macd_hist > 0: Bullish momentum
        macd_hist < 0: Bearish momentum
        macd_line crosses above signal: Buy signal
        macd_line crosses below signal: Sell signal
    """
    ema_fast = series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = series.ewm(span=slow_period, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal_period, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    
    return pd.DataFrame({
        'macd_line': macd_line,
        'macd_signal': macd_signal,
        'macd_hist': macd_hist
    })


def calculate_volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Volume Ratio (current volume vs average).
    
    Args:
        volume: Volume series
        period: Period for average calculation (default: 20)
        
    Returns:
        Volume ratio (1.0 = average, >1.0 = above average)
        
    Interpretation:
        volume_ratio > 1.5: High volume (strong conviction)
        volume_ratio > 1.0: Above average volume (confirmation)
        volume_ratio < 0.8: Low volume (weak signal)
    """
    avg_volume = volume.rolling(window=period, min_periods=period).mean()
    volume_ratio = volume / avg_volume
    
    return volume_ratio


def calculate_trend_sma(close: pd.Series, period: int = 50) -> pd.Series:
    """
    Calculate Trend indicator using Simple Moving Average.
    
    Args:
        close: Close price series
        period: SMA period (default: 50)
        
    Returns:
        Price / SMA ratio
        
    Interpretation:
        trend_sma > 1.0: Price above SMA (uptrend)
        trend_sma < 1.0: Price below SMA (downtrend)
        trend_sma > 1.05: Strong uptrend
        trend_sma < 0.95: Strong downtrend
    """
    sma = close.rolling(window=period, min_periods=period).mean()
    trend_sma = close / sma
    
    return trend_sma


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to a DataFrame.
    
    Expected DataFrame columns: date, open, high, low, close, volume
    
    Args:
        df: DataFrame with OHLCV data
        
    Returns:
        DataFrame with added indicator columns:
            - rsi_14: RSI(14)
            - macd_line: MACD line
            - macd_signal: MACD signal line
            - macd_hist: MACD histogram
            - volume_ratio: Current volume / 20-day avg
            - trend_sma: Price / 50-day SMA
            
    Usage:
        df = pd.DataFrame(...)  # OHLCV data
        df = add_indicators(df)
        
        # Filter for high-quality setups
        quality_setups = df[
            (df['rsi_14'] < 70) &
            (df['volume_ratio'] > 1.0) &
            (df['macd_hist'] > 0)
        ]
    """
    df = df.copy()
    
    # RSI
    df['rsi_14'] = calculate_rsi(df['close'], period=14)
    
    # MACD
    macd_df = calculate_macd(df['close'], fast_period=12, slow_period=26, signal_period=9)
    df['macd_line'] = macd_df['macd_line']
    df['macd_signal'] = macd_df['macd_signal']
    df['macd_hist'] = macd_df['macd_hist']
    
    # Volume Ratio
    df['volume_ratio'] = calculate_volume_ratio(df['volume'], period=20)
    
    # Trend SMA
    df['trend_sma'] = calculate_trend_sma(df['close'], period=50)
    
    return df


def is_quality_setup(
    rsi: float,
    volume_ratio: float,
    macd_hist: float,
    trend_sma: Optional[float] = None,
    rsi_max: float = 70.0,
    vol_min: float = 1.0,
    macd_positive: bool = True
) -> bool:
    """
    Check if a setup meets quality criteria.
    
    Args:
        rsi: RSI value
        volume_ratio: Volume ratio
        macd_hist: MACD histogram
        trend_sma: Optional trend SMA ratio
        rsi_max: Maximum RSI for quality (default: 70)
        vol_min: Minimum volume ratio (default: 1.0)
        macd_positive: Require positive MACD histogram (default: True)
        
    Returns:
        True if setup meets all quality criteria
        
    Quality Criteria:
        ✅ RSI < 70 (not overbought)
        ✅ Volume Ratio > 1.0 (volume confirmed)
        ✅ MACD Hist > 0 (momentum positive)
        ✅ Trend SMA > 1.0 (optional: price above 50-day SMA)
    """
    # Check for NaN values
    if pd.isna(rsi) or pd.isna(volume_ratio) or pd.isna(macd_hist):
        return False
    
    # RSI check (not overbought)
    if rsi >= rsi_max:
        return False
    
    # Volume check (confirmed)
    if volume_ratio < vol_min:
        return False
    
    # MACD check (positive momentum)
    if macd_positive and macd_hist <= 0:
        return False
    
    # Optional: Trend check
    if trend_sma is not None and not pd.isna(trend_sma):
        if trend_sma < 1.0:  # Price below SMA = downtrend
            return False
    
    return True


if __name__ == "__main__":
    # Example usage
    import yfinance as yf
    
    print("Testing Technical Analysis Library...")
    
    # Fetch sample data
    ticker = yf.Ticker("BTC-USD")
    df = ticker.history(period="6mo")
    
    # Normalize column names (yfinance uses capitalized)
    df.columns = df.columns.str.lower()
    df = df.reset_index()
    df['date'] = df['date'] if 'date' in df.columns else pd.to_datetime(df.index)
    
    # Add indicators
    df = add_indicators(df)
    
    # Display sample
    print("\n📊 Sample Data with Indicators:")
    print(df[['close', 'rsi_14', 'macd_hist', 'volume_ratio', 'trend_sma']].tail(10))
    
    # Check quality setups
    quality_count = df.apply(
        lambda row: is_quality_setup(
            rsi=row['rsi_14'],
            volume_ratio=row['volume_ratio'],
            macd_hist=row['macd_hist'],
            trend_sma=row['trend_sma']
        ),
        axis=1
    ).sum()
    
    print(f"\n✅ Quality Setups: {quality_count}/{len(df)} ({quality_count/len(df)*100:.1f}%)")
    print("\n✅ Technical Analysis Library Ready!")

