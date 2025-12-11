"""
Tuning audit logger.

Provides Pydantic schema for tuning events and utilities to append JSONL logs
with rotation when files grow too large.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Default log file
DEFAULT_LOG_PATH = Path("logs/tuning_events.jsonl")

# Rotation settings
MAX_LINES = 10_000


class TuningEvent(BaseModel):
    """
    Schema for a tuning event record.
    """
    symbol: str
    param_name: str
    old_value: float
    new_value: float
    reason: str
    hit_rate: float = Field(..., ge=0.0, le=1.0)
    regret_rate: float = Field(..., ge=0.0, le=1.0)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


def rotate_logs_if_needed(log_path: Path = DEFAULT_LOG_PATH, max_lines: int = MAX_LINES) -> None:
    """
    Rotate the JSONL log file if it exceeds max_lines.
    The current file is renamed with a timestamp suffix.
    """
    if not log_path.exists():
        return

    try:
        with log_path.open("r") as f:
            line_count = sum(1 for _ in f)
    except Exception:
        # If we cannot read the file, skip rotation to avoid losing data
        return

    if line_count < max_lines:
        return

    ts = int(time.time())
    rotated = log_path.with_name(f"{log_path.stem}_{ts}{log_path.suffix}")
    log_path.rename(rotated)


def log_tuning_event(event: TuningEvent, log_path: Optional[Path] = None) -> None:
    """
    Append a tuning event to the JSONL log, rotating if necessary.
    """
    log_path = log_path or DEFAULT_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    rotate_logs_if_needed(log_path)

    with log_path.open("a") as f:
        f.write(json.dumps(event.model_dump()) + "\n")


