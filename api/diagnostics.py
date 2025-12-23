"""
System Diagnostics API.

Exposes internal memory state and macro regime tracking for debugging.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import json
import logging
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger("api.diagnostics")

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

# -- MACRO ENDPOINTS --

@router.get("/macro")
async def get_macro_regime():
    """
    Get the current Macro Regime state from the tracker logs or live instance.
    """
    # Since we don't have a live global tracker instance easily accessible here without DI,
    # we'll read the latest state from the log file which RegimeTracker writes to.
    log_file = Path("data/macro_log.json")
    
    if not log_file.exists():
        return {
            "regime": "NEUTRAL",
            "risk_on": True,
            "vibe_score": 0.5,
            "source": "fallback"
        }
        
    try:
        with open(log_file, "r") as f:
            data = json.load(f)
            
        shifts = data.get("shifts", [])
        if not shifts:
            return {
                "regime": "NEUTRAL",
                "risk_on": True,
                "vibe_score": 0.5,
                "source": "empty_log"
            }
            
        # Get the 'new_regime' from the last shift
        latest = shifts[-1].get("new_regime", {})
        return {
            "regime": latest.get("id", "UNKNOWN"),
            "name": latest.get("name", "Unknown Regime"),
            "risk_on": latest.get("risk_on", False),
            "vibe_score": latest.get("vibe_score", 0.5),
            "timestamp": shifts[-1].get("timestamp"),
            "source": "macro_log"
        }
    except Exception as e:
        logger.error(f"Error reading macro log: {e}")
        return {"error": "Failed to read macro state"}

# -- MEMORY DIAGNOSTICS --

@router.get("/hallucinations")
async def get_hallucinations():
    """
    Get a list of trades flagged as hallucinations or delusions.
    Reads from 'data/trade_memory.json.backup' (since main memory might be dynamic or large).
    """
    # Prefer live memory file if possible, else backup
    memory_files = [
        Path("data/test_memory_wargames.json"), # Used in simulation
        Path("data/trade_memory.json"),         # Live logic
        Path("data/trade_memory.json.backup")   # Fallback
    ]
    
    found_file = None
    for p in memory_files:
        if p.exists():
            found_file = p
            break
            
    if not found_file:
        return {"items": [], "count": 0, "source": "none"}
        
    hits = []
    try:
        with open(found_file, "r") as f:
            data = json.load(f)
            
        # Structure of memory file is typically a list of dicts
        # We look for 'delusion': True or outcome_type='MODEL_HALLUCINATION'
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Sometimes wrapped?
            items = data.get("episodes", []) if "episodes" in data else []
            if not items and "memory" in data:
                 items = data["memory"]
        else:
            items = []
            
        for item in items:
            # Check various flags used in different versions
            is_hallucination = (
                item.get("meta", {}).get("delusion") is True or
                item.get("outcome_type") == "MODEL_HALLUCINATION" or
                "hallucination" in str(item.get("reason", "")).lower()
            )
            
            if is_hallucination:
                hits.append(item)
                
        # Limit to last 100 to avoid huge payloads
        hits = hits[-100:]
        hits.reverse() # Newest first
        
        return {
            "items": hits, 
            "count": len(hits), 
            "source": found_file.name
        }
        
    except Exception as e:
        logger.error(f"Error reading memory for diagnostics: {e}")
        return {"error": "Failed to analyze memory", "details": str(e)}
