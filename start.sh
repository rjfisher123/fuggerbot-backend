#!/bin/bash
# Startup script for FuggerBot
# This script can be used as an alternative to the CMD in Dockerfile

set -e

# Create necessary directories if they don't exist
mkdir -p data/logs data/forecasts data/paper_trades

# Set default port if not provided
PORT=${PORT:-8080}

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT}




