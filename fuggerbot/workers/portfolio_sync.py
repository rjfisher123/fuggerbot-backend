"""
Portfolio sync worker (module entry point).

This module re-exports the actual worker from the workers package
to allow execution via: python -m fuggerbot.workers.portfolio_sync
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import and re-export the actual worker
from workers.portfolio_sync import PortfolioSync, main

__all__ = ['PortfolioSync', 'main']

if __name__ == "__main__":
    main()
