"""
Daily forecast scheduler.

Automatically generates and stores forecasts on a schedule.
"""
import schedule
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.forecast_trader import ForecastTrader
from models.forecast_metadata import ForecastMetadata
from dash.utils.forecast_helper import get_historical_prices

logger = logging.getLogger(__name__)


class ForecastScheduler:
    """Schedules and runs daily forecasts."""
    
    def __init__(
        self,
        symbols: List[str],
        forecast_horizon: int = 30,
        historical_period: str = "1y",
        context_length: Optional[int] = None
    ):
        """
        Initialize forecast scheduler.
        
        Args:
            symbols: List of symbols to forecast daily
            forecast_horizon: Forecast horizon in days
            historical_period: Historical data period
            context_length: Context window size
        """
        self.symbols = symbols
        self.forecast_horizon = forecast_horizon
        self.historical_period = historical_period
        self.context_length = context_length
        
        self.forecast_trader = ForecastTrader()
        self.metadata = ForecastMetadata()
        
        logger.info(f"ForecastScheduler initialized for {len(symbols)} symbols")
    
    def run_daily_forecasts(self) -> Dict[str, Any]:
        """
        Run forecasts for all symbols.
        
        Returns:
            Dict with results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "symbols_processed": 0,
            "symbols_successful": 0,
            "symbols_failed": 0,
            "forecasts": []
        }
        
        for symbol in self.symbols:
            try:
                logger.info(f"Generating daily forecast for {symbol}")
                
                # Get historical data
                prices = get_historical_prices(symbol, period=self.historical_period)
                if not prices or len(prices) < 20:
                    logger.warning(f"Insufficient data for {symbol}")
                    results["symbols_failed"] += 1
                    continue
                
                # Generate forecast
                result = self.forecast_trader.analyze_symbol(
                    symbol=symbol,
                    historical_prices=prices,
                    forecast_horizon=self.forecast_horizon,
                    context_length=self.context_length
                )
                
                results["symbols_processed"] += 1
                
                if result.get("success") and result["trust_evaluation"].is_trusted:
                    # Save snapshot
                    parameters = {
                        "context_length": self.context_length,
                        "historical_period": self.historical_period,
                        "strict_mode": False,
                        "min_trust_score": 0.6,
                        "forecast_horizon": self.forecast_horizon
                    }
                    
                    forecast_id = self.metadata.generate_forecast_id(symbol, parameters)
                    snapshot_path = self.metadata.save_forecast_snapshot(
                        forecast_id, symbol, parameters, result
                    )
                    
                    # Extract key metrics for time series
                    forecast = result["forecast"]
                    recommendation = result["recommendation"]
                    trust_eval = result["trust_evaluation"]
                    
                    forecast_summary = {
                        "symbol": symbol,
                        "forecast_id": forecast_id,
                        "timestamp": datetime.now().isoformat(),
                        "expected_return_pct": recommendation.get("expected_return_pct", 0),
                        "risk_pct": recommendation.get("risk_pct", 0),
                        "trust_score": trust_eval.metrics.overall_trust_score,
                        "confidence": trust_eval.metrics.confidence_level,
                        "action": recommendation.get("action", "HOLD"),
                        "snapshot_path": str(snapshot_path)
                    }
                    
                    results["forecasts"].append(forecast_summary)
                    results["symbols_successful"] += 1
                    
                    logger.info(f"✅ Forecast generated for {symbol}: {forecast_id}")
                else:
                    results["symbols_failed"] += 1
                    logger.warning(f"Forecast failed or not trusted for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error generating forecast for {symbol}: {e}", exc_info=True)
                results["symbols_failed"] += 1
        
        # Save daily summary
        self._save_daily_summary(results)
        
        logger.info(
            f"Daily forecasts complete: {results['symbols_successful']}/{results['symbols_processed']} successful"
        )
        
        return results
    
    def _save_daily_summary(self, results: Dict[str, Any]) -> None:
        """Save daily forecast summary."""
        summary_dir = self.metadata.storage_dir.parent / "daily_summaries"
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        summary_file = summary_dir / f"forecast_summary_{date_str}.json"
        
        import json
        with open(summary_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Daily summary saved: {summary_file}")
    
    def start_scheduler(self, run_time: str = "09:00") -> None:
        """
        Start the daily forecast scheduler.
        
        Args:
            run_time: Time to run forecasts daily (HH:MM format)
        """
        schedule.every().day.at(run_time).do(self.run_daily_forecasts)
        
        logger.info(f"Forecast scheduler started - will run daily at {run_time}")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Forecast scheduler stopped")


def run_scheduler_cli():
    """CLI entry point for forecast scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Forecast Scheduler")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to forecast")
    parser.add_argument("--time", default="09:00", help="Daily run time (HH:MM)")
    parser.add_argument("--horizon", type=int, default=30, help="Forecast horizon")
    parser.add_argument("--period", default="1y", help="Historical period")
    
    args = parser.parse_args()
    
    scheduler = ForecastScheduler(
        symbols=args.symbols,
        forecast_horizon=args.horizon,
        historical_period=args.period
    )
    
    scheduler.start_scheduler(run_time=args.time)


if __name__ == "__main__":
    run_scheduler_cli()





