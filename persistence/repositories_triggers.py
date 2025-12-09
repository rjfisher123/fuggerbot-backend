"""Repository classes for trigger results and trade candidates."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from sqlalchemy.orm import Session
from sqlalchemy import desc

from persistence.models_triggers import TriggerResult, TradeCandidate


class TriggerResultRepository:
    """Repository for managing trigger results."""

    def __init__(self, session: Session):
        self.session = session

    def add_result(
        self,
        trigger_id: str,
        data_snapshot: Dict[str, Any],
        fired_at: Optional[datetime] = None,
    ) -> TriggerResult:
        """
        Add a new trigger result.
        
        Args:
            trigger_id: ID of the trigger that fired
            data_snapshot: Dictionary with snapshot of trigger data at time of firing
            fired_at: Timestamp when trigger fired (defaults to now)
        
        Returns:
            Created TriggerResult
        """
        result = TriggerResult(
            trigger_id=trigger_id,
            fired_at=fired_at or datetime.utcnow(),
            data_snapshot=json.dumps(data_snapshot),
            created_at=datetime.utcnow(),
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def get_by_id(self, result_id: int) -> Optional[TriggerResult]:
        """Get trigger result by ID."""
        return self.session.query(TriggerResult).filter(TriggerResult.id == result_id).first()

    def get_by_trigger_id(self, trigger_id: str, limit: int = 100) -> List[TriggerResult]:
        """
        Get recent trigger results for a specific trigger.
        
        Args:
            trigger_id: ID of the trigger
            limit: Maximum number of results to return
        
        Returns:
            List of TriggerResult objects, most recent first
        """
        return (
            self.session.query(TriggerResult)
            .filter(TriggerResult.trigger_id == trigger_id)
            .order_by(desc(TriggerResult.fired_at))
            .limit(limit)
            .all()
        )

    def list_recent(self, limit: int = 100) -> List[TriggerResult]:
        """
        List recent trigger results.
        
        Args:
            limit: Maximum number of results to return
        
        Returns:
            List of TriggerResult objects, most recent first
        """
        return (
            self.session.query(TriggerResult)
            .order_by(desc(TriggerResult.fired_at))
            .limit(limit)
            .all()
        )

    def delete_result(self, result_id: int) -> bool:
        """
        Delete a trigger result (and its associated trade candidates).
        
        Args:
            result_id: ID of the result to delete
        
        Returns:
            True if deleted, False if not found
        """
        result = self.get_by_id(result_id)
        if not result:
            return False
        self.session.delete(result)
        self.session.commit()
        return True


class TradeCandidateRepository:
    """Repository for managing trade candidates."""

    def __init__(self, session: Session):
        self.session = session

    def add_candidate(
        self,
        trigger_result_id: int,
        trigger_id: str,
        symbol: str,
        action: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TradeCandidate:
        """
        Add a new trade candidate.
        
        Args:
            trigger_result_id: ID of the associated TriggerResult
            trigger_id: ID of the trigger that generated this candidate
            symbol: Trading symbol
            action: Trade action (BUY, SELL, HOLD)
            confidence: Confidence score (0.0 to 1.0)
            metadata: Optional additional metadata dict
        
        Returns:
            Created TradeCandidate
        """
        candidate = TradeCandidate(
            trigger_result_id=trigger_result_id,
            trigger_id=trigger_id,
            symbol=symbol,
            action=action,
            confidence=confidence,
            candidate_metadata=json.dumps(metadata) if metadata else None,
            created_at=datetime.utcnow(),
        )
        self.session.add(candidate)
        self.session.commit()
        self.session.refresh(candidate)
        return candidate

    def get_by_id(self, candidate_id: int) -> Optional[TradeCandidate]:
        """Get trade candidate by ID."""
        return self.session.query(TradeCandidate).filter(TradeCandidate.id == candidate_id).first()

    def get_by_trigger_result_id(self, trigger_result_id: int) -> List[TradeCandidate]:
        """
        Get all trade candidates for a trigger result.
        
        Args:
            trigger_result_id: ID of the TriggerResult
        
        Returns:
            List of TradeCandidate objects
        """
        return (
            self.session.query(TradeCandidate)
            .filter(TradeCandidate.trigger_result_id == trigger_result_id)
            .order_by(desc(TradeCandidate.confidence))
            .all()
        )

    def get_by_trigger_id(self, trigger_id: str, limit: int = 100) -> List[TradeCandidate]:
        """
        Get recent trade candidates for a specific trigger.
        
        Args:
            trigger_id: ID of the trigger
            limit: Maximum number of candidates to return
        
        Returns:
            List of TradeCandidate objects, most recent first
        """
        return (
            self.session.query(TradeCandidate)
            .filter(TradeCandidate.trigger_id == trigger_id)
            .order_by(desc(TradeCandidate.created_at))
            .limit(limit)
            .all()
        )

    def list_recent(self, limit: int = 100) -> List[TradeCandidate]:
        """
        List recent trade candidates.
        
        Args:
            limit: Maximum number of candidates to return
        
        Returns:
            List of TradeCandidate objects, most recent first
        """
        return (
            self.session.query(TradeCandidate)
            .order_by(desc(TradeCandidate.created_at))
            .limit(limit)
            .all()
        )

    def get_by_symbol(self, symbol: str, limit: int = 100) -> List[TradeCandidate]:
        """
        Get recent trade candidates for a specific symbol.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of candidates to return
        
        Returns:
            List of TradeCandidate objects, most recent first
        """
        return (
            self.session.query(TradeCandidate)
            .filter(TradeCandidate.symbol == symbol.upper())
            .order_by(desc(TradeCandidate.created_at))
            .limit(limit)
            .all()
        )

    def get_by_action(self, action: str, limit: int = 100) -> List[TradeCandidate]:
        """
        Get recent trade candidates for a specific action.
        
        Args:
            action: Trade action (BUY, SELL, HOLD)
            limit: Maximum number of candidates to return
        
        Returns:
            List of TradeCandidate objects, most recent first
        """
        return (
            self.session.query(TradeCandidate)
            .filter(TradeCandidate.action == action.upper())
            .order_by(desc(TradeCandidate.created_at))
            .limit(limit)
            .all()
        )

    def delete_candidate(self, candidate_id: int) -> bool:
        """
        Delete a trade candidate.
        
        Args:
            candidate_id: ID of the candidate to delete
        
        Returns:
            True if deleted, False if not found
        """
        candidate = self.get_by_id(candidate_id)
        if not candidate:
            return False
        self.session.delete(candidate)
        self.session.commit()
        return True

