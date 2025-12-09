"""
Trade memory management for reasoning system.

Manages JSON-based trade history with regret tracking and performance analysis.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4

from reasoning.schemas import ReasoningDecision, TradeContext, DeepSeekResponse

logger = logging.getLogger(__name__)


class TradeMemory:
    """Manages trade history and performance tracking for reasoning system."""
    
    def __init__(self, memory_file: Optional[Path] = None):
        """
        Initialize trade memory.
        
        Args:
            memory_file: Path to JSON file for trade history (defaults to data/trade_memory.json)
        """
        if memory_file is None:
            project_root = Path(__file__).parent.parent
            memory_file = project_root / "data" / "trade_memory.json"
        
        self.memory_file = memory_file
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing memory
        self._memory = self._load_memory()
        logger.info(f"TradeMemory initialized with {len(self._memory.get('trades', []))} existing trades")
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load trade memory from JSON file."""
        if not self.memory_file.exists():
            return {
                "trades": [],
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            with open(self.memory_file, "r") as f:
                data = json.load(f)
                # Ensure trades list exists
                if "trades" not in data:
                    data["trades"] = []
                return data
        except Exception as e:
            logger.error(f"Error loading trade memory from {self.memory_file}: {e}", exc_info=True)
            return {
                "trades": [],
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_memory(self) -> None:
        """Save trade memory to JSON file."""
        try:
            self._memory["last_updated"] = datetime.now().isoformat()
            # Write to temporary file first, then rename (atomic write)
            temp_file = self.memory_file.with_suffix('.json.tmp')
            with open(temp_file, "w") as f:
                json.dump(self._memory, f, indent=2)
            # Atomic rename
            temp_file.replace(self.memory_file)
        except Exception as e:
            logger.error(f"Error saving trade memory to {self.memory_file}: {e}", exc_info=True)
            # Try to clean up temp file
            temp_file = self.memory_file.with_suffix('.json.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            raise
    
    def add_trade(
        self,
        context: TradeContext,
        response: DeepSeekResponse,
        trade_id: Optional[str] = None
    ) -> str:
        """
        Log a trade decision with context and LLM response.
        
        Args:
            context: TradeContext with trade information
            response: DeepSeekResponse with LLM decision and rationale
            trade_id: Optional trade ID (generated if not provided)
        
        Returns:
            Trade ID string
        """
        if trade_id is None:
            trade_id = str(uuid4())
        
        trade_record = {
            "trade_id": trade_id,
            "timestamp": datetime.now().isoformat(),
            "symbol": context.symbol,
            "price": context.price,
            "forecast_target": context.forecast_target,
            "forecast_confidence": context.forecast_confidence,
            "trust_score": context.trust_score,
            "volatility_metrics": context.volatility_metrics,
            "memory_summary": context.memory_summary,
            "decision": response.decision.value,
            "confidence": response.confidence,
            "risk_analysis": response.risk_analysis,
            "rationale": response.rationale,
            "outcome": None,  # Will be updated later
            "pnl": None,  # Will be updated later
            "regret": None  # Will be calculated when outcome is known
        }
        
        self._memory["trades"].append(trade_record)
        self._save_memory()
        
        logger.info(
            f"Trade logged: {trade_id} - {context.symbol} - "
            f"Decision: {response.decision.value} (confidence: {response.confidence:.2f})"
        )
        
        return trade_id
    
    def update_outcome(self, trade_id: str, pnl: float) -> bool:
        """
        Update trade with actual market outcome.
        
        Args:
            trade_id: Trade ID to update
            pnl: Profit and Loss (positive = profit, negative = loss)
        
        Returns:
            True if trade was found and updated, False otherwise
        
        Logic:
            - If decision was REJECTED but PnL was positive, mark as 'MISSED_OP' (Regret)
        """
        for trade in self._memory["trades"]:
            if trade["trade_id"] == trade_id:
                trade["outcome"] = "PROFIT" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
                trade["pnl"] = pnl
                
                # Regret logic: If we REJECTED but PnL was positive, mark as regret
                if trade["decision"] == ReasoningDecision.REJECT.value and pnl > 0:
                    trade["regret"] = "MISSED_OP"
                    logger.warning(
                        f"Regret detected: Trade {trade_id} was REJECTED but would have been profitable (PnL: {pnl:.2f})"
                    )
                elif trade["decision"] == ReasoningDecision.APPROVE.value:
                    # Approved trades: mark regret if we lost money
                    if pnl < 0:
                        trade["regret"] = "BAD_APPROVAL"
                    else:
                        trade["regret"] = None
                else:
                    # WAIT decisions or others
                    trade["regret"] = None
                
                self._save_memory()
                logger.info(f"Trade outcome updated: {trade_id} - {trade['outcome']} (PnL: {pnl:.2f})")
                return True
        
        logger.warning(f"Trade ID {trade_id} not found in memory")
        return False
    
    def get_summary(self, symbol: Optional[str] = None) -> str:
        """
        Get performance summary for symbol (or all trades if symbol is None).
        
        Calculates:
        - Weighted Win Rate (recent trades count 2x)
        - Regret Rate (% of rejections that would have won)
        
        Returns:
            Text summary string with warnings if Regret is high or Win Rate is low
        """
        trades = self._memory.get("trades", [])
        
        # Filter by symbol if provided
        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]
        
        if not trades:
            return f"No trade history found{' for ' + symbol if symbol else ''}."
        
        # Separate trades by decision type
        approved_trades = [t for t in trades if t.get("decision") == ReasoningDecision.APPROVE.value]
        rejected_trades = [t for t in trades if t.get("decision") == ReasoningDecision.REJECT.value]
        
        # Calculate Weighted Win Rate (recent trades count 2x)
        # Sort by timestamp (most recent first)
        sorted_trades = sorted(
            approved_trades,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        total_weight = 0
        weighted_wins = 0
        
        for i, trade in enumerate(sorted_trades):
            if trade.get("outcome") is None:
                continue  # Skip trades without outcomes
            
            # Recent trades (first half) get 2x weight
            weight = 2.0 if i < len(sorted_trades) / 2 else 1.0
            total_weight += weight
            
            if trade.get("outcome") == "PROFIT":
                weighted_wins += weight
        
        weighted_win_rate = (weighted_wins / total_weight * 100) if total_weight > 0 else 0.0
        
        # Calculate Regret Rate (% of rejections that would have won)
        rejected_with_outcome = [t for t in rejected_trades if t.get("outcome") is not None]
        regretted_rejections = [t for t in rejected_with_outcome if t.get("regret") == "MISSED_OP"]
        
        regret_rate = (
            (len(regretted_rejections) / len(rejected_with_outcome) * 100)
            if rejected_with_outcome else 0.0
        )
        
        # Build summary
        summary_parts = []
        summary_parts.append(f"Trade Performance Summary{' for ' + symbol if symbol else ''}:")
        summary_parts.append("")
        summary_parts.append(f"Total Trades: {len(trades)}")
        summary_parts.append(f"  - Approved: {len(approved_trades)}")
        summary_parts.append(f"  - Rejected: {len(rejected_trades)}")
        summary_parts.append("")
        
        if total_weight > 0:
            summary_parts.append(f"Weighted Win Rate: {weighted_win_rate:.1f}%")
            summary_parts.append(f"  (Recent trades weighted 2x)")
        else:
            summary_parts.append("Weighted Win Rate: N/A (no completed approved trades)")
        
        summary_parts.append("")
        
        if rejected_with_outcome:
            summary_parts.append(f"Regret Rate: {regret_rate:.1f}%")
            summary_parts.append(f"  ({len(regretted_rejections)} missed opportunities out of {len(rejected_with_outcome)} rejections)")
        else:
            summary_parts.append("Regret Rate: N/A (no completed rejected trades)")
        
        summary_parts.append("")
        summary_parts.append("Recommendations:")
        
        # Generate warnings
        warnings = []
        
        if regret_rate > 30:
            warnings.append(
                f"⚠️ HIGH REGRET RATE ({regret_rate:.1f}%): "
                "You are being too conservative. Many rejected trades would have been profitable. "
                "Consider being less risk-averse."
            )
        elif regret_rate > 15:
            warnings.append(
                f"⚠️ Moderate Regret Rate ({regret_rate:.1f}%): "
                "Some missed opportunities detected. Consider slightly reducing conservatism."
            )
        
        if total_weight > 0:
            if weighted_win_rate < 50:
                warnings.append(
                    f"⚠️ LOW WIN RATE ({weighted_win_rate:.1f}%): "
                    "Approved trades are underperforming. Be more skeptical of trade signals. "
                    "Increase confidence thresholds or improve signal quality."
                )
            elif weighted_win_rate < 60:
                warnings.append(
                    f"⚠️ Moderate Win Rate ({weighted_win_rate:.1f}%): "
                    "Win rate could be improved. Consider tightening approval criteria."
                )
        
        if warnings:
            for warning in warnings:
                summary_parts.append(warning)
        else:
            summary_parts.append("✅ Performance metrics are within acceptable ranges.")
        
        return "\n".join(summary_parts)
    
    def get_trades_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all trades for a specific symbol."""
        return [t for t in self._memory.get("trades", []) if t.get("symbol") == symbol]
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent trades."""
        trades = sorted(
            self._memory.get("trades", []),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        return trades[:limit]

