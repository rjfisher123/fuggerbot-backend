"""
Global Data Lake Ingestion Script for FuggerBot Alpha v2.0.

Extracts maximum historical data from Yahoo Finance across multiple asset classes
(Indices, Commodities, Bonds, Currencies) and loads into DuckDB for fast querying.

Architecture: yfinance API → Extract → Transform → Load (DuckDB)
Database: data/market_history.duckdb
Table: ohlcv_history (symbol, date, OHLCV data, asset_class)
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd
import duckdb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FuggerBot.DataLake")


# =============================================================================
# GLOBAL UNIVERSE CONFIGURATION
# =============================================================================

GLOBAL_UNIVERSE: Dict[str, List[str]] = {
    "INDICES": [
        "^GSPC",      # S&P 500
        "^IXIC",      # Nasdaq Composite
        "^N225",      # Nikkei 225
        "000001.SS",  # Shanghai Composite
        "^FTSE",      # FTSE 100
        "^DJI",       # Dow Jones Industrial Average
        "^RUT",       # Russell 2000
    ],
    "COMMODITIES": [
        "GC=F",       # Gold Futures
        "CL=F",       # Crude Oil WTI Futures
        "HG=F",       # Copper Futures
        "SI=F",       # Silver Futures
        "NG=F",       # Natural Gas Futures
    ],
    "BONDS": [
        "^TNX",       # 10-Year Treasury Yield
        "^IRX",       # 13-Week Treasury Bill
        "^TYX",       # 30-Year Treasury Yield
    ],
    "CURRENCIES": [
        "JPY=X",      # USD/JPY
        "CNY=X",      # USD/CNY
        "EURUSD=X",   # EUR/USD
        "GBPUSD=X",   # GBP/USD
        "AUDUSD=X",   # AUD/USD
    ],
    "CRYPTO": [
        "BTC-USD",    # Bitcoin
        "ETH-USD",    # Ethereum
    ]
}


# =============================================================================
# DATABASE SCHEMA & CONNECTION
# =============================================================================

DB_PATH = project_root / "data" / "market_history.duckdb"

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS ohlcv_history (
    date DATE NOT NULL,
    symbol VARCHAR NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    asset_class VARCHAR NOT NULL,
    PRIMARY KEY (symbol, date)
);
"""

INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_symbol_date ON ohlcv_history (symbol, date);
CREATE INDEX IF NOT EXISTS idx_asset_class ON ohlcv_history (asset_class);
CREATE INDEX IF NOT EXISTS idx_date ON ohlcv_history (date);
"""


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """
    Connect to DuckDB database and ensure schema exists.
    
    Returns:
        DuckDB connection
    """
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = duckdb.connect(str(DB_PATH))
    
    # Create schema if not exists
    conn.execute(SCHEMA_DDL)
    
    # Create indices for fast lookups
    conn.execute(INDEX_DDL)
    
    logger.info(f"✅ Connected to DuckDB at {DB_PATH}")
    
    return conn


# =============================================================================
# EXTRACTION & TRANSFORMATION
# =============================================================================

def fetch_max_history(symbol: str) -> Optional[pd.DataFrame]:
    """
    Fetch maximum available historical data for a symbol from Yahoo Finance.
    
    Args:
        symbol: Trading symbol (e.g., "^GSPC", "BTC-USD")
    
    Returns:
        DataFrame with OHLCV data, or None if fetch failed
    """
    try:
        logger.info(f"📊 Fetching data for {symbol}...")
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max")
        
        if df.empty:
            logger.warning(f"⚠️ No data returned for {symbol}")
            return None
        
        # Reset index to make Date a column
        df = df.reset_index()
        
        # Rename columns to lowercase for consistency
        df.columns = df.columns.str.lower()
        
        # Handle different date column names
        if 'date' not in df.columns:
            # yfinance sometimes uses 'Date' or index
            if 'Date' in df.columns:
                df.rename(columns={'Date': 'date'}, inplace=True)
            else:
                logger.error(f"❌ Could not find date column for {symbol}")
                return None
        
        # Clean data: drop rows with NaN in critical columns
        df = df.dropna(subset=['open', 'close'])
        
        # Cast types explicitly
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].fillna(0).astype(int)
        
        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        logger.info(f"✅ Fetched {len(df)} rows for {symbol} (from {df['date'].min()} to {df['date'].max()})")
        
        return df
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch data for {symbol}: {e}", exc_info=True)
        return None


def clean_and_transform(df: pd.DataFrame, symbol: str, asset_class: str) -> pd.DataFrame:
    """
    Clean and transform raw OHLCV data.
    
    Args:
        df: Raw DataFrame from yfinance
        symbol: Trading symbol
        asset_class: Asset class (e.g., "INDICES", "CRYPTO")
    
    Returns:
        Cleaned DataFrame ready for database insertion
    """
    # Add metadata columns
    df['symbol'] = symbol
    df['asset_class'] = asset_class
    
    # Select only required columns in correct order
    columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'asset_class']
    df = df[columns]
    
    # Remove duplicates (keep most recent)
    df = df.drop_duplicates(subset=['symbol', 'date'], keep='last')
    
    # Sort by date
    df = df.sort_values('date')
    
    return df


# =============================================================================
# LOADING (UPSERT TO DUCKDB)
# =============================================================================

def upsert_to_db(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame, symbol: str) -> int:
    """
    Upsert data to DuckDB using delete-then-insert strategy.
    
    Args:
        conn: DuckDB connection
        df: Cleaned DataFrame
        symbol: Trading symbol
    
    Returns:
        Number of rows inserted
    """
    try:
        # Step 1: Delete existing data for this symbol (clear cache)
        conn.execute("DELETE FROM ohlcv_history WHERE symbol = ?", [symbol])
        logger.debug(f"Cleared existing data for {symbol}")
        
        # Step 2: Insert fresh data
        conn.register('df_temp', df)
        conn.execute("""
            INSERT INTO ohlcv_history 
            SELECT * FROM df_temp
        """)
        conn.unregister('df_temp')
        
        rows_inserted = len(df)
        logger.info(f"✅ Inserted {rows_inserted} rows for {symbol}")
        
        return rows_inserted
    
    except Exception as e:
        logger.error(f"❌ Failed to upsert data for {symbol}: {e}", exc_info=True)
        return 0


# =============================================================================
# MAIN INGESTION LOGIC
# =============================================================================

def ingest_symbol(conn: duckdb.DuckDBPyConnection, symbol: str, asset_class: str) -> int:
    """
    Complete ETL pipeline for a single symbol.
    
    Args:
        conn: DuckDB connection
        symbol: Trading symbol
        asset_class: Asset class
    
    Returns:
        Number of rows successfully ingested
    """
    # Extract
    raw_df = fetch_max_history(symbol)
    if raw_df is None or raw_df.empty:
        return 0
    
    # Transform
    clean_df = clean_and_transform(raw_df, symbol, asset_class)
    
    # Load
    rows_inserted = upsert_to_db(conn, clean_df, symbol)
    
    return rows_inserted


def ingest_all_assets(conn: duckdb.DuckDBPyConnection) -> Dict[str, int]:
    """
    Ingest all assets from GLOBAL_UNIVERSE.
    
    Args:
        conn: DuckDB connection
    
    Returns:
        Dictionary with statistics per asset class
    """
    stats: Dict[str, int] = {}
    total_rows = 0
    total_symbols = 0
    failed_symbols = []
    
    logger.info("=" * 80)
    logger.info("🚀 STARTING GLOBAL DATA LAKE INGESTION")
    logger.info("=" * 80)
    
    for asset_class, symbols in GLOBAL_UNIVERSE.items():
        logger.info(f"\n📂 Processing {asset_class} ({len(symbols)} symbols)...")
        class_rows = 0
        
        for symbol in symbols:
            try:
                rows = ingest_symbol(conn, symbol, asset_class)
                class_rows += rows
                total_symbols += 1
                
                if rows == 0:
                    failed_symbols.append(symbol)
                
            except Exception as e:
                logger.error(f"❌ Unexpected error for {symbol}: {e}", exc_info=True)
                failed_symbols.append(symbol)
        
        stats[asset_class] = class_rows
        total_rows += class_rows
        logger.info(f"✅ {asset_class}: {class_rows:,} rows ingested")
    
    # Generate final report
    logger.info("\n" + "=" * 80)
    logger.info("📊 INGESTION COMPLETE - SUMMARY REPORT")
    logger.info("=" * 80)
    logger.info(f"Total Symbols Processed: {total_symbols}")
    logger.info(f"Total Rows Ingested: {total_rows:,}")
    logger.info(f"\nBreakdown by Asset Class:")
    for asset_class, rows in stats.items():
        percentage = (rows / total_rows * 100) if total_rows > 0 else 0
        logger.info(f"  - {asset_class:12s}: {rows:8,} rows ({percentage:5.1f}%)")
    
    if failed_symbols:
        logger.warning(f"\n⚠️ Failed Symbols ({len(failed_symbols)}): {', '.join(failed_symbols)}")
    
    # Database statistics
    result = conn.execute("SELECT COUNT(*) as total_rows FROM ohlcv_history").fetchone()
    db_total = result[0] if result else 0
    logger.info(f"\n📦 Database Total Rows: {db_total:,}")
    
    result = conn.execute("SELECT COUNT(DISTINCT symbol) as unique_symbols FROM ohlcv_history").fetchone()
    db_symbols = result[0] if result else 0
    logger.info(f"📦 Unique Symbols in DB: {db_symbols}")
    
    logger.info("=" * 80)
    
    return stats


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    try:
        # Connect to database
        conn = get_db_connection()
        
        # Run ingestion
        stats = ingest_all_assets(conn)
        
        # Close connection
        conn.close()
        logger.info("✅ Database connection closed")
        
        # Return success
        return 0
    
    except Exception as e:
        logger.error(f"❌ Fatal error during ingestion: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

