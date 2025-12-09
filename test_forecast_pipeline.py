#!/usr/bin/env python3
"""
Test script for the forecasting pipeline (Phase 1 + Phase 2).

This script demonstrates:
1. Generating forecasts using Chronos (TSFM)
2. Evaluating trust scores
3. Filtering low-confidence forecasts
"""
import sys
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.tsfm.inference import ChronosInferenceEngine
from models.tsfm.schemas import ForecastInput
from models.trust.filter import TrustFilter
from models.trust.schemas import TrustFilterConfig

# Import logger directly to avoid circular imports
import logging
logger = logging.getLogger("fuggerbot")
if not logger.handlers:
    # Setup basic logging if not already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("fuggerbot")


def generate_sample_series(length: int = 100, trend: float = 0.1, noise: float = 0.5) -> list:
    """Generate a sample time series for testing."""
    t = np.arange(length)
    series = 100 + trend * t + noise * np.random.randn(length)
    # Add some seasonality
    series += 5 * np.sin(2 * np.pi * t / 20)
    return series.tolist()


def test_single_forecast():
    """Test single forecast generation and trust evaluation."""
    print("\n" + "="*80)
    print("TEST 1: Single Forecast with Trust Evaluation")
    print("="*80)
    
    # Generate sample data
    historical_data = generate_sample_series(length=100, trend=0.1, noise=0.5)
    print(f"\n📊 Generated historical series: {len(historical_data)} points")
    print(f"   Range: ${min(historical_data):.2f} - ${max(historical_data):.2f}")
    
    # Create forecast input
    forecast_input = ForecastInput(
        series=historical_data,
        forecast_horizon=30,
        context_length=50,
        metadata={"symbol": "TEST", "frequency": "daily"}
    )
    
    # Generate forecast
    print("\n🔮 Generating forecast...")
    engine = ChronosInferenceEngine(model_name="amazon/chronos-t5-tiny")
    
    try:
        forecast = engine.forecast(forecast_input)
        print(f"✅ Forecast generated in {forecast.inference_time_ms:.1f}ms")
        print(f"   Point forecast range: ${min(forecast.point_forecast):.2f} - ${max(forecast.point_forecast):.2f}")
        print(f"   Uncertainty range: ${min(forecast.lower_bound):.2f} - ${max(forecast.upper_bound):.2f}")
    except Exception as e:
        print(f"❌ Forecast generation failed: {e}")
        return
    
    # Evaluate trust
    print("\n🔍 Evaluating trust...")
    trust_filter = TrustFilter()
    evaluation = trust_filter.evaluate(
        forecast=forecast,
        input_data=forecast_input,
        symbol="TEST"
    )
    
    # Display results
    print(f"\n📈 Trust Evaluation Results:")
    print(f"   Overall Trust Score: {evaluation.metrics.overall_trust_score:.3f}")
    print(f"   Confidence Level: {evaluation.metrics.confidence_level.upper()}")
    print(f"   Is Trusted: {'✅ YES' if evaluation.is_trusted else '❌ NO'}")
    
    print(f"\n📊 Individual Metrics:")
    print(f"   Uncertainty Score: {evaluation.metrics.uncertainty_score:.3f}")
    print(f"   Consistency Score: {evaluation.metrics.consistency_score:.3f}")
    print(f"   Data Quality Score: {evaluation.metrics.data_quality_score:.3f}")
    if evaluation.metrics.historical_accuracy:
        print(f"   Historical Accuracy: {evaluation.metrics.historical_accuracy:.3f}")
    if evaluation.metrics.market_regime_score:
        print(f"   Market Regime Score: {evaluation.metrics.market_regime_score:.3f}")
    
    if evaluation.metrics.rejection_reasons:
        print(f"\n⚠️  Rejection Reasons:")
        for reason in evaluation.metrics.rejection_reasons:
            print(f"   - {reason}")
    else:
        print(f"\n✅ No rejection reasons - forecast passed all checks!")


def test_batch_forecast():
    """Test batch forecast generation and filtering."""
    print("\n" + "="*80)
    print("TEST 2: Batch Forecast with Trust Filtering")
    print("="*80)
    
    # Generate multiple series
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    forecasts = []
    forecast_inputs = []
    
    print(f"\n📊 Generating forecasts for {len(symbols)} symbols...")
    
    engine = ChronosInferenceEngine()
    
    for symbol in symbols:
        # Generate different patterns for each symbol
        trend = np.random.uniform(-0.2, 0.3)
        noise = np.random.uniform(0.3, 0.8)
        historical_data = generate_sample_series(length=80, trend=trend, noise=noise)
        
        forecast_input = ForecastInput(
            series=historical_data,
            forecast_horizon=20,
            metadata={"symbol": symbol}
        )
        
        try:
            forecast = engine.forecast(forecast_input)
            forecasts.append(forecast)
            forecast_inputs.append(forecast_input)
            print(f"   ✅ {symbol}: Forecast generated")
        except Exception as e:
            print(f"   ❌ {symbol}: Failed - {e}")
    
    if not forecasts:
        print("❌ No forecasts generated")
        return
    
    # Evaluate trust for all
    print(f"\n🔍 Evaluating trust for {len(forecasts)} forecasts...")
    trust_filter = TrustFilter()
    
    trusted_forecasts, evaluations = trust_filter.filter_trusted(
        forecasts=forecasts,
        input_data_list=forecast_inputs,
        symbols=symbols
    )
    
    # Display results
    print(f"\n📈 Batch Trust Evaluation Results:")
    print(f"   Total Forecasts: {len(forecasts)}")
    print(f"   Trusted: {len(trusted_forecasts)} ✅")
    print(f"   Rejected: {len(forecasts) - len(trusted_forecasts)} ❌")
    
    if evaluations:
        avg_score = sum(e.metrics.overall_trust_score for e in evaluations) / len(evaluations)
        print(f"   Average Trust Score: {avg_score:.3f}")
    
    print(f"\n📊 Detailed Results:")
    for i, eval_result in enumerate(evaluations):
        symbol = symbols[i] if i < len(symbols) else f"Symbol_{i}"
        status = "✅ TRUSTED" if eval_result.is_trusted else "❌ REJECTED"
        print(f"   {symbol}: {status} (Score: {eval_result.metrics.overall_trust_score:.3f}, "
              f"Confidence: {eval_result.metrics.confidence_level})")


def test_trust_filter_config():
    """Test different trust filter configurations."""
    print("\n" + "="*80)
    print("TEST 3: Trust Filter Configuration Testing")
    print("="*80)
    
    # Generate sample forecast
    historical_data = generate_sample_series(length=100)
    forecast_input = ForecastInput(series=historical_data, forecast_horizon=30)
    
    engine = ChronosInferenceEngine()
    forecast = engine.forecast(forecast_input)
    
    # Test with different configurations
    configs = [
        ("Lenient", TrustFilterConfig(min_trust_score=0.4, enable_strict_mode=False)),
        ("Moderate", TrustFilterConfig(min_trust_score=0.6, enable_strict_mode=False)),
        ("Strict", TrustFilterConfig(min_trust_score=0.75, enable_strict_mode=True)),
    ]
    
    print(f"\n🔍 Testing with different trust filter configurations...")
    
    for config_name, config in configs:
        trust_filter = TrustFilter(config=config)
        evaluation = trust_filter.evaluate(forecast=forecast, input_data=forecast_input)
        
        print(f"\n   {config_name} Config (min_score={config.min_trust_score}, "
              f"strict={config.enable_strict_mode}):")
        print(f"      Trust Score: {evaluation.metrics.overall_trust_score:.3f}")
        print(f"      Result: {'✅ TRUSTED' if evaluation.is_trusted else '❌ REJECTED'}")


def test_poor_quality_forecast():
    """Test trust filter with intentionally poor quality data."""
    print("\n" + "="*80)
    print("TEST 4: Poor Quality Data Detection")
    print("="*80)
    
    # Generate poor quality series (lots of noise, outliers, short length)
    print("\n📊 Generating poor quality series (high noise, outliers, short length)...")
    poor_series = [100 + 10 * np.random.randn() for _ in range(15)]  # Short and noisy
    poor_series[5] = 200  # Outlier
    poor_series[10] = 50  # Another outlier
    
    forecast_input = ForecastInput(series=poor_series, forecast_horizon=20)
    
    engine = ChronosInferenceEngine()
    forecast = engine.forecast(forecast_input)
    
    # Evaluate trust
    trust_filter = TrustFilter()
    evaluation = trust_filter.evaluate(forecast=forecast, input_data=forecast_input)
    
    print(f"\n📈 Trust Evaluation for Poor Quality Data:")
    print(f"   Overall Trust Score: {evaluation.metrics.overall_trust_score:.3f}")
    print(f"   Data Quality Score: {evaluation.metrics.data_quality_score:.3f}")
    print(f"   Is Trusted: {'✅ YES' if evaluation.is_trusted else '❌ NO'}")
    
    if evaluation.metrics.rejection_reasons:
        print(f"\n⚠️  Rejection Reasons:")
        for reason in evaluation.metrics.rejection_reasons:
            print(f"   - {reason}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("FORECASTING PIPELINE TEST SUITE")
    print("Phase 1: TSFM (Time Series Forecasting Model)")
    print("Phase 2: Trust Filter")
    print("="*80)
    
    try:
        test_single_forecast()
        test_batch_forecast()
        test_trust_filter_config()
        test_poor_quality_forecast()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)
        print("\n💡 Next Steps:")
        print("   1. Install Chronos: pip install git+https://github.com/amazon-science/chronos-forecasting.git")
        print("   2. Update inference.py with real Chronos pipeline.predict() call")
        print("   3. Integrate with trading system using models/forecast_trader.py")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

