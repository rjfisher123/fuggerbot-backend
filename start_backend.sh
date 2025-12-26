#!/bin/bash
# FuggerBot Backend Startup Script
# IMPORTANT: Must use --loop asyncio for ib_insync compatibility with nest_asyncio

cd /Users/ryanfisher/fuggerbot

echo "🚀 Starting FuggerBot Backend..."
echo "   Port: 8000"
echo "   Loop: asyncio (required for ib_insync)"
echo ""

# Kill any existing instances
pkill -9 -f "uvicorn main:app" 2>/dev/null

# Start with asyncio loop (required for nest_asyncio + ib_insync)
nohup python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --loop asyncio \
    > /tmp/fuggerbot_backend.log 2>&1 &

sleep 3

# Check if it started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend started successfully!"
    echo "   API: http://localhost:8000"
    echo "   Docs: http://localhost:8000/docs"
    echo "   Logs: tail -f /tmp/fuggerbot_backend.log"
else
    echo "❌ Backend failed to start. Check logs:"
    echo "   tail -f /tmp/fuggerbot_backend.log"
    exit 1
fi

