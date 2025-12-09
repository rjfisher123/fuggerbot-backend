# Quick Icon Setup for FuggerBot

## To Use Your Picture as the Icon:

### Option 1: Simple Copy (Easiest)
1. **Copy your cropped image** to the `assets/` folder:
   ```bash
   cp /path/to/your/image.png assets/fuggerbot_icon.png
   ```

2. **Restart Streamlit**:
   ```bash
   # Stop Streamlit (Ctrl+C) then:
   streamlit run dash/streamlit_app.py
   ```

### Option 2: Create Favicon (Best for Browser Tab)
1. **Place your image** in assets folder:
   ```bash
   cp your_image.png assets/fuggerbot_icon.png
   ```

2. **Create favicon.ico** (for better browser tab support):
   ```bash
   pip install Pillow
   python assets/create_favicon.py assets/fuggerbot_icon.png
   ```

3. **Restart Streamlit**

## Supported File Names:
- `assets/fuggerbot_icon.png` ✅ (recommended)
- `assets/icon.png`
- `assets/portrait.png`
- `assets/favicon.ico`
- `assets/logo.png`

## Supported Formats:
- PNG (best quality)
- JPG/JPEG
- ICO (best for browser tabs)
- WEBP

## Troubleshooting:

**Icon not showing?**
1. Check file exists: `ls -la assets/fuggerbot_icon.*`
2. Check file permissions: `chmod 644 assets/fuggerbot_icon.png`
3. Restart Streamlit completely (close and reopen)
4. Clear browser cache (hard refresh: Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)

**Still not working?**
- Try renaming to exactly `assets/fuggerbot_icon.png`
- Make sure it's a square image (512x512 or 256x256 recommended)
- Check the terminal output when Streamlit starts - it will show which icon it's using

## Current Status:
The dashboard will automatically detect your image file when you place it in the `assets/` folder with one of the supported names above.




