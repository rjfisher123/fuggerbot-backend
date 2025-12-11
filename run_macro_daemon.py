#!/usr/bin/env python3
"""
Run the Macro Regime Daemon.

This script starts the continuous regime monitoring daemon.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from daemon.watcher import MacroDaemon

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting Macro Regime Daemon")
    print("=" * 60)
    print()
    
    try:
        daemon = MacroDaemon()
        daemon.start()  # This will run continuously
    except KeyboardInterrupt:
        print("\n🛑 Daemon stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


