"""
Trigger evaluator worker.

Runs periodically to evaluate enabled triggers and emit events.
"""
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.trigger_service import get_trigger_service
from dash.utils.price_feed import get_price
from persistence.db import SessionLocal
from persistence.models_triggers import TriggerEvent
from persistence.repositories_triggers import TriggerResultRepository, TradeCandidateRepository
from core.logger import logger
from core.logging import log_trigger_fire
from core.alert_router import get_alert_router


class TriggerEvaluator:
    """Evaluates triggers and emits events."""
    
    def __init__(self, interval_seconds: int = 60):
        """
        Initialize trigger evaluator.
        
        Args:
            interval_seconds: How often to evaluate triggers (default: 60 seconds)
        """
        self.interval_seconds = interval_seconds
        self.trigger_service = get_trigger_service()
        self.alert_router = get_alert_router()
        self.running = False
        logger.info(f"TriggerEvaluator initialized with {interval_seconds}s interval")
    
    def evaluate_condition(
        self,
        condition: str,
        current_price: float,
        threshold_value: float,
        previous_price: Optional[float] = None
    ) -> bool:
        """
        Evaluate a trigger condition.
        
        Args:
            condition: Condition type ("<", ">", "drop_pct", "rise_pct")
            current_price: Current market price
            threshold_value: Threshold value for the condition
            previous_price: Previous price (for percentage-based conditions)
        
        Returns:
            True if condition is met, False otherwise
        """
        if condition == "<":
            return current_price < threshold_value
        elif condition == ">":
            return current_price > threshold_value
        elif condition == "drop_pct":
            if previous_price is None or previous_price == 0:
                return False
            drop_pct = ((previous_price - current_price) / previous_price) * 100
            return drop_pct >= threshold_value
        elif condition == "rise_pct":
            if previous_price is None or previous_price == 0:
                return False
            rise_pct = ((current_price - previous_price) / previous_price) * 100
            return rise_pct >= threshold_value
        else:
            logger.warning(f"Unknown condition type: {condition}")
            return False
    
    def get_previous_price(self, symbol: str) -> Optional[float]:
        """
        Get previous price for a symbol (from last evaluation or cache).
        
        For now, this is a simple implementation. In production, you might
        want to cache prices or fetch historical data.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Previous price or None if not available
        """
        # TODO: Implement price caching/history
        # For now, return None (percentage-based triggers won't work on first run)
        return None
    
    def record_trigger_event(
        self,
        trigger: Dict[str, Any],
        current_price: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TriggerEvent:
        """
        Record a trigger event in the database.
        
        Args:
            trigger: Trigger dictionary
            current_price: Current price when trigger fired
            metadata: Additional metadata
        
        Returns:
            Created TriggerEvent
        """
        with SessionLocal() as session:
            event = TriggerEvent(
                trigger_id=trigger.get("id", "UNKNOWN"),
                symbol=trigger["symbol"],
                condition=trigger["condition"],
                threshold_value=trigger.get("value", trigger.get("price", 0)),
                action=trigger["action"],
                current_price=current_price,
                timestamp=datetime.utcnow(),
                event_metadata=json.dumps(metadata) if metadata else None
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            logger.info(f"Recorded trigger event: {trigger['symbol']} {trigger['condition']} {current_price}")
            return event
    
    def save_trigger_result(
        self,
        trigger: Dict[str, Any],
        current_price: float,
        previous_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        Save a TriggerResult and generate TradeCandidate rows.
        
        Args:
            trigger: Trigger dictionary
            current_price: Current price when trigger fired
            previous_price: Previous price (if available)
            metadata: Additional metadata
        
        Returns:
            Tuple of (TriggerResult, List[TradeCandidate])
        """
        trigger_id = trigger.get("id", f"trigger_{trigger['symbol']}_{trigger['condition']}")
        
        # Create data snapshot
        data_snapshot = {
            "symbol": trigger["symbol"],
            "condition": trigger["condition"],
            "threshold_value": trigger.get("value", trigger.get("price", 0)),
            "action": trigger["action"],
            "current_price": current_price,
            "previous_price": previous_price,
            "trigger_id": trigger_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            data_snapshot.update(metadata)
        
        with SessionLocal() as session:
            result_repo = TriggerResultRepository(session)
            candidate_repo = TradeCandidateRepository(session)
            
            # Save TriggerResult
            trigger_result = result_repo.add_result(
                trigger_id=trigger_id,
                data_snapshot=data_snapshot
            )
            logger.info(f"Saved TriggerResult id={trigger_result.id} for trigger_id={trigger_id}")
            
            # Generate TradeCandidate based on trigger action
            candidates = []
            action = trigger.get("action", "").upper()
            
            # Map trigger actions to trade actions
            if action in ["BUY", "buy"]:
                trade_action = "BUY"
                confidence = 0.75  # Default confidence for buy triggers
            elif action in ["SELL", "sell"]:
                trade_action = "SELL"
                confidence = 0.75  # Default confidence for sell triggers
            elif action in ["LAYER_IN", "layer_in"]:
                trade_action = "BUY"
                confidence = 0.60  # Lower confidence for layer-in
            else:
                # For "notify" or other actions, generate a HOLD candidate
                trade_action = "HOLD"
                confidence = 0.50
            
            # Adjust confidence based on price movement
            if previous_price and previous_price > 0:
                price_change_pct = abs((current_price - previous_price) / previous_price) * 100
                # Higher price movement = higher confidence
                if price_change_pct > 5:
                    confidence = min(confidence + 0.15, 0.95)
                elif price_change_pct > 2:
                    confidence = min(confidence + 0.10, 0.90)
            
            # Create trade candidate
            candidate = candidate_repo.add_candidate(
                trigger_result_id=trigger_result.id,
                trigger_id=trigger_id,
                symbol=trigger["symbol"],
                action=trade_action,
                confidence=confidence,
                metadata={
                    "trigger_action": trigger.get("action"),
                    "condition": trigger["condition"],
                    "threshold_value": trigger.get("value", trigger.get("price", 0)),
                    "current_price": current_price,
                    "previous_price": previous_price,
                    "price_change_pct": ((current_price - previous_price) / previous_price * 100) if previous_price else None
                }
            )
            candidates.append(candidate)
            logger.info(f"Generated TradeCandidate id={candidate.id}: {candidate.symbol} {candidate.action} (confidence={candidate.confidence:.2f})")
            
            return trigger_result, candidates
    
    def send_alert(self, trigger: Dict[str, Any], current_price: float, event: TriggerEvent):
        """
        Send alert for triggered event.
        
        Args:
            trigger: Trigger dictionary
            current_price: Current price
            event: TriggerEvent that was created
        """
        try:
            message = (
                f"🚨 Trigger Fired: {trigger['symbol']}\n"
                f"Condition: {trigger['condition']} {trigger.get('value', trigger.get('price', 0))}\n"
                f"Current Price: ${current_price:.2f}\n"
                f"Action: {trigger['action']}\n"
                f"Time: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            # Send via alert router (SMS/Slack/etc.)
            self.alert_router.send_alert(
                message=message,
                level="warning",
                channel="triggers"
            )
            logger.info(f"Sent alert for trigger: {trigger['symbol']}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}", exc_info=True)
    
    def evaluate_triggers(self) -> List[Dict[str, Any]]:
        """
        Evaluate all enabled triggers.
        
        Returns:
            List of triggers that fired
        """
        triggers = self.trigger_service.load_triggers()
        enabled_triggers = [t for t in triggers if t.get("enabled", True)]
        
        fired_triggers = []
        
        for trigger in enabled_triggers:
            try:
                symbol = trigger["symbol"]
                condition = trigger["condition"]
                threshold_value = trigger.get("value", trigger.get("price", 0))
                
                # Fetch current price
                current_price = get_price(symbol)
                if current_price is None:
                    logger.warning(f"Could not fetch price for {symbol}")
                    continue
                
                # Get previous price for percentage-based conditions
                previous_price = None
                if condition in ["drop_pct", "rise_pct"]:
                    previous_price = self.get_previous_price(symbol)
                
                # Evaluate condition
                if self.evaluate_condition(condition, current_price, threshold_value, previous_price):
                    logger.info(
                        f"✅ Trigger fired: {symbol} {condition} {threshold_value} "
                        f"(current: ${current_price:.2f})"
                    )
                    
                    # Log trigger fire event
                    log_trigger_fire(
                        trigger_id=trigger.get("id", f"trigger_{symbol}_{condition}"),
                        symbol=symbol,
                        condition=condition,
                        threshold=threshold_value,
                        current_price=current_price,
                        action=trigger.get("action", "notify"),
                        previous_price=previous_price
                    )
                    
                    # Record event (legacy TriggerEvent)
                    event = self.record_trigger_event(
                        trigger=trigger,
                        current_price=current_price,
                        metadata={
                            "previous_price": previous_price,
                            "threshold_value": threshold_value
                        }
                    )
                    
                    # Save TriggerResult and generate TradeCandidate
                    try:
                        trigger_result, candidates = self.save_trigger_result(
                            trigger=trigger,
                            current_price=current_price,
                            previous_price=previous_price,
                            metadata={
                                "previous_price": previous_price,
                                "threshold_value": threshold_value,
                                "event_id": event.id
                            }
                        )
                        logger.info(f"Saved TriggerResult and {len(candidates)} TradeCandidate(s)")
                    except Exception as e:
                        logger.error(f"Error saving TriggerResult/TradeCandidate: {e}", exc_info=True)
                        trigger_result = None
                        candidates = []
                    
                    # Send alert
                    if trigger["action"] == "notify" or trigger.get("send_alert", True):
                        self.send_alert(trigger, current_price, event)
                    
                    fired_triggers.append({
                        "trigger": trigger,
                        "event": event,
                        "trigger_result": trigger_result,
                        "candidates": candidates,
                        "current_price": current_price
                    })
                else:
                    logger.debug(
                        f"Trigger not met: {symbol} {condition} {threshold_value} "
                        f"(current: ${current_price:.2f})"
                    )
            
            except Exception as e:
                logger.error(f"Error evaluating trigger {trigger.get('symbol', 'UNKNOWN')}: {e}", exc_info=True)
        
        return fired_triggers
    
    def run_once(self) -> List[Dict[str, Any]]:
        """
        Run a single evaluation cycle.
        
        Returns:
            List of triggers that fired
        """
        logger.info("Starting trigger evaluation cycle...")
        fired = self.evaluate_triggers()
        logger.info(f"Evaluation complete. {len(fired)} trigger(s) fired.")
        return fired
    
    def run_forever(self):
        """Run the evaluator continuously."""
        self.running = True
        logger.info(f"Trigger evaluator started (interval: {self.interval_seconds}s)")
        
        try:
            while self.running:
                self.run_once()
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("Trigger evaluator stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Error in trigger evaluator: {e}", exc_info=True)
            self.running = False
    
    def stop(self):
        """Stop the evaluator."""
        self.running = False
        logger.info("Trigger evaluator stopped")


def main():
    """Main entry point for running the trigger evaluator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FuggerBot Trigger Evaluator")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Evaluation interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    evaluator = TriggerEvaluator(interval_seconds=args.interval)
    
    if args.once:
        evaluator.run_once()
    else:
        evaluator.run_forever()


if __name__ == "__main__":
    main()

