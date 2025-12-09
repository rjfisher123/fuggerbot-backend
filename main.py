"""
FastAPI application for FuggerBot.

Provides REST API endpoints for forecast creation and retrieval.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.forecast import router as forecast_router, dashboard_router as forecast_dashboard_router
from api.forecast_performance import dashboard_router as forecast_performance_dashboard_router
from api.backtest import router as backtest_router, dashboard_router as backtest_dashboard_router
from api.triggers import dashboard_router as triggers_dashboard_router
from api.portfolio import dashboard_router as portfolio_dashboard_router
from api.trades import router as trades_router, dashboard_router as trades_dashboard_router
from api.candidates import dashboard_router as candidates_dashboard_router
from api.auth import router as auth_router, dashboard_router as auth_dashboard_router
from api.market_data import router as market_data_router
from core.logger import logger

# Create FastAPI app
app = FastAPI(
    title="FuggerBot API",
    description="REST API for FuggerBot forecasting and trading system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(auth_dashboard_router)
app.include_router(market_data_router)
app.include_router(forecast_router)
app.include_router(backtest_router)
app.include_router(trades_router)
app.include_router(forecast_dashboard_router)
app.include_router(forecast_performance_dashboard_router)
app.include_router(backtest_dashboard_router)
app.include_router(triggers_dashboard_router)
app.include_router(portfolio_dashboard_router)
app.include_router(trades_dashboard_router)
app.include_router(candidates_dashboard_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "FuggerBot API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FuggerBot API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)

