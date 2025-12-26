"""
Meta Reliability Model.

Learns when FuggerBot is trustworthy using FRS history and outcomes.
"""
from typing import Dict, Any, List, Optional
from collections import deque
import numpy as np
from sklearn.linear_model import LogisticRegression
import logging

logger = logging.getLogger(__name__)


class MetaReliabilityModel:
    """Predicts FuggerBot reliability."""

    def __init__(
        self,
        max_history: int = 500,
        reliability_threshold: float = 0.6,
        min_training_samples: int = 50
    ):
        """
        Initialize meta reliability model.

        Args:
            max_history: Maximum records to keep
            reliability_threshold: Threshold for reliable predictions
            min_training_samples: Minimum samples before training
        """
        self.max_history = max_history
        self.reliability_threshold = reliability_threshold
        self.min_training_samples = min_training_samples
        self.history = deque(maxlen=max_history)
        self.model = LogisticRegression(max_iter=1000)
        self.is_trained = False

    def add_record(
        self,
        frs_score: float,
        trust_score: float,
        volatility: float,
        drift_score: float,
        regime: str,
        outcome: int
    ) -> None:
        """
        Add historical record (labelled outcome).

        Args:
            frs_score: FuggerBot reliability score
            trust_score: Trust score (0-1)
            volatility: Market volatility
            drift_score: Drift detection score
            regime: Regime type
            outcome: 1 if forecast was accurate, 0 otherwise
        """
        regime_features = self._encode_regime(regime)
        record = {
            "features": [
                frs_score,
                trust_score,
                volatility,
                drift_score,
                *regime_features
            ],
            "outcome": outcome
        }
        self.history.append(record)

    def train(self) -> bool:
        """Train meta model if enough data."""
        if len(self.history) < self.min_training_samples:
            logger.info("Not enough data to train meta reliability model")
            return False

        X = np.array([rec["features"] for rec in self.history])
        y = np.array([rec["outcome"] for rec in self.history])

        try:
            self.model.fit(X, y)
            self.is_trained = True
            logger.info("Meta reliability model trained successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to train meta reliability model: {e}", exc_info=True)
            self.is_trained = False
            return False

    def predict_reliability(
        self,
        frs_score: float,
        trust_score: float,
        volatility: float,
        drift_score: float,
        regime: str
    ) -> Dict[str, Any]:
        """
        Predict whether FuggerBot is reliable right now.

        Args:
            frs_score: Current FRS score
            trust_score: Trust score
            volatility: Market volatility
            drift_score: Drift score
            regime: Regime type

        Returns:
            Dict with reliability prediction
        """
        features = np.array([
            [
                frs_score,
                trust_score,
                volatility,
                drift_score,
                *self._encode_regime(regime)
            ]
        ])

        if self.is_trained:
            reliability_prob = float(self.model.predict_proba(features)[0][1])
        else:
            # Use heuristic if not trained
            reliability_prob = float(
                0.5 * frs_score + 0.3 * trust_score + 0.2 * (1 - drift_score)
            )

        is_reliable = reliability_prob >= self.reliability_threshold

        return {
            "reliability_probability": reliability_prob,
            "is_reliable": is_reliable,
            "threshold": self.reliability_threshold,
            "reliability_level": self._classify_reliability(reliability_prob),
            "model_trained": self.is_trained
        }

    def _encode_regime(self, regime: str) -> List[int]:
        """One-hot encode regime."""
        regimes = [
            "normal",
            "high_volatility",
            "low_predictability",
            "overconfidence",
            "data_quality_degradation"
        ]
        return [1 if regime == r else 0 for r in regimes]

    @staticmethod
    def _classify_reliability(prob: float) -> str:
        """Classify reliability probability."""
        if prob >= 0.8:
            return "high"
        elif prob >= 0.65:
            return "medium"
        else:
            return "low"











