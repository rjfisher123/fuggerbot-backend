"""
A2A (Agent-to-Agent) Adapter for FuggerBot Strategic Reasoner.

Handles signal ingestion from ai_inbox_digest v1.0 and feedback emission
back to upstream systems.

Key Responsibilities:
- Validate incoming signals
- Track signal processing state
- Emit structured feedback
- Maintain separation: Sensor → Strategy → Human Authority
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from uuid import uuid4

from agents.strategic.a2a_schema import (
    A2ASignal,
    A2AFeedback,
    FeedbackType,
)

logger = logging.getLogger(__name__)


class A2AAdapter:
    """
    A2A Adapter for FuggerBot Strategic Reasoner.
    
    Handles bidirectional communication with ai_inbox_digest v1.0:
    - Ingests curated signals (read-only, no re-computation)
    - Emits structured feedback (advisory only)
    """
    
    def __init__(
        self,
        feedback_callback: Optional[Callable[[A2AFeedback], None]] = None
    ):
        """
        Initialize A2A adapter.
        
        Args:
            feedback_callback: Optional callback function to handle emitted feedback.
                              If None, feedback is logged only.
        """
        self.feedback_callback = feedback_callback
        self.processed_signals: Dict[str, datetime] = {}  # signal_id -> processed_at
        self.feedback_log: List[A2AFeedback] = []
        logger.info("A2A Adapter initialized")
    
    def ingest_signal(self, signal_data: Dict[str, Any]) -> A2ASignal:
        """
        Ingest a signal from ai_inbox_digest v1.0.
        
        Args:
            signal_data: Raw signal data (dict) that will be validated and parsed into A2ASignal
        
        Returns:
            Validated A2ASignal object
        
        Raises:
            ValueError: If signal validation fails
        """
        try:
            # Parse and validate signal
            signal = A2ASignal(**signal_data)
            
            # Check for duplicates (optional: warn but allow)
            if signal.signal_id in self.processed_signals:
                logger.warning(
                    f"Signal {signal.signal_id} already processed at {self.processed_signals[signal.signal_id]}. "
                    "Processing again (may indicate duplicate upstream)."
                )
            
            # Record processing
            self.processed_signals[signal.signal_id] = datetime.now()
            
            logger.info(
                f"Ingested signal: {signal.signal_id} "
                f"(class={signal.signal_class}, priority={signal.effective_priority:.2f}, "
                f"corroboration={signal.corroboration_score:.2f})"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to ingest signal: {e}", exc_info=True)
            raise ValueError(f"Signal validation failed: {e}") from e
    
    def emit_feedback(
        self,
        signal_id: str,
        feedback_type: FeedbackType,
        summary: str,
        reasoning: str,
        strategic_relevance: Optional[float] = None,
        time_horizon: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> A2AFeedback:
        """
        Emit feedback about a processed signal.
        
        Args:
            signal_id: Signal ID this feedback refers to
            feedback_type: Type of feedback
            summary: Human-readable feedback summary
            reasoning: Reason for this feedback
            strategic_relevance: Optional strategic relevance score (0-1)
            time_horizon: Optional time horizon (e.g., 'days', 'quarters', 'years')
            context: Optional additional context dict
        
        Returns:
            Created A2AFeedback object
        """
        feedback = A2AFeedback(
            feedback_id=f"fb_{uuid4().hex[:8]}",
            signal_id=signal_id,
            feedback_type=feedback_type,
            summary=summary,
            reasoning=reasoning,
            strategic_relevance=strategic_relevance,
            time_horizon=time_horizon,
            context=context or {},
            emitted_at=datetime.now()
        )
        
        # Store in log
        self.feedback_log.append(feedback)
        
        # Call callback if provided
        if self.feedback_callback:
            try:
                self.feedback_callback(feedback)
            except Exception as e:
                logger.error(f"Feedback callback failed: {e}", exc_info=True)
        else:
            logger.info(
                f"Emitted feedback: {feedback.feedback_id} "
                f"(type={feedback_type}, signal={signal_id})"
            )
        
        return feedback
    
    def get_feedback_history(self, signal_id: Optional[str] = None) -> List[A2AFeedback]:
        """
        Get feedback history.
        
        Args:
            signal_id: Optional signal ID to filter by
        
        Returns:
            List of A2AFeedback objects
        """
        if signal_id:
            return [fb for fb in self.feedback_log if fb.signal_id == signal_id]
        return self.feedback_log.copy()
    
    def get_processed_signals(self) -> Dict[str, datetime]:
        """
        Get all processed signal IDs and timestamps.
        
        Returns:
            Dict mapping signal_id to processed_at datetime
        """
        return self.processed_signals.copy()
    
    def reset(self):
        """Reset adapter state (for testing/debugging)."""
        self.processed_signals.clear()
        self.feedback_log.clear()
        logger.info("A2A Adapter state reset")


def get_a2a_adapter(feedback_callback: Optional[Callable[[A2AFeedback], None]] = None) -> A2AAdapter:
    """
    Factory function to get an A2A adapter instance.
    
    Args:
        feedback_callback: Optional callback for feedback emission
    
    Returns:
        A2AAdapter instance
    """
    return A2AAdapter(feedback_callback=feedback_callback)

