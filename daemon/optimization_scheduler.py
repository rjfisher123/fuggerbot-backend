"""
FuggerBot Phase 5: Optimization Scheduler Daemon

Automates the meta-optimization feedback loop:
1. Run Miner → Update learning_book.json
2. Run War Games → Test strategies
3. Run Optimizer → Select best params
4. Validate → Ensure optimized_params.json updated

Runs weekly (default: Sunday 00:00) or on-demand.

Author: FuggerBot AI Team
Version: v2.5 - Operation Autopilot
"""
import os
import sys
import time
import json
import logging
import subprocess
import schedule
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/optimization_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OptimizationDaemon")


class OptimizationDaemon:
    """
    Meta-optimization scheduler daemon.
    
    Orchestrates the complete feedback loop:
    - Mining historical patterns
    - Simulating strategies (War Games)
    - Optimizing parameters
    - Validating deployment
    """
    
    def __init__(
        self,
        interval_days: int = 7,
        run_day: str = "sunday",
        run_time: str = "00:00"
    ):
        """
        Initialize the optimization daemon.
        
        Args:
            interval_days: Days between optimization cycles (default: 7)
            run_day: Day of week to run (default: "sunday")
            run_time: Time to run in HH:MM format (default: "00:00")
        """
        self.interval_days = interval_days
        self.run_day = run_day.lower()
        self.run_time = run_time
        
        # Paths
        self.project_root = Path(__file__).parent.parent
        self.miner_script = self.project_root / "research" / "miner.py"
        self.simulator_script = self.project_root / "daemon" / "simulator" / "war_games_runner.py"
        self.optimizer_script = self.project_root / "agents" / "trm" / "strategy_optimizer_agent.py"
        self.learning_book = self.project_root / "data" / "learning_book.json"
        self.war_games_results = self.project_root / "data" / "war_games_results.json"
        self.optimized_params = self.project_root / "data" / "optimized_params.json"
        self.status_file = self.project_root / "data" / "optimization_status.json"
        
        # Ensure log directory exists
        log_dir = self.project_root / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"OptimizationDaemon initialized: Run {run_day} at {run_time}")
    
    def _get_file_mtime(self, file_path: Path) -> Optional[float]:
        """Get file modification time, or None if file doesn't exist."""
        try:
            return file_path.stat().st_mtime if file_path.exists() else None
        except Exception as e:
            logger.error(f"Error getting mtime for {file_path}: {e}")
            return None
    
    def _run_subprocess(
        self,
        script_path: Path,
        step_name: str,
        timeout: int = 3600
    ) -> bool:
        """
        Run a Python script as a subprocess with robust error handling.
        
        Args:
            script_path: Path to Python script to run
            step_name: Human-readable name for logging
            timeout: Max execution time in seconds (default: 1 hour)
            
        Returns:
            True if successful (exit code 0), False otherwise
        """
        logger.info(f"🚀 [{step_name}] Starting: {script_path}")
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ [{step_name}] Success (exit code: 0)")
                # Log last 10 lines of output for context
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[-10:]:
                    if line.strip():
                        logger.debug(f"   {line}")
                return True
            else:
                logger.error(f"❌ [{step_name}] Failed (exit code: {result.returncode})")
                logger.error(f"   STDOUT: {result.stdout[-500:]}")  # Last 500 chars
                logger.error(f"   STDERR: {result.stderr[-500:]}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ [{step_name}] Timeout after {timeout}s")
            return False
            
        except Exception as e:
            logger.error(f"💥 [{step_name}] Exception: {e}", exc_info=True)
            return False
    
    def _validate_file_updated(
        self,
        file_path: Path,
        before_mtime: Optional[float],
        step_name: str
    ) -> bool:
        """
        Validate that a file was updated during the step.
        
        Args:
            file_path: Path to file to check
            before_mtime: Modification time before step (or None)
            step_name: Human-readable name for logging
            
        Returns:
            True if file exists and was modified, False otherwise
        """
        if not file_path.exists():
            logger.error(f"❌ [{step_name}] Validation failed: {file_path} does not exist")
            return False
        
        after_mtime = self._get_file_mtime(file_path)
        
        if before_mtime is None:
            # File was created during step
            logger.info(f"✅ [{step_name}] Validation: {file_path.name} created")
            return True
        
        if after_mtime and after_mtime > before_mtime:
            # File was modified during step
            logger.info(f"✅ [{step_name}] Validation: {file_path.name} updated")
            return True
        else:
            logger.warning(f"⚠️ [{step_name}] Validation: {file_path.name} not modified (before={before_mtime}, after={after_mtime})")
            return False
    
    def _save_status(self, status: Dict[str, Any]):
        """Save optimization status to JSON file."""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
            logger.debug(f"Status saved to {self.status_file}")
        except Exception as e:
            logger.error(f"Failed to save status: {e}")
    
    def run_cycle(self) -> bool:
        """
        Execute one complete optimization cycle.
        
        Pipeline:
        1. Run Miner → Update learning_book.json
        2. Run War Games → Test strategies
        3. Run Optimizer → Select best params
        4. Validate → Ensure files updated
        
        Returns:
            True if all steps succeeded, False if any step failed
        """
        cycle_start = time.time()
        timestamp = datetime.now().isoformat()
        
        logger.info("=" * 80)
        logger.info("🚀 STARTING OPTIMIZATION CYCLE")
        logger.info(f"   Timestamp: {timestamp}")
        logger.info("=" * 80)
        
        status = {
            "last_run": timestamp,
            "status": "IN_PROGRESS",
            "steps": {},
            "duration_seconds": 0
        }
        
        # STEP 1: Run Miner
        learning_book_before = self._get_file_mtime(self.learning_book)
        step1_success = self._run_subprocess(self.miner_script, "STEP 1: Miner", timeout=1800)
        step1_validated = self._validate_file_updated(self.learning_book, learning_book_before, "STEP 1")
        
        status["steps"]["miner"] = {
            "success": step1_success and step1_validated,
            "output_file": str(self.learning_book),
            "file_updated": step1_validated
        }
        
        if not (step1_success and step1_validated):
            logger.error("🛑 ABORTING: Miner step failed")
            status["status"] = "FAILED"
            status["failed_step"] = "miner"
            status["duration_seconds"] = time.time() - cycle_start
            self._save_status(status)
            return False
        
        # STEP 2: Run War Games Simulator
        war_games_before = self._get_file_mtime(self.war_games_results)
        step2_success = self._run_subprocess(self.simulator_script, "STEP 2: War Games", timeout=3600)
        step2_validated = self._validate_file_updated(self.war_games_results, war_games_before, "STEP 2")
        
        status["steps"]["simulator"] = {
            "success": step2_success and step2_validated,
            "output_file": str(self.war_games_results),
            "file_updated": step2_validated
        }
        
        if not (step2_success and step2_validated):
            logger.error("🛑 ABORTING: War Games step failed")
            status["status"] = "FAILED"
            status["failed_step"] = "simulator"
            status["duration_seconds"] = time.time() - cycle_start
            self._save_status(status)
            return False
        
        # STEP 3: Run Strategy Optimizer
        optimized_params_before = self._get_file_mtime(self.optimized_params)
        step3_success = self._run_subprocess(self.optimizer_script, "STEP 3: Optimizer", timeout=300)
        step3_validated = self._validate_file_updated(self.optimized_params, optimized_params_before, "STEP 3")
        
        status["steps"]["optimizer"] = {
            "success": step3_success and step3_validated,
            "output_file": str(self.optimized_params),
            "file_updated": step3_validated
        }
        
        if not (step3_success and step3_validated):
            logger.error("🛑 ABORTING: Optimizer step failed")
            status["status"] = "FAILED"
            status["failed_step"] = "optimizer"
            status["duration_seconds"] = time.time() - cycle_start
            self._save_status(status)
            return False
        
        # SUCCESS!
        cycle_duration = time.time() - cycle_start
        logger.info("=" * 80)
        logger.info(f"✅ OPTIMIZATION CYCLE COMPLETE (Duration: {cycle_duration:.1f}s)")
        logger.info("=" * 80)
        
        status["status"] = "SUCCESS"
        status["duration_seconds"] = cycle_duration
        self._save_status(status)
        
        return True
    
    def start_daemon(self):
        """
        Start the scheduler daemon.
        
        Schedules optimization cycles at the configured interval.
        Runs indefinitely until interrupted.
        """
        logger.info("🤖 Starting OptimizationDaemon...")
        logger.info(f"   Schedule: Every {self.run_day} at {self.run_time}")
        logger.info(f"   Press Ctrl+C to stop")
        
        # Schedule the job
        getattr(schedule.every(), self.run_day).at(self.run_time).do(self.run_cycle)
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("🛑 OptimizationDaemon stopped by user")
    
    def run_once(self) -> bool:
        """
        Run optimization cycle once (on-demand).
        
        Useful for testing or manual triggering.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("🔧 Running optimization cycle (on-demand mode)")
        return self.run_cycle()


def main():
    """Main entry point for the optimization scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="FuggerBot Meta-Optimization Scheduler"
    )
    parser.add_argument(
        "--mode",
        choices=["daemon", "once"],
        default="daemon",
        help="Run mode: 'daemon' (scheduled) or 'once' (on-demand)"
    )
    parser.add_argument(
        "--day",
        default="sunday",
        help="Day of week to run (default: sunday)"
    )
    parser.add_argument(
        "--time",
        default="00:00",
        help="Time to run in HH:MM format (default: 00:00)"
    )
    
    args = parser.parse_args()
    
    daemon = OptimizationDaemon(
        interval_days=7,
        run_day=args.day,
        run_time=args.time
    )
    
    if args.mode == "once":
        success = daemon.run_once()
        sys.exit(0 if success else 1)
    else:
        daemon.start_daemon()


if __name__ == "__main__":
    main()

