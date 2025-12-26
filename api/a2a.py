"""
A2A (Agent-to-Agent) Protocol API Endpoints for FuggerBot.

Handles signal ingestion from ai_inbox_digest v1.0 and feedback emission.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import logger
from agents.strategic import (
    A2ASignal,
    A2AFeedback,
    get_a2a_adapter,
    get_strategic_reasoner,
    FeedbackType,
)

router = APIRouter(prefix="/api/a2a", tags=["a2a"])

# Global instances (singleton pattern)
_a2a_adapter = None
_strategic_reasoner = None


def get_adapter():
    """Get or create A2A adapter instance."""
    global _a2a_adapter
    if _a2a_adapter is None:
        _a2a_adapter = get_a2a_adapter()
    return _a2a_adapter


def get_reasoner():
    """Get or create Strategic Reasoner instance."""
    global _strategic_reasoner
    if _strategic_reasoner is None:
        _strategic_reasoner = get_strategic_reasoner(a2a_adapter=get_adapter())
    return _strategic_reasoner


class IngestResponse(BaseModel):
    """Response model for signal ingestion."""
    success: bool = Field(..., description="Whether ingestion was successful")
    signal_id: str = Field(..., description="Signal ID that was processed")
    interpretation_id: Optional[str] = Field(default=None, description="Interpretation ID (if applicable)")
    feedback_id: Optional[str] = Field(default=None, description="Feedback ID that was emitted")
    strategic_relevance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Strategic relevance score")
    message: str = Field(..., description="Human-readable status message")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_signal(signal_data: Dict[str, Any]):
    """
    Ingest a signal from ai_inbox_digest v1.0 via A2A protocol.
    
    Accepts a JSON payload conforming to A2ASignal schema.
    
    Returns:
        IngestResponse with signal processing results
    """
    try:
        logger.info(f"Received A2A signal ingestion request: {signal_data.get('signal_id', 'unknown')}")
        
        # Get adapter and reasoner
        adapter = get_adapter()
        reasoner = get_reasoner()
        
        # Ingest signal (validates schema)
        try:
            signal = adapter.ingest_signal(signal_data)
        except Exception as e:
            logger.error(f"Signal validation failed: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Signal validation failed: {str(e)}")
        
        # Process signal (strategic interpretation + feedback emission)
        try:
            interpretation = reasoner.process_signal(signal)
            
            # Get feedback that was emitted
            feedback_history = adapter.get_feedback_history(signal.signal_id)
            feedback_id = feedback_history[-1].feedback_id if feedback_history else None
            
            logger.info(
                f"Signal processed successfully: {signal.signal_id} "
                f"(relevance={interpretation.strategic_relevance:.2f}, "
                f"feedback={feedback_id})"
            )
            
            return IngestResponse(
                success=True,
                signal_id=signal.signal_id,
                interpretation_id=f"int_{signal.signal_id}",
                feedback_id=feedback_id,
                strategic_relevance=interpretation.strategic_relevance,
                message=f"Signal processed successfully. Strategic relevance: {interpretation.strategic_relevance:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Signal processing failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Signal processing failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in signal ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/feedback/{signal_id}")
async def get_feedback_for_signal(signal_id: str):
    """
    Get feedback history for a specific signal.
    
    Args:
        signal_id: Signal ID to retrieve feedback for
    
    Returns:
        List of A2AFeedback objects
    """
    try:
        adapter = get_adapter()
        feedback_history = adapter.get_feedback_history(signal_id)
        
        # Use model_dump with mode='json' to properly serialize datetime objects
        return JSONResponse(content={
            "signal_id": signal_id,
            "feedback_count": len(feedback_history),
            "feedback": [fb.model_dump(mode='json') for fb in feedback_history]
        })
    except Exception as e:
        logger.error(f"Failed to retrieve feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feedback: {str(e)}")


@router.get("/status")
async def get_a2a_status():
    """
    Get A2A adapter status and statistics.
    
    Returns:
        Status information about processed signals and feedback
    """
    try:
        adapter = get_adapter()
        processed_signals = adapter.get_processed_signals()
        feedback_log = adapter.get_feedback_history()
        
        return JSONResponse(content={
            "status": "operational",
            "processed_signals_count": len(processed_signals),
            "total_feedback_count": len(feedback_log),
            "processed_signal_ids": list(processed_signals.keys())[:10]  # First 10
        })
    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

