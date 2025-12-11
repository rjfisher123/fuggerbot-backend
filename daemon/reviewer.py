"""
Reviewer daemon.

Automatically runs post-mortem reviews on completed trades and saves results
back to trade_memory.json.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import sys

# Ensure project root on sys.path for script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reasoning.memory import TradeMemory
from engine.postmortem import TradeCoroner

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # 5 minutes


def _load_memory(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"trades": []}
    with path.open("r") as f:
        return json.load(f)


def _save_memory(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


class ReviewerDaemon:
    """
    Background reviewer that auto-runs post-mortems on completed trades.
    """

    def __init__(self, memory_path: Optional[Path] = None, poll_interval: int = POLL_INTERVAL_SECONDS):
        self.memory_path = memory_path or Path("data/trade_memory.json")
        self.poll_interval = poll_interval
        self.coroner = TradeCoroner()

    def run_once(self, max_reviews: int = 10) -> int:
        """
        Run a single review pass.

        Args:
            max_reviews: Maximum number of trades to review in this pass (default: 10)

        Returns:
            count of trades reviewed.
        """
        data = _load_memory(self.memory_path)
        trades: List[Dict[str, Any]] = data.get("trades", [])
        if not trades:
            logger.info("No trades in memory.")
            return 0

        reviewed = 0
        updated = False

        for trade in trades:
            # Limit reviews per pass to avoid long-running processes
            if reviewed >= max_reviews:
                break

            pnl = trade.get("pnl")
            post_mortem = trade.get("post_mortem")

            # Only review closed trades (pnl present) without a post-mortem
            if pnl is None or post_mortem is not None:
                continue

            try:
                report = self.coroner.conduct_review(trade)
                if report:
                    trade["post_mortem"] = report.model_dump()
                    reviewed += 1
                    updated = True

                    reason = report.outcome_category.value if hasattr(report.outcome_category, "value") else str(report.outcome_category)
                    logger.info(
                        f"📝 Reviewed {trade.get('symbol', 'UNKNOWN')}: "
                        f"{trade.get('outcome', 'UNKNOWN')} attributed to {reason} "
                        f"({report.root_cause[:80]}...)"
                    )
            except Exception as e:
                logger.error(f"Error reviewing trade {trade.get('trade_id', 'UNKNOWN')}: {e}", exc_info=True)
                continue

        if updated:
            try:
                # Reload file right before saving to merge with any concurrent updates
                # This prevents overwriting new trades added by the bot
                current_data = _load_memory(self.memory_path)
                current_trades = {t.get("trade_id"): t for t in current_data.get("trades", [])}
                
                # Update current trades with our post-mortem additions
                for trade in trades:
                    trade_id = trade.get("trade_id")
                    if trade_id and trade.get("post_mortem"):
                        if trade_id in current_trades:
                            # Preserve all existing fields, just add/update post_mortem
                            current_trades[trade_id]["post_mortem"] = trade["post_mortem"]
                        else:
                            # New trade not in current data, add it
                            current_data["trades"].append(trade)
                
                # Convert back to list and save
                current_data["trades"] = list(current_trades.values())
                _save_memory(self.memory_path, current_data)
                logger.info(f"💾 Saved {reviewed} post-mortems to {self.memory_path}")
            except Exception as e:
                logger.error(f"Failed to save memory: {e}", exc_info=True)

        return reviewed

    def start(self):
        """
        Start the daemon loop.
        """
        logger.info("ReviewerDaemon started.")
        while True:
            try:
                count = self.run_once()
                logger.info(f"Review cycle complete. Trades reviewed: {count}")
            except Exception as e:
                logger.error(f"Error during review cycle: {e}", exc_info=True)
            time.sleep(self.poll_interval)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reviewer Daemon for Trade Post-Mortems")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)"
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=10,
        help="Maximum reviews per pass (default: 10)"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    daemon = ReviewerDaemon()
    
    if args.once:
        count = daemon.run_once(max_reviews=args.max_reviews)
        print(f"Reviewed {count} trades")
    else:
        daemon.start()

