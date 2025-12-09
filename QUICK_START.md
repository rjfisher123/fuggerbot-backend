# Quick Start Guide - FuggerBot Forecasting Dashboard

## 🚀 Run the FastAPI Dashboard

### Start the FastAPI server
```bash
cd /Users/ryanfisher/fuggerbot
uvicorn main:app --reload
```

Open your browser to **http://localhost:8000**. You’ll see links to the dashboard pages and the interactive API docs.

### Dashboard Pages
- **/forecast** – Forecast creation + visualization
- **/backtest** – Evaluate forecasts vs actuals
- **/triggers** – Manage price triggers
- **/trades** – Approve/reject IBKR trades
- **/portfolio** – Review portfolio + paper trades

API documentation is available at **/docs** (Swagger UI) and **/redoc**.

---

## 🧪 Test Commands

### Test Chronos Integration
```bash
# Test that Chronos is working
python test_chronos_integration.py
```

### Test Full Pipeline
```bash
# Test forecasting + trust filter
python test_forecast_pipeline.py
```

### Test Integration Demo
```bash
# See full integration examples
python demo_forecast_integration.py
```

---

## 📊 Dashboard Features

- **Forecast**: Chronos-based inference, trust metrics, recommendations
- **Backtest**: Compare forecasts vs realized prices, view metrics
- **Triggers**: Create/enable/disable price triggers with SMS approvals
- **Trades**: Approve/reject IBKR trades, monitor connection status
- **Portfolio**: Review capital summary, open positions, paper trades

---

## 🔧 Configuration

### Adjust Trust Thresholds
In the Forecast Analysis page:
- Use the **"Min Trust Score"** slider (default: 0.6)
- Enable **"Strict Mode"** for stricter filtering
- Adjust **"Context Length"** for historical data window

### Forecast Horizon
- Set **"Forecast Horizon"** (1-365 days)
- Default: 30 days

---

## 💡 Example Workflow

1. **Start the FastAPI server**:
   ```bash
   uvicorn main:app --reload
   ```
2. Navigate to `http://localhost:8000/forecast`
3. Enter `AAPL`, set horizon to `30`, and click “Generate Forecast”
4. Review trust/FQS scores and recommendations
5. Jump to `/triggers` to add a price trigger
6. Monitor approvals at `/trades` and portfolio stats at `/portfolio`

---

## 🐛 Troubleshooting

### If Chronos is Not Installed
The system automatically uses **mock forecasts** - this is fine for testing!

To install real Chronos:
```bash
pip install git+https://github.com/amazon-science/chronos-forecasting.git
```

### If the FastAPI server won't start
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server with logging
uvicorn main:app --reload --log-level debug
```

### View Logs
```bash
# Check application logs
tail -f data/logs/fuggerbot.log
```

---

## 📝 Quick Reference

| Command | Purpose |
|---------|---------|
| `uvicorn main:app --reload` | Start FastAPI dashboard |
| `python test_chronos_integration.py` | Test Chronos |
| `python test_forecast_pipeline.py` | Test full pipeline |
| `python demo_forecast_integration.py` | See integration examples |

---

## 🎯 Next Steps

1. **Run the dashboard** and explore Forecast Analysis
2. **Test with different symbols** (AAPL, MSFT, TSLA, etc.)
3. **Try batch analysis** for multiple symbols
4. **Adjust trust thresholds** to see how filtering works
5. **Check trading recommendations** based on forecasts

Enjoy exploring the FastAPI dashboard! 🚀

---

### Looking for the legacy Streamlit UI?
The Streamlit app is now deprecated but still available under `dash/`. See `LEGACY_STREAMLIT.md` if you need to launch it for reference.

