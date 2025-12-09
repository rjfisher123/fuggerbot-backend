#!/bin/bash
# Install FuggerBot trigger monitor as a launchd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.fuggerbot.monitor.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🚀 Installing FuggerBot Trigger Monitor..."
echo ""

# Check if plist file exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Error: $PLIST_SOURCE not found!"
    exit 1
fi

# Check if already installed
if [ -f "$PLIST_DEST" ]; then
    echo "⚠️  Monitor is already installed. Uninstalling first..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm "$PLIST_DEST"
    echo "✅ Old installation removed"
    echo ""
fi

# Copy plist to LaunchAgents
echo "📋 Copying plist file to ~/Library/LaunchAgents/..."
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Update the plist with the correct paths (in case user moved the project)
echo "🔧 Updating paths in plist file..."
sed -i '' "s|/Users/ryanfisher/fuggerbot|$SCRIPT_DIR|g" "$PLIST_DEST"

# Find Python3 path - prefer pyenv if available, otherwise use system python
if [ -f "$HOME/.pyenv/shims/python3" ]; then
    # Use pyenv shim (will resolve to correct version)
    PYTHON3_PATH="$HOME/.pyenv/shims/python3"
elif [ -n "$(which python3)" ]; then
    PYTHON3_PATH=$(which python3)
else
    echo "❌ Error: python3 not found!"
    exit 1
fi
echo "🐍 Using Python: $PYTHON3_PATH"
sed -i '' "s|/usr/bin/python3|$PYTHON3_PATH|g" "$PLIST_DEST"

# Load the service
echo "🔄 Loading launchd service..."
launchctl load "$PLIST_DEST"

echo ""
echo "✅ FuggerBot Trigger Monitor installed successfully!"
echo ""
echo "📝 Useful commands:"
echo "   Start:   launchctl start com.fuggerbot.monitor"
echo "   Stop:    launchctl stop com.fuggerbot.monitor"
echo "   Status:  launchctl list | grep fuggerbot"
echo "   Logs:    tail -f $SCRIPT_DIR/data/logs/monitor.log"
echo "   Uninstall: ./uninstall_monitor.sh"
echo ""

