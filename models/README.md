# Forecasting & Trust Filter System

This directory contains the forecasting backbone and trust filter system for FuggerBot.

## Architecture

### Phase 1: Forecasting Backbone (`tsfm/`)
- **`schemas.py`**: Pydantic data contracts for forecasts
- **`inference.py`**: Chronos model inference engine

### Phase 2: Trust Filter (`trust/`)
- **`schemas.py`**: Trust evaluation data contracts
- **`metrics.py`**: Trust scoring calculations
- **`filter.py`**: Main trust filter engine

### Integration (`forecast_trader.py`)
- High-level interface combining forecasting + trust filtering
- Trading recommendation generation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install git+https://github.com/amazon-science/chronos-forecasting.git
```

### 2. Run Test Suite

```bash
python test_forecast_pipeline.py
```

### 3. Basic Usage

```python
from models.forecast_trader import ForecastTrader
import yfinance as yf

# Initialize
trader = ForecastTrader()

# Get historical data
ticker = yf.Ticker("AAPL")
hist = ticker.history(period="1y")
prices = hist["Close"].tolist()

# Analyze symbol
result = trader.analyze_symbol(
    symbol="AAPL",
    historical_prices=prices,
    forecast_horizon=30
)

# Check if trusted
if result["trust_evaluation"].is_trusted:
    recommendation = result["recommendation"]
    print(f"Action: {recommendation['action']}")
    print(f"Expected Return: {recommendation['expected_return_pct']:.2f}%")
    print(f"Confidence: {recommendation['confidence']}")
```

## Integration with Trading System

The `ForecastTrader` class can be integrated into your existing trading workflow:

```python
from models.forecast_trader import ForecastTrader
from core.ibkr_trader import get_ibkr_trader

# Initialize
forecast_trader = ForecastTrader()
ibkr_trader = get_ibkr_trader()

# Analyze symbols
symbols = ["AAPL", "MSFT", "GOOGL"]
results = {}

for symbol in symbols:
    # Get historical prices (from your price feed)
    prices = get_historical_prices(symbol)
    
    # Analyze
    result = forecast_trader.analyze_symbol(
        symbol=symbol,
        historical_prices=prices,
        forecast_horizon=30
    )
    results[symbol] = result

# Get trusted recommendations
recommendations = forecast_trader.get_trusted_recommendations(results)

# Execute trades for high-confidence recommendations
for rec in recommendations:
    if rec["confidence"] == "high" and rec["action"] == "BUY":
        ibkr_trader.execute_trade(
            symbol=rec["symbol"],
            action="BUY",
            quantity=10,
            require_confirmation=True
        )
```

## Configuration

### Trust Filter Configuration

```python
from models.trust.schemas import TrustFilterConfig
from models.forecast_trader import ForecastTrader

# Custom trust filter config
config = TrustFilterConfig(
    min_trust_score=0.7,  # Higher threshold
    enable_strict_mode=True,  # All thresholds must pass
    min_uncertainty_score=0.6,
    min_consistency_score=0.6
)

trader = ForecastTrader(trust_config=config)
```

## Files Structure

```
models/
├── __init__.py
├── README.md
├── forecast_trader.py      # Integration module
├── tsfm/                   # Phase 1: Forecasting
│   ├── __init__.py
│   ├── schemas.py
│   └── inference.py
└── trust/                  # Phase 2: Trust Filter
    ├── __init__.py
    ├── schemas.py
    ├── metrics.py
    └── filter.py
```

## Next Steps

1. **Update Chronos Integration**: Once Chronos is installed, update `models/tsfm/inference.py` to use real `pipeline.predict()` calls
2. **Historical Accuracy Tracking**: Implement persistent storage for accuracy history
3. **Market Data Integration**: Connect to your price feed for real-time analysis
4. **Trading Integration**: Integrate with `core/ibkr_trader.py` for automated trading






