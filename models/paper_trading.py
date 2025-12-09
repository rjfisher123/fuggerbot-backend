"""
Paper Trading Engine.

Simulates trades with position sizing, exits, stops, and drift-based pauses.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from models.forecast_metadata import ForecastMetadata
from models.position_sizing import PositionSizer
from models.regime_classifier import RegimeClassifier
from models.drift_detection import DriftDetector

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """Simulates paper trading with full risk management."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize paper trading engine.
        
        Args:
            initial_capital: Starting capital for simulation
            storage_dir: Directory for trade records
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent / "data" / "paper_trades"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.position_sizer = PositionSizer()
        self.regime_classifier = RegimeClassifier()
        self.drift_detector = DriftDetector()
        self.metadata = ForecastMetadata()
    
    def open_position(
        self,
        symbol: str,
        forecast_id: str,
        entry_price: float,
        forecast_data: Dict[str, Any],
        regime_data: Dict[str, Any],
        position_size_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Open a paper trading position.
        
        Args:
            symbol: Trading symbol
            forecast_id: Forecast ID for tracking
            entry_price: Entry price
            forecast_data: Forecast data dict
            regime_data: Regime classification
            position_size_pct: Optional position size (if None, calculated)
            
        Returns:
            Dict with position details
        """
        # Calculate position size if not provided
        if position_size_pct is None:
            recommendation = forecast_data.get("recommendation", {})
            position_rec = self.position_sizer.calculate_position_size(
                expected_return_pct=recommendation.get("expected_return_pct", 0),
                risk_pct=recommendation.get("risk_pct", 0),
                fqs_score=forecast_data.get("fqs", {}).get("fqs_score", 0.5),
                regime=regime_data
            )
            position_size_pct = position_rec["position_size_pct"]
        
        # Calculate position value
        position_value = self.current_capital * (position_size_pct / 100.0)
        shares = position_value / entry_price
        
        # Create position
        position = {
            "symbol": symbol,
            "forecast_id": forecast_id,
            "entry_price": entry_price,
            "shares": shares,
            "position_value": position_value,
            "position_size_pct": position_size_pct,
            "entry_date": datetime.now().isoformat(),
            "forecast_data": forecast_data,
            "regime_data": regime_data,
            "status": "open"
        }
        
        self.positions[symbol] = position
        
        # Update capital (reserve position value)
        self.current_capital -= position_value
        
        logger.info(f"Opened paper position: {symbol} @ ${entry_price:.2f}, {shares:.2f} shares, ${position_value:.2f}")
        
        return position
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str = "manual"
    ) -> Dict[str, Any]:
        """
        Close a paper trading position.
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_reason: Reason for exit (manual, stop_loss, take_profit, regime_exit, drift_pause)
            
        Returns:
            Dict with trade result
        """
        if symbol not in self.positions:
            return {"error": f"No open position for {symbol}"}
        
        position = self.positions[symbol]
        entry_price = position["entry_price"]
        shares = position["shares"]
        
        # Calculate P/L
        entry_value = position["position_value"]
        exit_value = shares * exit_price
        pnl = exit_value - entry_value
        pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0
        
        # Update capital
        self.current_capital += exit_value
        
        # Create trade record
        trade_record = {
            "symbol": symbol,
            "forecast_id": position["forecast_id"],
            "entry_price": entry_price,
            "exit_price": exit_price,
            "shares": shares,
            "entry_value": entry_value,
            "exit_value": exit_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "entry_date": position["entry_date"],
            "exit_date": datetime.now().isoformat(),
            "exit_reason": exit_reason,
            "holding_period_days": (
                datetime.now() - datetime.fromisoformat(position["entry_date"])
            ).days
        }
        
        self.trade_history.append(trade_record)
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"Closed position: {symbol}, P/L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        
        return trade_record
    
    def check_stop_conditions(
        self,
        symbol: str,
        current_price: float,
        forecast_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Check if position should be closed due to stop conditions.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            forecast_data: Optional updated forecast data
            
        Returns:
            Exit reason if stop triggered, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        entry_price = position["entry_price"]
        current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # Stop loss: -10%
        if current_pnl_pct <= -10.0:
            return "stop_loss"
        
        # Take profit: +20%
        if current_pnl_pct >= 20.0:
            return "take_profit"
        
        # Regime exit: Check if regime changed to problematic
        if forecast_data:
            regime = forecast_data.get("regime", {})
            regime_type = regime.get("regime", "normal")
            
            if regime_type in ["low_predictability", "data_quality_degradation", "overconfidence"]:
                return "regime_exit"
        
        # Drift pause: Check for drift
        drift_report = self.drift_detector.detect_drift(symbol, days=30)
        if drift_report.get("requires_attention"):
            return "drift_pause"
        
        return None
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary."""
        total_position_value = sum(pos["position_value"] for pos in self.positions.values())
        total_capital = self.current_capital + total_position_value
        
        # Calculate unrealized P/L (would need current prices)
        open_positions = len(self.positions)
        closed_trades = len(self.trade_history)
        
        if self.trade_history:
            total_realized_pnl = sum(t["pnl"] for t in self.trade_history)
            total_realized_pnl_pct = (total_realized_pnl / self.initial_capital) * 100
            win_rate = sum(1 for t in self.trade_history if t["pnl"] > 0) / len(self.trade_history) * 100
        else:
            total_realized_pnl = 0.0
            total_realized_pnl_pct = 0.0
            win_rate = 0.0
        
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_capital": total_capital,
            "total_return_pct": ((total_capital - self.initial_capital) / self.initial_capital) * 100,
            "open_positions": open_positions,
            "closed_trades": closed_trades,
            "total_realized_pnl": total_realized_pnl,
            "total_realized_pnl_pct": total_realized_pnl_pct,
            "win_rate": win_rate,
            "positions": list(self.positions.keys())
        }
    
    def save_trade_history(self) -> Path:
        """Save trade history to file."""
        filename = f"paper_trades_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.storage_dir / filename
        
        data = {
            "summary": self.get_portfolio_summary(),
            "trade_history": self.trade_history,
            "open_positions": list(self.positions.values())
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        return filepath




