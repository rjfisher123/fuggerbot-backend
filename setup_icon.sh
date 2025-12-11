#!/bin/bash
# Helper script to set up the FuggerBot icon from an image file

echo "🎨 FuggerBot Icon Setup"
echo "========================"
echo ""

# Check if image file is provided as argument
if [ -z "$1" ]; then
    echo "Usage: ./setup_icon.sh /path/to/your/image.png"
    echo ""
    echo "Or manually:"
    echo "1. Copy your portrait image to: assets/fuggerbot_icon.png"
    echo "2. Restart Streamlit"
    exit 1
fi

SOURCE_IMAGE="$1"
TARGET_DIR="assets"
TARGET_FILE="$TARGET_DIR/fuggerbot_icon.png"

# Check if source exists
if [ ! -f "$SOURCE_IMAGE" ]; then
    echo "❌ Error: Image file not found: $SOURCE_IMAGE"
    exit 1
fi

# Create assets directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy image
echo "📋 Copying image..."
cp "$SOURCE_IMAGE" "$TARGET_FILE"

# Check if copy was successful
if [ -f "$TARGET_FILE" ]; then
    echo "✅ Success! Icon saved to: $TARGET_FILE"
    echo ""
    echo "📊 File info:"
    ls -lh "$TARGET_FILE"
    echo ""
    echo "🚀 Next step: Restart Streamlit to see the new icon!"
    echo "   streamlit run dash/streamlit_app.py"
else
    echo "❌ Error: Failed to copy image"
    exit 1
fi





