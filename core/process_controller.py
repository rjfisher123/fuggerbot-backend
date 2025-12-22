"""
FuggerBot v3.0 - Process Controller (The Zombie Hunter)

Replaces legacy launcher.py.
Responsibility:
1. Kill any lingering "zombie" instances (run_bot.py, miner.py, etc.)
2. Start the unified v3.0 stack in a clean environment.
"""
import psutil
import subprocess
import time
import os
import signal
import sys
import logging
from typing import List

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [ZOOMBIE_HUNTER] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ZombieHunter")

LOG_DIR = "logs"
ZOMBIE_TARGETS = ["run_bot.py", "miner.py", "optimization_scheduler.py", "reviewer.py", "fuggerbot_commander.py"]

active_processes: List[subprocess.Popen] = []

def ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        logger.info(f"📁 Verified log directory: {LOG_DIR}")

def kill_zombies():
    """
    Scan system processes and terminate any matching ZOMBIE_TARGETS.
    """
    logger.info("🧟 Hunting zombies...")
    killed_count = 0
    
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Check if process matches target
            cmdline = proc.info.get('cmdline')
            pid = proc.info.get('pid')
            
            if pid == current_pid:
                continue
                
            if cmdline:
                # Check for python scripts
                cmd_str = " ".join(cmdline) 
                for target in ZOMBIE_TARGETS:
                    if target in cmd_str:
                        logger.warning(f"🔫 Found zombie: {target} (PID: {pid})")
                        proc.terminate()
                        killed_count += 1
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    if killed_count > 0:
        logger.info(f"💀 Terminated {killed_count} zombie processes. Waiting for cleanup...")
        time.sleep(2)
    else:
        logger.info("✨ No zombies found. Clean slate.")

def start_process(command: list, name: str, log_file: str):
    """Start a background process and log output."""
    try:
        f = open(log_file, "w")
        p = subprocess.Popen(
            command,
            stdout=f,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
            text=True
        )
        active_processes.append(p)
        logger.info(f"🚀 Started {name} (PID: {p.pid})")
        return p
    except Exception as e:
        logger.error(f"❌ Failed to start {name}: {e}")
        return None

def start_stack():
    """Launch the FuggerBot v3.0 stack."""
    ensure_log_dir()
    
    logger.info("🔋 Initializing FuggerBot v3.0 Stack...")
    
    # 1. FuggerBot Commander (UI)
    start_process(
        ["streamlit", "run", "fuggerbot_commander.py", "--server.port", "8501", "--server.headless", "true"],
        "FuggerBot Commander",
        f"{LOG_DIR}/commander.log"
    )

    # 2. Optimization Scheduler "The Brain"
    start_process(
        ["python", "daemon/optimization_scheduler.py", "--mode", "daemon"],
        "Optimization Scheduler",
        f"{LOG_DIR}/scheduler.log"
    )

    # 3. Live Trading Bot "The Executioner"
    start_process(
        ["python", "run_bot.py", "--continuous", "--interval", "60"],
        "Trading Bot",
        f"{LOG_DIR}/bot.log"
    )
    
    # 4. Trade Reviewer "The Auditor"
    start_process(
        ["python", "daemon/reviewer.py"],
        "Trade Reviewer",
        f"{LOG_DIR}/reviewer.log"
    )

    logger.info("✅ All systems go.")
    print("\n" + "="*50)
    print("   🚀 FUGGERBOT v3.0 OPERATIONAL")
    print("="*50)
    print(f"🤖 User Interface: http://localhost:8501")
    print("="*50 + "\n")

def signal_handler(sig, frame):
    """Graceful shutdown."""
    logger.info("\n🛑 Shutdown signal received.")
    for p in active_processes:
        if p.poll() is None:
            p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    # 1. Kill Zombies
    kill_zombies()
    
    # 2. Start Stack
    start_stack()
    
    # 3. Monitor
    try:
        while True:
            time.sleep(5)
            # Simple liveness check
            for p in active_processes:
                if p.poll() is not None:
                    # One of the core services died
                    logger.error(f"⚠️ Service PID {p.pid} died unexpected! Check logs.")
    except KeyboardInterrupt:
        signal_handler(None, None)
