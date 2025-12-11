"""
Adaptive Parameter Loader.

Manages dynamic trading parameters backed by a JSON file.
Allows per-symbol parameter tuning and runtime updates.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_PARAMS = {
    "trust_threshold": 0.65,
    "min_confidence": 0.75
}

# Default file path
PARAMS_FILE = Path("data/adaptive_params.json")


class AdaptiveParamLoader:
    """
    Manages adaptive trading parameters with per-symbol customization.
    
    Parameters are stored in JSON format and can be updated at runtime.
    Supports symbol-specific overrides with fallback to defaults.
    """
    
    def __init__(self, params_file: Optional[Path] = None):
        """
        Initialize the adaptive parameter loader.
        
        Args:
            params_file: Path to JSON file (defaults to data/adaptive_params.json)
        """
        self.params_file = params_file if params_file is not None else PARAMS_FILE
        self.params_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize parameters
        self._params = self._load_params()
        
        logger.info(f"AdaptiveParamLoader initialized from {self.params_file}")
    
    def _load_params(self) -> Dict[str, Any]:
        """
        Load parameters from JSON file, or return defaults if file doesn't exist.
        
        Returns:
            Dictionary with parameters structure:
            {
                "defaults": {...},
                "symbols": {
                    "SYMBOL": {...}
                }
            }
        """
        if not self.params_file.exists():
            logger.info(f"Params file not found, using defaults: {self.params_file}")
            return {
                "defaults": DEFAULT_PARAMS.copy(),
                "symbols": {}
            }
        
        try:
            with open(self.params_file, 'r') as f:
                data = json.load(f)
            
            # Ensure structure is valid
            if "defaults" not in data:
                data["defaults"] = DEFAULT_PARAMS.copy()
            if "symbols" not in data:
                data["symbols"] = {}
            
            # Merge defaults to ensure all keys exist
            for key, value in DEFAULT_PARAMS.items():
                if key not in data["defaults"]:
                    data["defaults"][key] = value
            
            logger.debug(f"Loaded parameters from {self.params_file}")
            return data
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading params file: {e}, using defaults")
            return {
                "defaults": DEFAULT_PARAMS.copy(),
                "symbols": {}
            }
    
    def _save_params(self) -> bool:
        """
        Save parameters to JSON file (atomic write).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Atomic write: write to temp file first, then rename
            temp_file = self.params_file.with_suffix('.json.tmp')
            
            with open(temp_file, 'w') as f:
                json.dump(self._params, f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.params_file)
            
            logger.debug(f"Saved parameters to {self.params_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving params file: {e}")
            # Clean up temp file if it exists
            temp_file = self.params_file.with_suffix('.json.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False
    
    def get_params(self, symbol: str) -> Dict[str, Any]:
        """
        Get parameters for a specific symbol.
        
        Returns symbol-specific parameters merged with defaults.
        If symbol has no specific params, returns defaults.
        
        Args:
            symbol: Trading symbol (e.g., "BTC-USD", "NVDA")
        
        Returns:
            Dictionary with parameters for the symbol:
            {
                "trust_threshold": float,
                "min_confidence": float
            }
        """
        # Start with defaults
        params = self._params["defaults"].copy()
        
        # Override with symbol-specific params if they exist
        if symbol in self._params.get("symbols", {}):
            symbol_params = self._params["symbols"][symbol]
            params.update(symbol_params)
            logger.debug(f"Using symbol-specific params for {symbol}")
        else:
            logger.debug(f"Using default params for {symbol}")
        
        return params
    
    def update_params(self, symbol: str, new_params: Dict[str, Any]) -> bool:
        """
        Update parameters for a specific symbol.
        
        Merges new_params with existing symbol params (or creates new entry).
        Saves to JSON file.
        
        Args:
            symbol: Trading symbol to update
            new_params: Dictionary of parameters to update/merge
        
        Returns:
            True if successful, False otherwise
        """
        # Ensure symbols dict exists
        if "symbols" not in self._params:
            self._params["symbols"] = {}
        
        # Get existing params for symbol (or empty dict)
        existing = self._params["symbols"].get(symbol, {})
        
        # Merge new params with existing
        updated = {**existing, **new_params}
        
        # Validate parameter values
        if "trust_threshold" in updated:
            updated["trust_threshold"] = max(0.0, min(1.0, float(updated["trust_threshold"])))
        if "min_confidence" in updated:
            updated["min_confidence"] = max(0.0, min(1.0, float(updated["min_confidence"])))
        
        # Update in memory
        self._params["symbols"][symbol] = updated
        
        # Save to file
        success = self._save_params()
        
        if success:
            logger.info(f"Updated params for {symbol}: {updated}")
        else:
            logger.error(f"Failed to save params for {symbol}")
        
        return success
    
    def reset_to_defaults(self) -> bool:
        """
        Reset all parameters to defaults (safety hatch).
        
        Removes all symbol-specific overrides and resets defaults.
        Saves to JSON file.
        
        Returns:
            True if successful, False otherwise
        """
        logger.warning("Resetting all parameters to defaults")
        
        self._params = {
            "defaults": DEFAULT_PARAMS.copy(),
            "symbols": {}
        }
        
        success = self._save_params()
        
        if success:
            logger.info("Parameters reset to defaults")
        else:
            logger.error("Failed to save reset parameters")
        
        return success
    
    def get_all_symbols(self) -> list[str]:
        """
        Get list of all symbols that have custom parameters.
        
        Returns:
            List of symbol strings
        """
        return list(self._params.get("symbols", {}).keys())
    
    def get_defaults(self) -> Dict[str, Any]:
        """
        Get the default parameters.
        
        Returns:
            Dictionary with default parameters
        """
        return self._params.get("defaults", DEFAULT_PARAMS).copy()


