"""
FuggerBot v2.5 - Unified System Launcher

Starts all FuggerBot components in a single command:
- Main Dashboard (port 8501)
- Macro Dashboard (port 8502)
- Optimization Scheduler (daemon mode)
- Live Trading Bot (continuous mode)

Usage:
    python launcher.py

Press Ctrl+C to stop all services.

Author: FuggerBot AI Team
Version: v2.5 - Operation Autopilot
"""
import subprocess
import sys
import time
import signal
import os
import logging
from typing import List

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [LAUNCHER] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Launcher")

# Configuration
LOG_DIR = "logs"
processes: List[subprocess.Popen] = []


def ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logger.info(f"📁 Created log directory: {LOG_DIR}")


def cleanup_ports():
    """
    Clean up any processes using the dashboard ports.
    
    This prevents "Port already in use" errors from previous runs.
    """
    ports = [8501, 8502]
    for port in ports:
        try:
            # Find processes using the port
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        logger.info(f"🧹 Cleaned up process {pid} on port {port}")
                    except (ProcessLookupError, ValueError):
                        pass
        except Exception as e:
            # Not critical if cleanup fails
            pass


def start_process(command: list, name: str, log_file: str):
    """
    Start a background process and pipe output to a log file.
    
    Args:
        command: Command to execute as a list
        name: Human-readable name for logging
        log_file: Path to log file for stdout/stderr
        
    Returns:
        subprocess.Popen object or None if failed
    """
    try:
        f = open(log_file, "w")
        p = subprocess.Popen(
            command,
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
            text=True
        )
        processes.append(p)
        logger.info(f"✅ Started {name} (PID: {p.pid}) -> Logs: {log_file}")
        return p
    except Exception as e:
        logger.error(f"❌ Failed to start {name}: {e}")
        return None


def signal_handler(sig, frame):
    """
    Handle Ctrl+C to gracefully terminate all child processes.
    
    Args:
        sig: Signal number
        frame: Current stack frame
    """
    logger.info("\n🛑 Shutdown signal received. Terminating all systems...")
    for i, p in enumerate(processes):
        if p.poll() is None:  # If running
            logger.info(f"   Terminating PID {p.pid}...")
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"   Process {p.pid} did not terminate, killing...")
                p.kill()
    
    logger.info("👋 All systems offline.")
    sys.exit(0)


def main():
    """Main entry point for the unified launcher."""
    ensure_log_dir()
    cleanup_ports()  # Clean up ports before starting
    
    # Register Signal Handler (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("="*50)
    print("   🚀 FUGGERBOT V2.5 - UNIFIED LAUNCHER")
    print("="*50)

    # 1. Start Dashboard (Streamlit)
    start_process(
        ["streamlit", "run", "tools/dashboard.py", "--server.port", "8501", "--server.headless", "true"],
        "Dashboard",
        f"{LOG_DIR}/dashboard.log"
    )

    # 2. Start Macro Dashboard (Optional, on port 8502)
    start_process(
        ["streamlit", "run", "ui/diagnostics/macro_dashboard.py", "--server.port", "8502", "--server.headless", "true"],
        "Macro Dashboard",
        f"{LOG_DIR}/macro_dashboard.log"
    )

    # 3. Start Optimization Scheduler (The Brain)
    start_process(
        ["python", "daemon/optimization_scheduler.py", "--mode", "daemon"],
        "Optimization Scheduler",
        f"{LOG_DIR}/scheduler.log"
    )

    # 4. Start Live Trading Bot (The Executioner)
    start_process(
        ["python", "run_bot.py", "--continuous", "--interval", "60"],
        "Trading Bot",
        f"{LOG_DIR}/bot.log"
    )
    
    # 5. Start Trade Reviewer (Post-Mortem Analysis)
    start_process(
        ["python", "daemon/reviewer.py"],
        "Trade Reviewer",
        f"{LOG_DIR}/reviewer.log"
    )

    print("\n✅ SYSTEM OPERATIONAL")
    print(f"📊 Main Dashboard:  http://localhost:8501")
    print(f"🌍 Macro Dashboard: http://localhost:8502")
    print(f"📝 Logs located in /{LOG_DIR} directory")
    print("Press Ctrl+C to stop all services.\n")

    # Monitor Loop
    try:
        while True:
            time.sleep(5)
            # Check if any critical process died
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    exit_code = p.poll()
                    logger.warning(f"⚠️ Process {p.pid} died unexpectedly (exit code: {exit_code}). Check logs.")
                    # Optional: Logic to auto-restart could go here
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()

