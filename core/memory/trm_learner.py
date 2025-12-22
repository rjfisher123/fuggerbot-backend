"""
TRM Learner Agent

Responsible for storing and retrieving regime-aware trade outcomes and "regret".
Used to tune hyperparameters in hindsight based on "what if" analysis vs actual outcomes.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

class TRMLearnerAgent:
    """
    Learns from Trade/Regime/Memory (TRM) triplets.
    Stores episodic memory of:
    - Forecast (Signal)
    - Regime (Context)
    - Decision (Action)
    - Outcome (Reward)
    - Regret (Counterfactual Reward)
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent / "data"
        else:
            self.data_dir = data_dir
            
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.data_dir / "trm_memory.jsonl"
        self._cache = []
        self._load_memory()
        
    def _load_memory(self):
        """Load memory from JSONL file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    for line in f:
                        if line.strip():
                            self._cache.append(json.loads(line))
                logger.info(f"TRMLearner loaded {len(self._cache)} episodes.")
            except Exception as e:
                logger.error(f"Failed to load TRM memory: {e}")
                
    def record_episode(self, 
                      forecast: float,
                      confidence: float,
                      regime: str,
                      decision: str,
                      outcome: str,
                      pnl: float,
                      meta: Dict[str, Any] = None):
        """
        Record a completed trade episode.
        
        Args:
            forecast: The raw signal strength (0.0 to 1.0)
            confidence: The model's confidence
            regime: Market regime label (e.g. "BULL_TREND", "HIGH_VOL")
            decision: "APPROVE", "REJECT", "VETO"
            outcome: "PROFIT", "LOSS", "FLAT"
            pnl: Realized PnL
            meta: Additional metadata (e.g. specific inhibitors triggered)
        """
        episode = {
            "timestamp": datetime.now().isoformat(),
            "forecast": forecast,
            "confidence": confidence,
            "regime": regime,
            "decision": decision,
            "outcome": outcome,
            "pnl": pnl,
            "meta": meta or {}
        }
        
        # Calculate Regret (Simple heuristic for now)
        # Regret = Opportunity Cost or Realized Loss
        regret = 0.0
        if decision == "REJECT" and pnl > 0: 
            # Missed Opportunity (Hypothetical PnL if we had taken it)
            # note: caller needs to provide hypothetical PnL for rejected trades if known
            regret = pnl 
        elif decision == "APPROVE" and pnl < 0:
            # Bad Trade
            regret = abs(pnl)
            
        episode["regret"] = regret
        
        self._cache.append(episode)
        self._append_to_file(episode)
        
    def _append_to_file(self, episode: Dict):
        """Append single episode to JSONL."""
        try:
            with open(self.memory_file, "a") as f:
                f.write(json.dumps(episode) + "\n")
        except Exception as e:
            logger.error(f"Failed to save TRM episode: {e}")

    def get_regime_stats(self, regime: str) -> Dict:
        """Get success stats for a specific regime."""
        relevant = [e for e in self._cache if e["regime"] == regime]
        if not relevant:
            return {"count": 0, "win_rate": 0.0, "avg_regret": 0.0}
            
        wins = sum(1 for e in relevant if e["outcome"] == "PROFIT")
        total_pnl = sum(e.get("pnl", 0) for e in relevant)
        total_regret = sum(e.get("regret", 0) for e in relevant)
        
        return {
            "count": len(relevant),
            "win_rate": wins / len(relevant),
            "avg_pnl": total_pnl / len(relevant),
            "avg_regret": total_regret / len(relevant)
        }

    def predict_tuning(self, current_regime: str) -> Dict[str, float]:
        """
        Recommend parameter adjustments based on history.
        Very basic implementation: 
        - If high regret in this regime, suggest tighter confidence.
        - If high missed opportunity, suggest looser confidence.
        """
        stats = self.get_regime_stats(current_regime)
        if stats["count"] < 10:
            return {} # Not enough data
            
        recommendation = {}
        
        # Analyze failures
        failures = [e for e in self._cache 
                   if e["regime"] == current_regime and e["outcome"] == "LOSS" and e["decision"] == "APPROVE"]
        
        if failures:
            avg_fail_conf = np.mean([f["confidence"] for f in failures])
            recommendation["min_confidence_suggestion"] = float(avg_fail_conf * 1.05) # Suggest raising bar slightly
            
        return recommendation
