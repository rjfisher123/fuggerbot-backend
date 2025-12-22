"""
Forecast metadata and reproducibility tracking.

Provides Forecast ID generation and parameter snapshot storage.
"""
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class ForecastMetadata:
    """Manages forecast metadata and reproducibility."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize forecast metadata manager.
        
        Args:
            storage_dir: Directory to store forecast snapshots (defaults to data/forecasts/)
        """
        if storage_dir is None:
            storage_dir = Path(__file__).parent.parent.parent / "data" / "forecasts"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_forecast_id(
        self,
        symbol: str,
        parameters: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate a reproducible Forecast ID from parameters.
        
        Args:
            symbol: Trading symbol
            parameters: Dict with keys: context_length, historical_period, 
                       strict_mode, min_trust_score, forecast_horizon
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Forecast ID string (hash-based)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create parameter snapshot
        snapshot = {
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "parameters": {
                "context_length": parameters.get("context_length"),
                "historical_period": parameters.get("historical_period", "1y"),
                "strict_mode": parameters.get("strict_mode", False),
                "min_trust_score": parameters.get("min_trust_score", 0.6),
                "forecast_horizon": parameters.get("forecast_horizon", 30)
            }
        }
        
        # Create hash from snapshot
        snapshot_str = json.dumps(snapshot, sort_keys=True)
        hash_obj = hashlib.sha256(snapshot_str.encode())
        forecast_id = hash_obj.hexdigest()[:16]  # 16 character ID
        
        return forecast_id
    
    def save_forecast_snapshot(
        self,
        forecast_id: str,
        symbol: str,
        parameters: Dict[str, Any],
        forecast_result: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> Path:
        """
        Save a forecast snapshot for reproducibility.
        
        Args:
            forecast_id: Forecast ID
            symbol: Trading symbol
            parameters: Forecast parameters
            forecast_result: Complete forecast result dict
            timestamp: Optional timestamp
            
        Returns:
            Path to saved snapshot file
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        snapshot = {
            "forecast_id": forecast_id,
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "parameters": parameters,
            "forecast": {
                "point_forecast": forecast_result.get("forecast", {}).point_forecast if hasattr(forecast_result.get("forecast"), "point_forecast") else None,
                "lower_bound": forecast_result.get("forecast", {}).lower_bound if hasattr(forecast_result.get("forecast"), "lower_bound") else None,
                "upper_bound": forecast_result.get("forecast", {}).upper_bound if hasattr(forecast_result.get("forecast"), "upper_bound") else None,
                "forecast_horizon": forecast_result.get("forecast", {}).forecast_horizon if hasattr(forecast_result.get("forecast"), "forecast_horizon") else None,
            },
            "trust_evaluation": {
                "overall_trust_score": forecast_result.get("trust_evaluation", {}).metrics.overall_trust_score if hasattr(forecast_result.get("trust_evaluation"), "metrics") else None,
                "confidence_level": forecast_result.get("trust_evaluation", {}).metrics.confidence_level if hasattr(forecast_result.get("trust_evaluation"), "metrics") else None,
                "is_trusted": forecast_result.get("trust_evaluation", {}).is_trusted if hasattr(forecast_result.get("trust_evaluation"), "is_trusted") else None,
            },
            "recommendation": forecast_result.get("recommendation", {})
        }
        
        # Save to file
        filename = f"{symbol}_{forecast_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.storage_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)
        
        return filepath
    
    def load_forecast_snapshot(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a forecast snapshot by ID.
        
        Args:
            forecast_id: Forecast ID to load
            
        Returns:
            Snapshot dict or None if not found
        """
        # Find file with this forecast_id
        for filepath in self.storage_dir.glob(f"*_{forecast_id}_*.json"):
            with open(filepath, "r") as f:
                return json.load(f)
        return None










