"""Repository classes for backtest results."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc

from persistence.models_backtest import Backtest


class BacktestRepository:
    """Repository for managing backtest results."""

    def __init__(self, session: Session):
        self.session = session

    def add_backtest(
        self,
        backtest_id: str,
        forecast_id: str,
        symbol: str,
        horizon: int,
        realised_series: List[float],
        metrics: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Backtest:
        """
        Add a new backtest result.
        
        Args:
            backtest_id: Unique backtest identifier
            forecast_id: ID of the forecast that was evaluated
            symbol: Trading symbol
            horizon: Forecast horizon (number of periods)
            realised_series: Actual prices that occurred
            metrics: Dictionary with all backtest metrics
            metadata: Optional additional metadata
        
        Returns:
            Created Backtest
        """
        backtest = Backtest(
            backtest_id=backtest_id,
            forecast_id=forecast_id,
            symbol=symbol,
            horizon=horizon,
            realised_series=json.dumps(realised_series),
            metrics=json.dumps(metrics),
            backtest_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )
        self.session.add(backtest)
        self.session.commit()
        self.session.refresh(backtest)
        return backtest

    def get_by_id(self, backtest_id: str) -> Optional[Backtest]:
        """Get backtest by backtest_id."""
        return (
            self.session.query(Backtest)
            .filter(Backtest.backtest_id == backtest_id)
            .first()
        )

    def get_by_forecast_id(self, forecast_id: str, limit: int = 100) -> List[Backtest]:
        """
        Get backtests for a specific forecast.
        
        Args:
            forecast_id: Forecast ID
            limit: Maximum number to return
        
        Returns:
            List of Backtest objects, most recent first
        """
        return (
            self.session.query(Backtest)
            .filter(Backtest.forecast_id == forecast_id)
            .order_by(desc(Backtest.created_at))
            .limit(limit)
            .all()
        )

    def list_recent(self, limit: int = 100) -> List[Backtest]:
        """
        List recent backtest results.
        
        Args:
            limit: Maximum number to return
        
        Returns:
            List of Backtest objects, most recent first
        """
        return (
            self.session.query(Backtest)
            .order_by(desc(Backtest.created_at))
            .limit(limit)
            .all()
        )

    def list_by_symbol(self, symbol: str, limit: int = 100) -> List[Backtest]:
        """
        List backtests for a specific symbol.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number to return
        
        Returns:
            List of Backtest objects, most recent first
        """
        return (
            self.session.query(Backtest)
            .filter(Backtest.symbol == symbol.upper())
            .order_by(desc(Backtest.created_at))
            .limit(limit)
            .all()
        )

    def delete_backtest(self, backtest_id: str) -> bool:
        """
        Delete a backtest result.
        
        Args:
            backtest_id: Backtest ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        backtest = self.get_by_id(backtest_id)
        if not backtest:
            return False
        self.session.delete(backtest)
        self.session.commit()
        return True

