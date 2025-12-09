"""
Trigger service for managing price triggers.

This service handles loading, saving, creating, updating, and toggling triggers.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.logger import logger


class TriggerService:
    """Service for managing triggers."""
    
    def __init__(self, trigger_file: Optional[Path] = None):
        """
        Initialize trigger service.
        
        Args:
            trigger_file: Path to triggers JSON file (defaults to dash/data/triggers.json)
        """
        if trigger_file is None:
            project_root = Path(__file__).parent.parent
            trigger_file = project_root / "dash" / "data" / "triggers.json"
        
        self.trigger_file = trigger_file
        self.trigger_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"TriggerService initialized with file: {self.trigger_file}")
    
    def load_triggers(self) -> List[Dict[str, Any]]:
        """
        Load all triggers from file.
        
        Returns:
            List of trigger dictionaries
        """
        if self.trigger_file.exists():
            try:
                with open(self.trigger_file, "r") as f:
                    triggers = json.load(f)
                    # Ensure all triggers have 'enabled' field (default True)
                    for trigger in triggers:
                        if "enabled" not in trigger:
                            trigger["enabled"] = True
                    return triggers
            except Exception as e:
                logger.error(f"Error loading triggers: {e}", exc_info=True)
                return []
        return []
    
    def save_triggers(self, triggers: List[Dict[str, Any]]) -> bool:
        """
        Save triggers to file.
        
        Args:
            triggers: List of trigger dictionaries
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self.trigger_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.trigger_file, "w") as f:
                json.dump(triggers, f, indent=2)
            logger.info(f"Saved {len(triggers)} triggers to {self.trigger_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving triggers: {e}", exc_info=True)
            return False
    
    def create_trigger(
        self,
        symbol: str,
        condition: str,
        value: float,
        action: str,
        enabled: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new trigger.
        
        Args:
            symbol: Trading symbol
            condition: Trigger condition ("<", ">", "drop_pct", "rise_pct")
            value: Trigger value/threshold
            action: Action to take ("notify", "buy", "sell", "layer_in")
            enabled: Whether trigger is enabled (default: True)
            **kwargs: Additional trigger fields (quantity, order_type, limit_price, etc.)
        
        Returns:
            Created trigger dictionary
        """
        trigger = {
            "symbol": symbol.upper().strip(),
            "condition": condition,
            "value": float(value),
            "price": float(value),  # For backward compatibility
            "action": action,
            "enabled": enabled,
            **kwargs
        }
        
        triggers = self.load_triggers()
        triggers.append(trigger)
        
        if self.save_triggers(triggers):
            logger.info(f"Created trigger: {symbol} {condition} {value} → {action}")
            return trigger
        else:
            raise ValueError("Failed to save trigger")
    
    def delete_trigger(self, trigger_id: int) -> bool:
        """
        Delete a trigger by index.
        
        Args:
            trigger_id: Index of trigger to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        triggers = self.load_triggers()
        
        if 0 <= trigger_id < len(triggers):
            deleted = triggers.pop(trigger_id)
            if self.save_triggers(triggers):
                logger.info(f"Deleted trigger: {deleted.get('symbol')} {deleted.get('condition')} {deleted.get('value')}")
                return True
        
        return False
    
    def toggle_trigger(self, trigger_id: int) -> Optional[Dict[str, Any]]:
        """
        Toggle enable/disable status of a trigger.
        
        Args:
            trigger_id: Index of trigger to toggle
        
        Returns:
            Updated trigger dictionary if successful, None otherwise
        """
        triggers = self.load_triggers()
        
        if 0 <= trigger_id < len(triggers):
            trigger = triggers[trigger_id]
            trigger["enabled"] = not trigger.get("enabled", True)
            
            if self.save_triggers(triggers):
                status = "enabled" if trigger["enabled"] else "disabled"
                logger.info(f"Toggled trigger {trigger_id} ({status}): {trigger.get('symbol')}")
                return trigger
        
        return None
    
    def update_trigger(
        self,
        trigger_id: int,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update a trigger's fields.
        
        Args:
            trigger_id: Index of trigger to update
            **updates: Fields to update (symbol, condition, value, action, etc.)
        
        Returns:
            Updated trigger dictionary if successful, None otherwise
        """
        triggers = self.load_triggers()
        
        if 0 <= trigger_id < len(triggers):
            trigger = triggers[trigger_id]
            trigger.update(updates)
            
            # Ensure value and price are synced
            if "value" in updates:
                trigger["price"] = updates["value"]
            elif "price" in updates:
                trigger["value"] = updates["price"]
            
            if self.save_triggers(triggers):
                logger.info(f"Updated trigger {trigger_id}: {trigger.get('symbol')}")
                return trigger
        
        return None
    
    def get_last_fired_timestamp(self, trigger: Dict[str, Any]) -> Optional[str]:
        """
        Get the last fired timestamp for a trigger from the database.
        
        Args:
            trigger: Trigger dictionary
        
        Returns:
            ISO format timestamp string or None if never fired
        """
        try:
            from persistence.db import SessionLocal
            from persistence.models_triggers import TriggerEvent
            from sqlalchemy import desc
            
            symbol = trigger.get("symbol", "").upper()
            condition = trigger.get("condition")
            threshold_value = trigger.get("value", trigger.get("price", 0))
            
            with SessionLocal() as session:
                event = (
                    session.query(TriggerEvent)
                    .filter(
                        TriggerEvent.symbol == symbol,
                        TriggerEvent.condition == condition,
                        TriggerEvent.threshold_value == threshold_value
                    )
                    .order_by(desc(TriggerEvent.fired_at))
                    .first()
                )
                
                if event:
                    return event.fired_at.isoformat()
                return None
        except Exception as e:
            logger.error(f"Error getting last fired timestamp: {e}", exc_info=True)
            return None


# Global service instance
_trigger_service: Optional[TriggerService] = None


def get_trigger_service() -> TriggerService:
    """
    Get or create global trigger service instance.
    
    Returns:
        TriggerService instance
    """
    global _trigger_service
    if _trigger_service is None:
        _trigger_service = TriggerService()
    return _trigger_service

