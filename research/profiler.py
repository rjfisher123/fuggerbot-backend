"""
Symbol performance profiler.

Analyzes `data/trade_memory.json` to generate performance profiles per symbol.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SymbolProfiler:
    """
    Builds performance profiles for symbols based on trade_memory.json.
    """

    def __init__(self, memory_path: Optional[Path] = None):
        """
        Args:
            memory_path: Optional custom path to trade memory JSON.
        """
        if memory_path is None:
            memory_path = Path("data/trade_memory.json")
        self.memory_path = Path(memory_path)

    def generate_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate performance profiles for each symbol.

        Returns:
            Dictionary keyed by symbol with metrics:
                - total_signals: int
                - hit_rate: float (0-1)
                - regret_rate: float (0-1)
                - avg_confidence: float
                - volatility_regime: float
        """
        trades = self._load_trades()
        if not trades:
            return {}

        by_symbol: Dict[str, List[Dict[str, Any]]] = {}
        for trade in trades:
            symbol = trade.get("symbol")
            if not symbol:
                continue
            by_symbol.setdefault(symbol, []).append(trade)

        profiles: Dict[str, Dict[str, Any]] = {}

        for symbol, sym_trades in by_symbol.items():
            total_signals = len(sym_trades)

            # Approvals and rejections
            approvals = [t for t in sym_trades if t.get("decision") == "APPROVE"]
            rejections = [t for t in sym_trades if t.get("decision") == "REJECT"]

            # Hit rate: approved trades with positive PnL
            approved_with_pnl = [t for t in approvals if self._is_number(t.get("pnl"))]
            approved_wins = [t for t in approved_with_pnl if t.get("pnl", 0) > 0]
            hit_rate = (len(approved_wins) / len(approved_with_pnl)) if approved_with_pnl else 0.0

            # Regret rate: rejected trades that would have been profitable
            rejected_with_pnl = [t for t in rejections if self._is_number(t.get("pnl"))]
            rejected_wins = [t for t in rejected_with_pnl if t.get("pnl", 0) > 0]
            regret_rate = (len(rejected_wins) / len(rejected_with_pnl)) if rejected_with_pnl else 0.0

            # Average confidence across all trades (where available)
            confidences = [t.get("confidence") for t in sym_trades if self._is_number(t.get("confidence"))]
            avg_confidence = self._safe_mean(confidences)

            # Average volatility (volatility_metrics.volatility)
            vols = []
            for t in sym_trades:
                vm = t.get("volatility_metrics") or {}
                v = vm.get("volatility")
                if self._is_number(v):
                    vols.append(v)
            volatility_regime = self._safe_mean(vols)

            profiles[symbol] = {
                "total_signals": total_signals,
                "hit_rate": hit_rate,
                "regret_rate": regret_rate,
                "avg_confidence": avg_confidence,
                "volatility_regime": volatility_regime,
            }

        return profiles

    def _load_trades(self) -> List[Dict[str, Any]]:
        if not self.memory_path.exists():
            logger.warning(f"Trade memory not found at {self.memory_path}")
            return []
        try:
            with open(self.memory_path, "r") as f:
                data = json.load(f)
            trades = data.get("trades", [])
            if not isinstance(trades, list):
                logger.warning("Trade memory format unexpected (trades not a list)")
                return []
            return trades
        except Exception as e:
            logger.error(f"Failed to load trade memory: {e}")
            return []

    @staticmethod
    def _safe_mean(values: List[float]) -> float:
        if not values:
            return 0.0
        return float(sum(values) / len(values))

    @staticmethod
    def _is_number(val: Any) -> bool:
        try:
            float(val)
            return True
        except (TypeError, ValueError):
            return False








