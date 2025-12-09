#!/usr/bin/env python3
"""
Demo script showing forecast integration with trading system.

This demonstrates the complete workflow:
1. Generate forecasts
2. Evaluate trust
3. Get trading recommendations
4. Integrate with trigger system
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import directly to avoid circular import issues
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.forecast_trader import ForecastTrader
from dash.utils.forecast_helper import get_historical_prices, get_price_statistics
from dash.utils.price_feed import get_price
import logging

# Import forecast service functions directly
from models.forecast_trader import ForecastTrader as FT
from dash.utils.forecast_helper import get_historical_prices as ghp

def get_forecast_recommendation(symbol: str, forecast_horizon: int = 30, period: str = "1y"):
    """Get forecast recommendation (inline version to avoid import issues)."""
    try:
        prices = ghp(symbol, period=period)
        if not prices or len(prices) < 20:
            return None
        trader = FT()
        result = trader.analyze_symbol(symbol=symbol, historical_prices=prices, forecast_horizon=forecast_horizon)
        if result.get("success") and result["trust_evaluation"].is_trusted:
            rec = result["recommendation"]
            return {
                "symbol": symbol,
                "action": rec["action"],
                "expected_return_pct": rec.get("expected_return_pct", 0),
                "risk_pct": rec.get("risk_pct", 0),
                "confidence": rec.get("confidence", "unknown"),
                "trust_score": rec.get("trust_score", 0),
                "reason": rec.get("reason", ""),
                "forecast_horizon": forecast_horizon
            }
        return None
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

def check_forecast_trigger(symbol: str, current_price: float, trigger_price: float, forecast_horizon: int = 30):
    """Check forecast trigger (inline version)."""
    result = {
        "symbol": symbol,
        "current_price": current_price,
        "trigger_price": trigger_price,
        "price_diff_pct": ((current_price - trigger_price) / trigger_price) * 100,
        "forecast_recommendation": None,
        "should_execute": False,
        "reason": ""
    }
    forecast_rec = get_forecast_recommendation(symbol, forecast_horizon)
    if forecast_rec:
        result["forecast_recommendation"] = forecast_rec
        price_trigger_hit = current_price < trigger_price
        if price_trigger_hit and forecast_rec["action"] == "BUY":
            result["should_execute"] = True
            result["reason"] = f"Price trigger hit and forecast recommends BUY"
        elif price_trigger_hit:
            result["should_execute"] = False
            result["reason"] = f"Price trigger hit but forecast recommends {forecast_rec['action']}"
        else:
            result["should_execute"] = False
            result["reason"] = "Price trigger not hit"
    else:
        price_trigger_hit = current_price < trigger_price
        result["should_execute"] = price_trigger_hit
        result["reason"] = "Forecast unavailable, using price trigger only" if price_trigger_hit else "Price trigger not hit"
    return result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_single_symbol_analysis():
    """Demo: Analyze a single symbol."""
    print("\n" + "="*80)
    print("DEMO 1: Single Symbol Analysis")
    print("="*80)
    
    symbol = "AAPL"
    print(f"\n📊 Analyzing {symbol}...")
    
    # Get historical data
    prices = get_historical_prices(symbol, period="1y")
    if not prices:
        print(f"❌ Failed to fetch data for {symbol}")
        return
    
    stats = get_price_statistics(prices)
    print(f"✅ Fetched {stats['count']} data points")
    print(f"   Current Price: ${stats['current']:.2f}")
    print(f"   Volatility: {stats['volatility_pct']:.2f}%")
    
    # Analyze with forecast trader
    trader = ForecastTrader()
    result = trader.analyze_symbol(
        symbol=symbol,
        historical_prices=prices,
        forecast_horizon=30
    )
    
    if not result.get("success"):
        print(f"❌ Analysis failed: {result.get('error')}")
        return
    
    # Display results
    trust_eval = result["trust_evaluation"]
    recommendation = result["recommendation"]
    
    print(f"\n📈 Trust Evaluation:")
    print(f"   Trust Score: {trust_eval.metrics.overall_trust_score:.3f}")
    print(f"   Confidence: {trust_eval.metrics.confidence_level.upper()}")
    print(f"   Status: {'✅ TRUSTED' if trust_eval.is_trusted else '❌ REJECTED'}")
    
    if trust_eval.is_trusted:
        print(f"\n💡 Trading Recommendation:")
        print(f"   Action: {recommendation['action']}")
        print(f"   Expected Return: {recommendation['expected_return_pct']:.2f}%")
        print(f"   Risk: {recommendation['risk_pct']:.2f}%")
        print(f"   Reason: {recommendation['reason']}")
    else:
        print(f"\n⚠️  Forecast rejected - no recommendation available")
        if trust_eval.metrics.rejection_reasons:
            print("   Reasons:")
            for reason in trust_eval.metrics.rejection_reasons:
                print(f"     - {reason}")


def demo_forecast_service():
    """Demo: Using the forecast service."""
    print("\n" + "="*80)
    print("DEMO 2: Forecast Service Integration")
    print("="*80)
    
    symbol = "MSFT"
    print(f"\n📊 Getting forecast recommendation for {symbol}...")
    
    # Use the service
    recommendation = get_forecast_recommendation(symbol, forecast_horizon=30)
    
    if recommendation:
        print(f"✅ Recommendation received:")
        print(f"   Action: {recommendation['action']}")
        print(f"   Expected Return: {recommendation['expected_return_pct']:.2f}%")
        print(f"   Confidence: {recommendation['confidence'].upper()}")
        print(f"   Trust Score: {recommendation['trust_score']:.3f}")
    else:
        print(f"❌ No trusted recommendation available for {symbol}")


def demo_trigger_validation():
    """Demo: Forecast-validated trigger checking."""
    print("\n" + "="*80)
    print("DEMO 3: Forecast-Validated Trigger")
    print("="*80)
    
    symbol = "GOOGL"
    print(f"\n🎯 Checking trigger for {symbol}...")
    
    # Get current price
    current_price = get_price(symbol)
    if not current_price:
        print(f"❌ Could not get current price for {symbol}")
        return
    
    # Set a trigger price (e.g., 5% below current)
    trigger_price = current_price * 0.95
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   Trigger Price: ${trigger_price:.2f} (5% below)")
    
    # Check trigger with forecast validation
    result = check_forecast_trigger(
        symbol=symbol,
        current_price=current_price,
        trigger_price=trigger_price,
        forecast_horizon=30
    )
    
    print(f"\n📊 Trigger Analysis:")
    print(f"   Price Diff: {result['price_diff_pct']:.2f}%")
    print(f"   Should Execute: {'✅ YES' if result['should_execute'] else '❌ NO'}")
    print(f"   Reason: {result['reason']}")
    
    if result.get("forecast_recommendation"):
        rec = result["forecast_recommendation"]
        print(f"\n   Forecast Recommendation:")
        print(f"     Action: {rec['action']}")
        print(f"     Expected Return: {rec['expected_return_pct']:.2f}%")


def demo_batch_analysis():
    """Demo: Batch analysis of multiple symbols."""
    print("\n" + "="*80)
    print("DEMO 4: Batch Analysis")
    print("="*80)
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    print(f"\n📊 Analyzing {len(symbols)} symbols...")
    
    trader = ForecastTrader()
    results = {}
    
    for symbol in symbols:
        prices = get_historical_prices(symbol, period="1y")
        if prices and len(prices) >= 20:
            result = trader.analyze_symbol(
                symbol=symbol,
                historical_prices=prices,
                forecast_horizon=30
            )
            if result.get("success"):
                results[symbol] = result
    
    # Get trusted recommendations
    trusted = trader.get_trusted_recommendations(results)
    
    print(f"\n✅ Analysis complete:")
    print(f"   Total analyzed: {len(results)}")
    print(f"   Trusted recommendations: {len(trusted)}")
    
    if trusted:
        print(f"\n💡 Top Recommendations:")
        for rec in trusted[:5]:  # Show top 5
            print(f"   {rec['symbol']}: {rec['action']} "
                  f"(Return: {rec['expected_return_pct']:.2f}%, "
                  f"Confidence: {rec['confidence'].upper()})")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("FORECAST INTEGRATION DEMO")
    print("="*80)
    print("\nThis demo shows how the forecasting system integrates with:")
    print("  - Historical price data")
    print("  - Trust evaluation")
    print("  - Trading recommendations")
    print("  - Trigger validation")
    print("="*80)
    
    try:
        demo_single_symbol_analysis()
        demo_forecast_service()
        demo_trigger_validation()
        demo_batch_analysis()
        
        print("\n" + "="*80)
        print("✅ ALL DEMOS COMPLETED")
        print("="*80)
        print("\n💡 Next Steps:")
        print("   1. Start the FastAPI dashboard: uvicorn main:app --reload")
        print("   2. Visit http://localhost:8000/triggers to add price triggers")
        print("   3. Approve trades at http://localhost:8000/trades")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

