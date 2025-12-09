"""
Date Anchoring for Multi-Symbol Analysis.

Freezes historical window to ensure consistent inputs across runs.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class DateAnchoring:
    """Manages date anchoring for reproducible multi-symbol analysis."""
    
    def __init__(self, anchor_date: Optional[datetime] = None):
        """
        Initialize date anchoring.
        
        Args:
            anchor_date: Optional fixed anchor date (defaults to latest trading date)
        """
        self.anchor_date = anchor_date
        if anchor_date:
            logger.info(f"Date anchored to: {anchor_date.strftime('%Y-%m-%d')}")
    
    def get_anchored_period(
        self,
        period: str = "1y",
        reference_date: Optional[datetime] = None
    ) -> Tuple[datetime, datetime]:
        """
        Get anchored date range for historical data.
        
        Args:
            period: Period string (1y, 6mo, etc.)
            reference_date: Optional reference date (defaults to anchor_date or now)
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if reference_date is None:
            reference_date = self.anchor_date or datetime.now()
        
        # Parse period
        period_map = {
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "6mo": 180,
            "3mo": 90,
            "1mo": 30
        }
        
        days = period_map.get(period, 365)
        
        # Calculate dates
        end_date = reference_date
        start_date = end_date - timedelta(days=days)
        
        return start_date, end_date
    
    def get_latest_trading_date(
        self,
        prices_data: list,
        date_field: Optional[str] = None
    ) -> Optional[datetime]:
        """
        Extract latest available trading date from dataset.
        
        Args:
            prices_data: Price data (list of dicts or list of values)
            date_field: Optional date field name if data is dicts
            
        Returns:
            Latest trading date or None
        """
        # If we have a list of prices without dates, assume most recent is "today"
        # In practice, you'd extract from yfinance data
        if isinstance(prices_data, list) and len(prices_data) > 0:
            # For now, return current date (in real implementation, extract from yfinance)
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        return None
    
    def freeze_for_analysis(
        self,
        symbols: list,
        period: str = "1y"
    ) -> Dict[str, Tuple[datetime, datetime]]:
        """
        Freeze date ranges for multi-symbol analysis.
        
        Args:
            symbols: List of symbols to analyze
            period: Historical period
            
        Returns:
            Dict mapping symbols to (start_date, end_date) tuples
        """
        # Get latest trading date (would extract from actual data in production)
        latest_date = self.anchor_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Freeze dates for all symbols
        frozen_ranges = {}
        start_date, end_date = self.get_anchored_period(period, latest_date)
        
        for symbol in symbols:
            frozen_ranges[symbol] = (start_date, end_date)
        
        logger.info(
            f"Frozen date range for {len(symbols)} symbols: "
            f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        
        return frozen_ranges
    
    def set_anchor_date(self, date: datetime) -> None:
        """Set anchor date for reproducibility."""
        self.anchor_date = date
        logger.info(f"Anchor date set to: {date.strftime('%Y-%m-%d')}")

