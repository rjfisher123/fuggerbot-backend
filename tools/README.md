# FuggerBot Tools

## Dashboard

The `dashboard.py` provides a real-time view of the bot's reasoning state.

### Usage

```bash
streamlit run tools/dashboard.py
```

### Features

- **Live Production Data**: View real-time trade decisions from `data/trade_memory.json`
- **War Games Simulation**: View test data from `data/test_memory_wargames.json`
- **KPI Metrics**: Hit rate, regret rate, total PnL, trade count
- **Visualizations**: 
  - Decision boundary scatter plot (Trust Score vs LLM Confidence)
  - Recent activity bar chart
- **Raw Data Table**: Complete reasoning logs with all details

### Data Source Toggle

Use the sidebar to switch between:
- **Live Production**: Real bot decisions (default)
- **War Games Simulation**: Test evaluation data

The dashboard auto-refreshes every 5 seconds to show latest decisions.


