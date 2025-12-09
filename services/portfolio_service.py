from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from services.portfolio_repository import (
    PaperTradeRepository,
    PositionRepository,
    create_sample_positions,
    create_sample_trades,
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for retrieving portfolio summary, positions, and trade history via SQLite."""

    def __init__(self, db_path: Optional[Path] = None, use_sample_data: Optional[bool] = None):
        project_root = Path(__file__).parent.parent
        default_db_path = project_root / "data" / "paper_trades.db"
        self.db_path = db_path or default_db_path

        if use_sample_data is None:
            use_sample_data = os.getenv("PORTFOLIO_SAMPLE_DATA", "false").lower() == "true"
        self.use_sample_data = use_sample_data

        self.position_repo = PositionRepository(self.db_path)
        self.trade_repo = PaperTradeRepository(self.db_path)
        self.initial_capital = float(os.getenv("PAPER_TRADING_INITIAL_CAPITAL", "100000"))

        logger.info(f"PortfolioService initialized (db={self.db_path})")

    def _seed_sample_data(self):
        if not self.use_sample_data:
            return
        logger.info("Seeding sample portfolio data (PORTFOLIO_SAMPLE_DATA=true)")
        for position in create_sample_positions():
            self.position_repo.upsert_position(position)
        for trade in create_sample_trades():
            self.trade_repo.insert_trade(trade)

    def _load_data(self):
        positions = self.position_repo.get_open_positions()
        trades = self.trade_repo.get_recent_trades(limit=50)

        if not positions and not trades and self.use_sample_data:
            self._seed_sample_data()
            positions = self.position_repo.get_open_positions()
            trades = self.trade_repo.get_recent_trades(limit=50)

        return positions, trades

    def _calculate_summary(self, positions, trades) -> Dict[str, Any]:
        total_unrealized = sum(p.unrealized_pnl for p in positions)
        total_position_value = sum(p.current_value for p in positions)
        total_realized = sum(t.pnl for t in trades)

        total_capital = self.initial_capital + total_realized + total_unrealized
        current_capital = self.initial_capital + total_realized

        win_trades = sum(1 for t in trades if t.pnl > 0)
        win_rate = (win_trades / len(trades) * 100) if trades else 0.0

        return {
            "initial_capital": self.initial_capital,
            "current_capital": current_capital,
            "total_capital": total_capital,
            "total_return_pct": ((total_capital - self.initial_capital) / self.initial_capital) * 100,
            "open_positions": len(positions),
            "closed_trades": len(trades),
            "total_realized_pnl": total_realized,
            "total_realized_pnl_pct": (total_realized / self.initial_capital) * 100 if self.initial_capital else 0.0,
            "win_rate": win_rate,
            "total_unrealized_pnl": total_unrealized,
            "total_position_value": total_position_value,
        }

    def get_portfolio_data(self) -> Dict[str, Any]:
        positions, trades = self._load_data()
        summary = self._calculate_summary(positions, trades)
        last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "summary": summary,
            "open_positions": positions,
            "trade_history": trades,
            "last_updated": last_updated,
        }


_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
"""
Portfolio service for retrieving portfolio and paper trading data.

This service loads the latest saved paper trading snapshot if available.
If no snapshot exists, it provides a sample dataset for display purposes.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for retrieving portfolio summary, positions, and trade history."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            project_root = Path(__file__).parent.parent
            data_dir = project_root / "data" / "paper_trades"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PortfolioService initialized with data directory: {self.data_dir}")

    def _get_latest_snapshot_file(self) -> Optional[Path]:
        """Return the most recent paper trading snapshot file, if any."""
        files = sorted(self.data_dir.glob("paper_trades_*.json"), reverse=True)
        return files[0] if files else None

    def _load_snapshot(self) -> Optional[Dict[str, Any]]:
        """Load the latest snapshot from disk."""
        snapshot_file = self._get_latest_snapshot_file()
        if not snapshot_file or not snapshot_file.exists():
            return None

        try:
            with open(snapshot_file, "r") as f:
                data = json.load(f)
                data["last_updated"] = snapshot_file.stem.replace("paper_trades_", "")
                return data
        except Exception as e:
            logger.error(f"Error loading portfolio snapshot {snapshot_file}: {e}", exc_info=True)
            return None

    def _get_sample_data(self) -> Dict[str, Any]:
        """Return sample portfolio data when no snapshot is available."""
        sample_summary = {
            "initial_capital": 100000.0,
            "current_capital": 98500.0,
            "total_capital": 101250.0,
            "total_return_pct": 1.25,
            "open_positions": 2,
            "closed_trades": 5,
            "total_realized_pnl": 1250.0,
            "total_realized_pnl_pct": 1.25,
            "win_rate": 60.0,
        }

        sample_positions = [
            {
                "symbol": "AAPL",
                "entry_price": 170.25,
                "current_price": 174.10,
                "shares": 100,
                "position_value": 17410.0,
                "unrealized_pnl": 385.0,
                "unrealized_pnl_pct": 2.25,
                "forecast_id": "SAMPLE01",
                "entry_date": "2025-11-01",
            },
            {
                "symbol": "NVDA",
                "entry_price": 440.00,
                "current_price": 432.50,
                "shares": 40,
                "position_value": 17300.0,
                "unrealized_pnl": -300.0,
                "unrealized_pnl_pct": -1.70,
                "forecast_id": "SAMPLE02",
                "entry_date": "2025-11-10",
            },
        ]

        sample_trades = [
            {
                "symbol": "MSFT",
                "entry_price": 310.0,
                "exit_price": 325.5,
                "pnl": 1550.0,
                "pnl_pct": 5.0,
                "exit_reason": "take_profit",
                "holding_period_days": 12,
                "exit_date": "2025-10-25",
            },
            {
                "symbol": "TSLA",
                "entry_price": 240.0,
                "exit_price": 228.5,
                "pnl": -1150.0,
                "pnl_pct": -4.8,
                "exit_reason": "stop_loss",
                "holding_period_days": 8,
                "exit_date": "2025-10-20",
            },
        ]

        return {
            "summary": sample_summary,
            "open_positions": sample_positions,
            "trade_history": sample_trades,
            "last_updated": "Sample Data",
        }

    def get_portfolio_data(self) -> Dict[str, Any]:
        """
        Get portfolio summary, positions, and trade history.

        Returns:
            Dict with keys: summary, open_positions, trade_history, last_updated
        """
        snapshot = self._load_snapshot()
        if snapshot:
            summary = snapshot.get("summary", {})
            positions = snapshot.get("open_positions", [])
            trades = snapshot.get("trade_history", [])
            last_updated = snapshot.get("last_updated", "Snapshot")
        else:
            sample = self._get_sample_data()
            summary = sample["summary"]
            positions = sample["open_positions"]
            trades = sample["trade_history"]
            last_updated = sample["last_updated"]

        # Provide defaults for missing fields
        summary.setdefault("initial_capital", 100000.0)
        summary.setdefault("current_capital", summary["initial_capital"])
        summary.setdefault("total_capital", summary["current_capital"])
        summary.setdefault("total_return_pct", 0.0)
        summary.setdefault("open_positions", len(positions))
        summary.setdefault("closed_trades", len(trades))
        summary.setdefault("total_realized_pnl", 0.0)
        summary.setdefault("total_realized_pnl_pct", 0.0)
        summary.setdefault("win_rate", 0.0)

        return {
            "summary": summary,
            "open_positions": positions,
            "trade_history": trades,
            "last_updated": last_updated,
        }


# Global service instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create global portfolio service instance."""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service

