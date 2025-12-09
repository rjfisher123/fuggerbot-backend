#!/usr/bin/env python3
"""Test script for MacroDaemon."""
from daemon.watcher import MacroDaemon

print('Creating daemon...')
daemon = MacroDaemon()

print('\nRunning single cycle...')
daemon.run_once()

print('\n✅ Done!')
