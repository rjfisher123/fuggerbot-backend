# FuggerBot

AI-powered asymmetric investment automation.

## Structure
- `api/` – FastAPI routers (forecast, backtest, triggers, trades, portfolio)
- `services/` – Business logic shared by API + background jobs
- `ui/templates/` – Jinja templates for the dashboard
- `frontend/` - Next.js/React Dashboard (Antigravity IO)

## Launch
**Backend**: `./start.sh` or `uvicorn main:app --reload`
**Frontend**: `cd frontend && npm run dev`
