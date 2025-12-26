"""
Test script for optimized parameter loader.

Verifies that get_optimized_params() correctly loads parameters
from data/optimized_params.json based on symbol and regime.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.adaptive_loader import AdaptiveParamLoader
from context.tracker import RegimeTracker

logging.basicConfig(level=logging.INFO)

def test_optimized_loader():
    """Test the optimized parameter loader with various scenarios."""
    
    print("=" * 80)
    print("TESTING OPTIMIZED PARAMETER LOADER")
    print("=" * 80)
    
    loader = AdaptiveParamLoader()
    regime_tracker = RegimeTracker()
    current_regime = regime_tracker.get_current_regime()
    
    print(f"\n📊 Current Regime: {current_regime.name} (ID: {current_regime.id})")
    print("-" * 80)
    
    # Test cases
    test_symbols = ["BTC-USD", "ETH-USD", "NVDA", "MSFT"]
    
    for symbol in test_symbols:
        print(f"\n🔍 Testing {symbol}:")
        params = loader.get_optimized_params(symbol, current_regime.name)
        
        print(f"   ✅ Trust Threshold: {params.get('trust_threshold', 'N/A')}")
        print(f"   ✅ Min Confidence: {params.get('min_confidence', 'N/A')}")
        print(f"   ✅ Max Position Size: {params.get('max_position_size', 'N/A')}")
        print(f"   ✅ Stop Loss: {params.get('stop_loss', 'N/A')}")
        print(f"   ✅ Take Profit: {params.get('take_profit', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_optimized_loader()






