"""
Drift detection for forecast quality monitoring.

Detects systematic bias, regime shifts, and calibration issues.
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from models.forecast_metadata import ForecastMetadata


class DriftDetector:
    """Detects forecast drift and quality degradation."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize drift detector.
        
        Args:
            storage_dir: Directory with forecast snapshots
        """
        self.metadata = ForecastMetadata(storage_dir)
    
    def load_recent_evaluations(
        self,
        symbol: Optional[str] = None,
        days: int = 30,
        min_samples: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Load recent forecast evaluations.
        
        Args:
            symbol: Optional symbol filter
            days: Number of days to look back
            min_samples: Minimum samples required
            
        Returns:
            List of evaluation dicts
        """
        evaluations = []
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
        
        # Load all forecast snapshots
        storage_dir = self.metadata.storage_dir
        for filepath in storage_dir.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    snapshot = json.load(f)
                
                # Filter by symbol if provided
                if symbol and snapshot.get("symbol") != symbol:
                    continue
                
                # Check date
                timestamp_str = snapshot.get("timestamp", "")
                if timestamp_str:
                    snapshot_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if snapshot_time.timestamp() < cutoff_date:
                        continue
                
                # Try to load evaluation if available
                eval_file = filepath.parent / f"eval_{filepath.stem}"
                if eval_file.exists():
                    with open(eval_file, "r") as ef:
                        eval_data = json.load(ef)
                        evaluations.append(eval_data)
            except Exception:
                continue
        
        return evaluations[:min_samples] if len(evaluations) >= min_samples else []
    
    def detect_systematic_bias(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect systematic bias (persistently optimistic or pessimistic).
        
        Args:
            evaluations: List of forecast evaluation dicts
            
        Returns:
            Dict with bias detection results
        """
        if len(evaluations) < 5:
            return {"detected": False, "reason": "Insufficient data"}
        
        errors = []
        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            mape = metrics.get("mape")
            if mape is not None:
                # Get forecast vs actual direction
                # This would need actual price data - simplified here
                errors.append(mape)
        
        if not errors:
            return {"detected": False, "reason": "No error data available"}
        
        # Check for consistent over/under-prediction
        # Positive bias = consistently over-predicting
        # Negative bias = consistently under-predicting
        mean_error = np.mean(errors)
        std_error = np.std(errors)
        
        # Significant bias if mean error > 2 standard deviations from zero
        bias_threshold = 2 * std_error
        
        if abs(mean_error) > bias_threshold:
            bias_type = "optimistic" if mean_error > 0 else "pessimistic"
            return {
                "detected": True,
                "bias_type": bias_type,
                "magnitude": abs(mean_error),
                "mean_error": mean_error,
                "severity": "high" if abs(mean_error) > 3 * std_error else "moderate"
            }
        
        return {"detected": False, "mean_error": mean_error}
    
    def detect_regime_shift(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect regime shifts (volatility expansion/contraction).
        
        Args:
            evaluations: List of forecast evaluation dicts
            
        Returns:
            Dict with regime shift detection results
        """
        if len(evaluations) < 10:
            return {"detected": False, "reason": "Insufficient data"}
        
        # Split into early and recent periods
        mid_point = len(evaluations) // 2
        early = evaluations[:mid_point]
        recent = evaluations[mid_point:]
        
        early_errors = [e.get("metrics", {}).get("mape", 0) for e in early if e.get("metrics", {}).get("mape")]
        recent_errors = [e.get("metrics", {}).get("mape", 0) for e in recent if e.get("metrics", {}).get("mape")]
        
        if len(early_errors) < 3 or len(recent_errors) < 3:
            return {"detected": False, "reason": "Insufficient error data"}
        
        early_vol = np.std(early_errors)
        recent_vol = np.std(recent_errors)
        
        if early_vol == 0:
            return {"detected": False, "reason": "No volatility in early period"}
        
        vol_ratio = recent_vol / early_vol
        
        # Regime shift if volatility changed by >50%
        if vol_ratio > 1.5:
            return {
                "detected": True,
                "shift_type": "volatility_expansion",
                "magnitude": vol_ratio,
                "early_vol": early_vol,
                "recent_vol": recent_vol
            }
        elif vol_ratio < 0.67:
            return {
                "detected": True,
                "shift_type": "volatility_contraction",
                "magnitude": vol_ratio,
                "early_vol": early_vol,
                "recent_vol": recent_vol
            }
        
        return {"detected": False, "vol_ratio": vol_ratio}
    
    def detect_calibration_issues(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect model underconfidence or overconfidence.
        
        Args:
            evaluations: List of forecast evaluation dicts
            
        Returns:
            Dict with calibration detection results
        """
        if len(evaluations) < 5:
            return {"detected": False, "reason": "Insufficient data"}
        
        coverages = []
        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            calibration = metrics.get("calibration", {})
            coverage = calibration.get("coverage")
            if coverage is not None:
                coverages.append(coverage)
        
        if not coverages:
            return {"detected": False, "reason": "No calibration data"}
        
        mean_coverage = np.mean(coverages)
        expected_coverage = 95.0  # For 95% confidence intervals
        
        coverage_error = mean_coverage - expected_coverage
        
        # Overconfident if coverage < 90% (bounds too narrow)
        # Underconfident if coverage > 98% (bounds too wide)
        if mean_coverage < 90.0:
            return {
                "detected": True,
                "issue_type": "overconfidence",
                "mean_coverage": mean_coverage,
                "expected_coverage": expected_coverage,
                "severity": "high" if mean_coverage < 85.0 else "moderate"
            }
        elif mean_coverage > 98.0:
            return {
                "detected": True,
                "issue_type": "underconfidence",
                "mean_coverage": mean_coverage,
                "expected_coverage": expected_coverage,
                "severity": "high" if mean_coverage > 99.0 else "moderate"
            }
        
        return {
            "detected": False,
            "mean_coverage": mean_coverage,
            "calibration_error": abs(coverage_error)
        }
    
    def detect_drift(
        self,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Comprehensive drift detection.
        
        Args:
            symbol: Optional symbol to analyze
            days: Number of days to analyze
            
        Returns:
            Dict with all drift detection results
        """
        evaluations = self.load_recent_evaluations(symbol, days)
        
        if not evaluations:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 14 evaluations over {days} days"
            }
        
        bias = self.detect_systematic_bias(evaluations)
        regime = self.detect_regime_shift(evaluations)
        calibration = self.detect_calibration_issues(evaluations)
        
        issues = []
        if bias.get("detected"):
            issues.append(f"Systematic {bias['bias_type']} bias detected")
        if regime.get("detected"):
            issues.append(f"Regime shift: {regime['shift_type']}")
        if calibration.get("detected"):
            issues.append(f"Calibration issue: {calibration['issue_type']}")
        
        return {
            "status": "analyzed",
            "sample_size": len(evaluations),
            "bias_detection": bias,
            "regime_detection": regime,
            "calibration_detection": calibration,
            "issues_detected": issues,
            "requires_attention": len(issues) > 0
        }











