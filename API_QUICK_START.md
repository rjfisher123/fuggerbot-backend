# FuggerBot API Quick Start

## Installation

Install FastAPI dependencies:

```bash
pip install fastapi uvicorn[standard]
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Running the API

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Or use Python directly:

```bash
python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### POST /api/forecast
Create a new forecast.

**Request Body:**
```json
{
  "symbol": "AAPL",
  "historical_prices": [150.0, 151.0, 152.0, ...],
  "forecast_horizon": 30,
  "options": {
    "context_length": null,
    "historical_period": "1y",
    "strict_mode": false,
    "min_trust_score": 0.6,
    "deterministic_mode": true
  }
}
```

**Response:**
```json
{
  "forecast_id": "abc123...",
  "symbol": "AAPL",
  "created_at": "2024-01-01T12:00:00",
  "forecast_horizon": 30,
  "model_name": "amazon/chronos-t5-tiny",
  "trust_score": 0.85,
  "fqs_score": 0.78,
  "regime": {...},
  "frs_score": 0.82,
  "coherence": {...},
  "recommendation": {...}
}
```

### GET /api/forecast/{forecast_id}
Retrieve a forecast by ID.

**Response:** Same as POST response above.

## Testing

### Using curl

```bash
# Create forecast
curl -X POST "http://localhost:8000/api/forecast" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "historical_prices": [150.0, 151.0, 152.0],
    "forecast_horizon": 30
  }'

# Get forecast
curl "http://localhost:8000/api/forecast/{forecast_id}"
```

### Using Python requests

```python
import requests

# Create forecast
response = requests.post(
    "http://localhost:8000/api/forecast",
    json={
        "symbol": "AAPL",
        "historical_prices": [150.0, 151.0, 152.0],
        "forecast_horizon": 30
    }
)
forecast = response.json()
print(f"Forecast ID: {forecast['forecast_id']}")

# Get forecast
forecast_id = forecast['forecast_id']
response = requests.get(f"http://localhost:8000/api/forecast/{forecast_id}")
retrieved_forecast = response.json()
```

## Notes

- The API uses the same forecast service as the Streamlit app
- Forecasts are persisted using the existing metadata system
- All forecasts created via API can be viewed in the Streamlit dashboard
- The API is designed to run alongside the Streamlit app (different ports)





