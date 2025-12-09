#!/usr/bin/env python3
"""Run the FuggerBot trigger monitor as a background service."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.trigger_engine import run_trigger_monitor
from core.logger import logger

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FuggerBot Trigger Monitor")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check triggers once and exit (for testing)"
    )
    
    args = parser.parse_args()
    
    if args.once:
        logger.info("Running trigger check once...")
        from core.trigger_engine import TriggerEngine
        trigger_file = project_root / "dash" / "data" / "triggers.json"
        alerted_file = project_root / "dash" / "data" / "alerted_triggers.json"
        engine = TriggerEngine(trigger_file, alerted_file, args.interval)
        engine.check_all_triggers()
        logger.info("Trigger check complete.")
    else:
        logger.info(f"Starting continuous trigger monitoring (interval: {args.interval}s)")
        try:
            run_trigger_monitor(interval=args.interval)
        except KeyboardInterrupt:
            logger.info("Trigger monitor stopped by user")


