#!/bin/bash
# Uninstall FuggerBot trigger monitor launchd service

set -e

PLIST_NAME="com.fuggerbot.monitor.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🛑 Uninstalling FuggerBot Trigger Monitor..."
echo ""

if [ ! -f "$PLIST_DEST" ]; then
    echo "ℹ️  Monitor is not installed."
    exit 0
fi

# Stop and unload the service
echo "🔄 Stopping and unloading service..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl stop com.fuggerbot.monitor 2>/dev/null || true

# Remove the plist file
echo "🗑️  Removing plist file..."
rm "$PLIST_DEST"

echo ""
echo "✅ FuggerBot Trigger Monitor uninstalled successfully!"
echo ""


