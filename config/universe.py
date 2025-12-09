"""
Asset Universe Configuration for FuggerBot.

Defines asset classes for broad market testing across multiple asset types.
"""
from typing import List

# Core cryptocurrency assets
CRYPTO_CORE: List[str] = [
    'BTC-USD',   # Bitcoin
    'ETH-USD',   # Ethereum
    'SOL-USD',   # Solana
    'XRP-USD',   # Ripple
    'DOGE-USD'   # Dogecoin
]

# Technology giants and major tech stocks
TECH_GIANTS: List[str] = [
    'NVDA',   # NVIDIA
    'MSFT',   # Microsoft
    'AAPL',   # Apple
    'GOOGL',  # Google (Alphabet)
    'META',   # Meta (Facebook)
    'TSLA',   # Tesla
    'AMD'     # Advanced Micro Devices
]

# Macro ETFs for broad market exposure
MACRO_ETF: List[str] = [
    'SPY',   # S&P 500 ETF
    'QQQ',   # Nasdaq 100 ETF
    'IWM',   # Russell 2000 ETF
    'TLT',   # 20+ Year Treasury Bond ETF
    'GLD'    # Gold ETF
]

# Major forex pairs
FOREX_MAJORS: List[str] = [
    'EURUSD=X',  # Euro/US Dollar
    'JPY=X',     # US Dollar/Japanese Yen
    'GBPUSD=X'   # British Pound/US Dollar
]

# Full test suite combining all asset classes
FULL_TEST_SUITE: List[str] = (
    CRYPTO_CORE +
    TECH_GIANTS +
    MACRO_ETF +
    FOREX_MAJORS
)

# Asset class metadata
ASSET_CLASSES = {
    'CRYPTO_CORE': {
        'assets': CRYPTO_CORE,
        'description': 'Core cryptocurrency assets',
        'count': len(CRYPTO_CORE)
    },
    'TECH_GIANTS': {
        'assets': TECH_GIANTS,
        'description': 'Technology giants and major tech stocks',
        'count': len(TECH_GIANTS)
    },
    'MACRO_ETF': {
        'assets': MACRO_ETF,
        'description': 'Macro ETFs for broad market exposure',
        'count': len(MACRO_ETF)
    },
    'FOREX_MAJORS': {
        'assets': FOREX_MAJORS,
        'description': 'Major forex pairs',
        'count': len(FOREX_MAJORS)
    },
    'FULL_TEST_SUITE': {
        'assets': FULL_TEST_SUITE,
        'description': 'Full test suite combining all asset classes',
        'count': len(FULL_TEST_SUITE)
    }
}


def get_asset_class(class_name: str) -> List[str]:
    """
    Get asset list for a specific class.
    
    Args:
        class_name: Name of asset class (e.g., 'CRYPTO_CORE', 'TECH_GIANTS')
    
    Returns:
        List of asset symbols
    
    Raises:
        ValueError: If class_name is not found
    """
    class_name_upper = class_name.upper()
    
    if class_name_upper == 'CRYPTO_CORE':
        return CRYPTO_CORE
    elif class_name_upper == 'TECH_GIANTS':
        return TECH_GIANTS
    elif class_name_upper == 'MACRO_ETF':
        return MACRO_ETF
    elif class_name_upper == 'FOREX_MAJORS':
        return FOREX_MAJORS
    elif class_name_upper == 'FULL_TEST_SUITE':
        return FULL_TEST_SUITE
    else:
        raise ValueError(
            f"Unknown asset class: {class_name}. "
            f"Available classes: {list(ASSET_CLASSES.keys())}"
        )


def get_all_assets() -> List[str]:
    """
    Get all assets from all classes (deduplicated).
    
    Returns:
        List of all unique asset symbols
    """
    return list(set(FULL_TEST_SUITE))


def get_asset_count() -> dict:
    """
    Get count of assets in each class.
    
    Returns:
        Dictionary mapping class names to asset counts
    """
    return {
        name: info['count']
        for name, info in ASSET_CLASSES.items()
    }

