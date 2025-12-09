# 🖼️ Save Your Portrait Image Here

## ⚠️ IMPORTANT: You need to save the image file first!

The dashboard is ready to use your portrait, but **you need to save the image file** to this folder.

## Step-by-Step:

### Option 1: Drag & Drop (Easiest)
1. **Right-click the portrait image** you want to use
2. **Save As...** or **Download** the image
3. **Drag the saved image** into this `assets/` folder
4. **Rename it** to `fuggerbot_icon.png` (or it will auto-detect if named `icon.png`)

### Option 2: Copy Command
If you have the image saved somewhere:
```bash
# Replace with your actual image path
cp ~/Downloads/portrait.png assets/fuggerbot_icon.png

# Or from Desktop
cp ~/Desktop/your_image.jpg assets/fuggerbot_icon.png
```

### Option 3: Save from Browser
1. **Right-click the portrait image** in your browser
2. **Save Image As...**
3. **Navigate to**: `/Users/ryanfisher/fuggerbot/assets/`
4. **Save as**: `fuggerbot_icon.png`

## After Saving:

1. **Verify the file exists:**
   ```bash
   ls -la assets/fuggerbot_icon.png
   ```

2. **Restart Streamlit:**
   ```bash
   # Stop Streamlit (Ctrl+C) then:
   streamlit run dash/streamlit_app.py
   ```

3. **Check terminal output** - you should see:
   ```
   ✅ Using icon: /Users/ryanfisher/fuggerbot/assets/fuggerbot_icon.png
   ```

4. **Refresh browser** - the portrait should appear in:
   - Browser tab icon
   - Sidebar (top of navigation)

## Supported File Names:
- `fuggerbot_icon.png` ✅ (recommended - will be used first)
- `icon.png`
- `portrait.png`
- `favicon.ico`
- `logo.png`

## Supported Formats:
- PNG (best quality)
- JPG/JPEG
- ICO (best for browser tabs)
- WEBP

## Current Status:
❌ **No image file found yet** - Please save your portrait image to this folder!

