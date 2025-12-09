# FuggerBot

AI-powered asymmetric investment automation.

## Structure
- `api/` – FastAPI routers (forecast, backtest, triggers, trades, portfolio)
- `services/` – Business logic shared by API + background jobs
- `ui/templates/` – Jinja templates for the dashboard
- `dash/` – Legacy Streamlit UI (deprecated, see `LEGACY_STREAMLIT.md`)
