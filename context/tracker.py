"""
Regime Tracker.

Maintains state of the current macroeconomic regime and provides context for LLM prompts.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from context.schemas import MacroRegime

logger = logging.getLogger(__name__)


# Default neutral regime
NEUTRAL_REGIME = MacroRegime(
    id="NEUTRAL",
    name="Neutral Market Regime",
    summary="Baseline market conditions with no extreme characteristics",
    risk_on=True,
    vibe_score=0.5,
    timestamp=datetime.now()
)


class RegimeTracker:
    """
    Tracks the current macroeconomic regime state.
    
    Maintains a single active regime and provides methods to update it
    and generate prompt context for LLM reasoning.
    """
    
    def __init__(self, initial_regime: Optional[MacroRegime] = None):
        """
        Initialize the regime tracker.
        
        Args:
            initial_regime: Initial regime to use. Defaults to NEUTRAL_REGIME.
        """
        self.current_regime = initial_regime if initial_regime is not None else NEUTRAL_REGIME
        self.log_file = Path("data/macro_log.json")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"RegimeTracker initialized with regime: {self.current_regime.id}")
    
    def update_regime(self, new_regime: MacroRegime) -> None:
        """
        Update the current regime state and log the shift.
        
        Args:
            new_regime: The new MacroRegime to set as current
        """
        old_regime = self.current_regime
        self.current_regime = new_regime
        
        # Log the regime shift
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_regime": {
                "id": old_regime.id,
                "name": old_regime.name,
                "risk_on": old_regime.risk_on,
                "vibe_score": old_regime.vibe_score
            },
            "new_regime": {
                "id": new_regime.id,
                "name": new_regime.name,
                "risk_on": new_regime.risk_on,
                "vibe_score": new_regime.vibe_score
            }
        }
        
        # Load existing log or create new
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    log_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                log_data = {"shifts": []}
        else:
            log_data = {"shifts": []}
        
        # Ensure shifts list exists
        if "shifts" not in log_data:
            log_data["shifts"] = []
        
        # Append new shift
        log_data["shifts"].append(log_entry)
        log_data["last_updated"] = datetime.now().isoformat()
        
        # Save log
        try:
            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.info(
                f"🌍 Regime shift: {old_regime.id} -> {new_regime.id} "
                f"({old_regime.name} -> {new_regime.name})"
            )
        except Exception as e:
            logger.error(f"Failed to save regime shift log: {e}")
    
    def get_current_regime(self) -> MacroRegime:
        """
        Get the current active regime.
        
        Returns:
            MacroRegime object representing the current regime
        """
        return self.current_regime
    
    def get_prompt_context(self) -> str:
        """
        Get formatted context string for LLM prompt.
        
        Returns a concise string describing the current regime that can be
        injected into LLM prompts for trading decisions.
        
        Returns:
            Formatted string like "CURRENT REGIME: QT (Hawkish). Be conservative."
        """
        regime = self.current_regime
        
        # Build risk guidance
        if regime.risk_on:
            risk_guidance = "Risk-on environment. Favor growth and momentum."
        else:
            risk_guidance = "Risk-off environment. Be conservative, favor quality and defensives."
        
        # Build vibe guidance
        if regime.vibe_score < 0.3:
            vibe_guidance = "Very negative sentiment. High caution."
        elif regime.vibe_score < 0.5:
            vibe_guidance = "Negative sentiment. Exercise caution."
        elif regime.vibe_score < 0.7:
            vibe_guidance = "Neutral to positive sentiment."
        else:
            vibe_guidance = "Positive sentiment. Favor risk assets."
        
        # Combine into prompt context
        prompt = (
            f"CURRENT REGIME: {regime.name} ({regime.id}).\n"
            f"Summary: {regime.summary}\n"
            f"Risk Mode: {'RISK-ON' if regime.risk_on else 'RISK-OFF'}\n"
            f"Sentiment: {regime.vibe_score:.2f}/1.0 - {vibe_guidance}\n"
            f"Guidance: {risk_guidance}"
        )
        
        return prompt
