"""
Cross-Asset Coherence Engine.

Compares symbol signals against parent indices, sectors, and macro indicators.
"""
import numpy as np
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class CrossAssetCoherence:
    """Analyzes cross-asset coherence for signal validation."""
    
    def __init__(self):
        """Initialize cross-asset coherence analyzer."""
        # Mapping of symbols to parent indices/sectors
        self.symbol_to_index = {
            # Tech stocks → QQQ
            "AAPL": "QQQ", "MSFT": "QQQ", "GOOGL": "QQQ", "AMZN": "QQQ",
            "META": "QQQ", "NVDA": "QQQ", "TSLA": "QQQ",
            # General → SPY
            "SPY": "SPY", "DIA": "DIA", "IWM": "IWM"
        }
        
        # Sector ETFs
        self.sector_etfs = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLE": "Energy",
            "XLV": "Healthcare",
            "XLI": "Industrial",
            "XLP": "Consumer Staples",
            "XLY": "Consumer Discretionary",
            "XLB": "Materials",
            "XLU": "Utilities",
            "XLRE": "Real Estate",
            "XLC": "Communication"
        }
    
    def get_parent_index(self, symbol: str) -> Optional[str]:
        """
        Get parent index for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Parent index symbol or None
        """
        return self.symbol_to_index.get(symbol.upper())
    
    def get_sector(self, symbol: str) -> Optional[str]:
        """
        Get sector ETF for a symbol (simplified - would use actual mapping in production).
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Sector ETF symbol or None
        """
        # Simplified mapping - in production, use actual sector data
        tech_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"]
        if symbol.upper() in tech_symbols:
            return "XLK"
        return None
    
    def check_coherence(
        self,
        symbol: str,
        symbol_regime: str,
        symbol_action: str,
        symbol_expected_return: float,
        parent_index_regime: Optional[str] = None,
        parent_index_action: Optional[str] = None,
        vix_level: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check coherence between symbol signal and parent index/macro conditions.
        
        Args:
            symbol: Trading symbol
            symbol_regime: Symbol's regime classification
            symbol_action: Symbol's recommended action (BUY/SELL/HOLD)
            symbol_expected_return: Symbol's expected return
            parent_index_regime: Optional parent index regime
            parent_index_action: Optional parent index action
            vix_level: Optional VIX level (volatility indicator)
            
        Returns:
            Dict with coherence analysis
        """
        coherence_score = 1.0
        warnings = []
        penalties = []
        
        # Check parent index alignment
        parent_index = self.get_parent_index(symbol)
        if parent_index and parent_index_regime and parent_index_action:
            # Check regime alignment
            if symbol_regime == "normal" and parent_index_regime != "normal":
                coherence_score -= 0.2
                warnings.append(f"Symbol in normal regime but {parent_index} in {parent_index_regime}")
            
            # Check action alignment
            if symbol_action == "BUY" and parent_index_action == "SELL":
                coherence_score -= 0.3
                penalties.append("BUY signal contradicts parent index SELL signal")
            elif symbol_action == "SELL" and parent_index_action == "BUY":
                coherence_score -= 0.3
                penalties.append("SELL signal contradicts parent index BUY signal")
        
        # Check VIX alignment
        if vix_level is not None:
            if vix_level > 30:  # High volatility
                if symbol_regime == "normal":
                    coherence_score -= 0.15
                    warnings.append("High VIX but symbol in normal regime - may indicate regime shift")
            elif vix_level < 15:  # Low volatility
                if symbol_regime == "high_volatility":
                    coherence_score -= 0.15
                    warnings.append("Low VIX but symbol in high volatility regime")
        
        # Check sector alignment
        sector_etf = self.get_sector(symbol)
        if sector_etf:
            # Would check sector ETF regime/action if available
            pass
        
        # Ensure coherence score in [0, 1]
        coherence_score = max(0.0, min(1.0, coherence_score))
        
        # Classify coherence
        if coherence_score >= 0.8:
            coherence_level = "high"
        elif coherence_score >= 0.6:
            coherence_level = "moderate"
        else:
            coherence_level = "low"
        
        return {
            "coherence_score": float(coherence_score),
            "coherence_level": coherence_level,
            "warnings": warnings,
            "penalties": penalties,
            "is_coherent": coherence_score >= 0.7,
            "parent_index": parent_index,
            "sector_etf": sector_etf
        }
    
    def analyze_symbol_with_context(
        self,
        symbol: str,
        symbol_forecast: Dict[str, Any],
        parent_index_data: Optional[Dict[str, Any]] = None,
        vix_data: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive coherence analysis for a symbol.
        
        Args:
            symbol: Trading symbol
            symbol_forecast: Symbol forecast data (regime, action, expected_return)
            parent_index_data: Optional parent index forecast data
            vix_data: Optional VIX level
            
        Returns:
            Complete coherence analysis
        """
        symbol_regime = symbol_forecast.get("regime", {}).get("regime", "normal")
        symbol_action = symbol_forecast.get("recommendation", {}).get("action", "HOLD")
        symbol_expected_return = symbol_forecast.get("recommendation", {}).get("expected_return_pct", 0)
        
        parent_index_regime = None
        parent_index_action = None
        if parent_index_data:
            parent_index_regime = parent_index_data.get("regime", {}).get("regime")
            parent_index_action = parent_index_data.get("recommendation", {}).get("action")
        
        coherence = self.check_coherence(
            symbol=symbol,
            symbol_regime=symbol_regime,
            symbol_action=symbol_action,
            symbol_expected_return=symbol_expected_return,
            parent_index_regime=parent_index_regime,
            parent_index_action=parent_index_action,
            vix_level=vix_data
        )
        
        # Adjust confidence based on coherence
        base_confidence = symbol_forecast.get("trust_evaluation", {}).metrics.confidence_level
        if not coherence["is_coherent"]:
            # Downgrade confidence
            if base_confidence == "high":
                adjusted_confidence = "medium"
            elif base_confidence == "medium":
                adjusted_confidence = "low"
            else:
                adjusted_confidence = "low"
        else:
            adjusted_confidence = base_confidence
        
        return {
            **coherence,
            "base_confidence": base_confidence,
            "adjusted_confidence": adjusted_confidence,
            "confidence_downgraded": adjusted_confidence != base_confidence
        }




