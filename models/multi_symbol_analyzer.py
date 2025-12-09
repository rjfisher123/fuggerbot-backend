"""
Multi-Symbol Comparative Analysis.

Ranks and compares forecasts across multiple symbols.
"""
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from models.forecast_trader import ForecastTrader
from models.forecast_quality import ForecastQualityScorer
from models.regime_classifier import RegimeClassifier
from models.date_anchoring import DateAnchoring
from models.stability_smoothing import StabilitySmoother

logger = logging.getLogger(__name__)


class MultiSymbolAnalyzer:
    """Analyzes and ranks multiple symbols."""
    
    def __init__(
        self,
        forecast_trader: Optional[ForecastTrader] = None,
        use_date_anchoring: bool = True,
        use_stability_smoothing: bool = True
    ):
        """
        Initialize multi-symbol analyzer.
        
        Args:
            forecast_trader: Optional ForecastTrader instance
            use_date_anchoring: Whether to use date anchoring for reproducibility
            use_stability_smoothing: Whether to apply stability smoothing
        """
        self.forecast_trader = forecast_trader or ForecastTrader()
        self.quality_scorer = ForecastQualityScorer()
        self.regime_classifier = RegimeClassifier()
        self.date_anchoring = DateAnchoring() if use_date_anchoring else None
        self.stability_smoother = StabilitySmoother() if use_stability_smoothing else None
    
    def analyze_symbols(
        self,
        symbols: List[str],
        forecast_horizon: int = 30,
        historical_period: str = "1y",
        context_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple symbols and rank opportunities.
        
        Args:
            symbols: List of symbols to analyze
            forecast_horizon: Forecast horizon
            historical_period: Historical data period
            context_length: Context window size
            
        Returns:
            Dict with ranked opportunities and analysis
        """
        from dash.utils.forecast_helper import get_historical_prices
        
        # Freeze date ranges for reproducibility
        if self.date_anchoring:
            frozen_ranges = self.date_anchoring.freeze_for_analysis(symbols, historical_period)
            logger.info(f"Date anchoring enabled - using frozen date ranges")
        
        results = {}
        
        for symbol in symbols:
            try:
                prices = get_historical_prices(symbol, period=historical_period)
                if not prices or len(prices) < 20:
                    continue
                
                result = self.forecast_trader.analyze_symbol(
                    symbol=symbol,
                    historical_prices=prices,
                    forecast_horizon=forecast_horizon,
                    context_length=context_length
                )
                
                if result.get("success") and result["trust_evaluation"].is_trusted:
                    # Calculate FQS
                    fqs = self.quality_scorer.calculate_fqs(
                        result["forecast"],
                        result["trust_evaluation"],
                        prices
                    )
                    
                    # Classify regime
                    regime = self.regime_classifier.classify_regime(
                        result["forecast"],
                        result["trust_evaluation"],
                        prices
                    )
                    
                    # Apply stability smoothing if enabled
                    if self.stability_smoother:
                        # Smooth FQS
                        smoothed_fqs_score, smoothed_category = self.stability_smoother.smooth_fqs(
                            symbol, fqs["fqs_score"], fqs["interpretation"].split(" - ")[0]
                        )
                        fqs["fqs_score"] = smoothed_fqs_score
                        fqs["interpretation"] = f"{smoothed_category} - {fqs['interpretation'].split(' - ')[1] if ' - ' in fqs['interpretation'] else 'Forecast quality'}"
                        
                        # Smooth regime
                        smoothed_regime_type = self.stability_smoother.smooth_regime(
                            symbol, regime["regime"]
                        )
                        regime["regime"] = smoothed_regime_type
                        regime["regime_label"] = self.regime_classifier._get_regime_label(smoothed_regime_type)
                        
                        # Smooth uncertainty
                        risk_pct = result.get("recommendation", {}).get("risk_pct", 0)
                        smoothed_risk = self.stability_smoother.smooth_uncertainty(symbol, risk_pct)
                        if "recommendation" in result:
                            result["recommendation"]["risk_pct"] = smoothed_risk
                    
                    results[symbol] = {
                        **result,
                        "fqs": fqs,
                        "regime": regime
                    }
            except Exception as e:
                continue
        
        # Rank opportunities
        ranked = self._rank_opportunities(results)
        
        return {
            "total_analyzed": len(symbols),
            "successful": len(results),
            "ranked_opportunities": ranked,
            "by_regime": self._group_by_regime(results)
        }
    
    def _rank_opportunities(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Rank opportunities by category with mutually exclusive classification.
        
        Priority order:
        1. High Uncertainty (highest priority - excludes from BUY/SELL)
        2. Top SELL (if not in High Uncertainty)
        3. Top BUY (if not in High Uncertainty or SELL)
        """
        high_uncertainty = []
        buy_opportunities = []
        sell_opportunities = []
        
        # First pass: Identify High Uncertainty cases (highest priority)
        for symbol, result in results.items():
            rec = result.get("recommendation", {})
            risk = rec.get("risk_pct", 0)
            fqs = result.get("fqs", {}).get("fqs_score", 0)
            regime = result.get("regime", {})
            regime_type = regime.get("regime", "normal")
            
            # High uncertainty criteria:
            # - Risk > 20% OR
            # - FQS < 0.5 OR
            # - Unstable regime (low_predictability, data_quality_degradation)
            is_high_uncertainty = (
                risk > 20.0 or 
                fqs < 0.5 or 
                regime_type in ["low_predictability", "data_quality_degradation"]
            )
            
            if is_high_uncertainty:
                entry = {
                    "symbol": symbol,
                    "action": rec.get("action", "HOLD"),
                    "expected_return_pct": rec.get("expected_return_pct", 0),
                    "risk_pct": risk,
                    "fqs_score": fqs,
                    "trust_score": result.get("trust_evaluation", {}).metrics.overall_trust_score,
                    "regime": regime.get("regime_label", "Unknown"),
                    "exclusion_reason": self._get_exclusion_reason(risk, fqs, regime_type)
                }
                high_uncertainty.append(entry)
        
        # Get symbols excluded from BUY/SELL due to high uncertainty
        excluded_symbols = {entry["symbol"] for entry in high_uncertainty}
        
        # Second pass: Classify remaining symbols into BUY/SELL
        for symbol, result in results.items():
            # Skip if already in high uncertainty
            if symbol in excluded_symbols:
                continue
            
            rec = result.get("recommendation", {})
            action = rec.get("action", "HOLD")
            expected_return = rec.get("expected_return_pct", 0)
            risk = rec.get("risk_pct", 0)
            fqs = result.get("fqs", {}).get("fqs_score", 0)
            
            entry = {
                "symbol": symbol,
                "action": action,
                "expected_return_pct": expected_return,
                "risk_pct": risk,
                "fqs_score": fqs,
                "trust_score": result.get("trust_evaluation", {}).metrics.overall_trust_score,
                "regime": result.get("regime", {}).get("regime_label", "Unknown")
            }
            
            # Classify as SELL (priority 2) or BUY (priority 3)
            if action == "SELL" and expected_return < -2.0:
                sell_opportunities.append(entry)
            elif action == "BUY" and expected_return > 2.0:
                buy_opportunities.append(entry)
        
        # Sort by expected return (descending for BUY, ascending for SELL)
        buy_opportunities.sort(key=lambda x: x["expected_return_pct"], reverse=True)
        sell_opportunities.sort(key=lambda x: x["expected_return_pct"])
        high_uncertainty.sort(key=lambda x: x["risk_pct"], reverse=True)
        
        return {
            "top_buy_opportunities": buy_opportunities[:3],
            "top_sell_opportunities": sell_opportunities[:3],
            "high_uncertainty_cases": high_uncertainty[:3]
        }
    
    @staticmethod
    def _get_exclusion_reason(risk: float, fqs: float, regime_type: str) -> str:
        """Get reason why symbol was excluded from BUY/SELL."""
        reasons = []
        if risk > 20.0:
            reasons.append(f"High risk ({risk:.1f}%)")
        if fqs < 0.5:
            reasons.append(f"Low FQS ({fqs:.2f})")
        if regime_type == "low_predictability":
            reasons.append("Low predictability regime")
        if regime_type == "data_quality_degradation":
            reasons.append("Data quality issues")
        return "; ".join(reasons) if reasons else "High uncertainty"
    
    def _group_by_regime(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group symbols by regime."""
        by_regime = {}
        for symbol, result in results.items():
            regime_label = result.get("regime", {}).get("regime_label", "Unknown")
            if regime_label not in by_regime:
                by_regime[regime_label] = []
            by_regime[regime_label].append(symbol)
        return by_regime

