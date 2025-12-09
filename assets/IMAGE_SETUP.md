# Using a Cropped Image for FuggerBot Icon

## Quick Setup

1. **Place your cropped image** in the `assets/` folder with one of these names:
   - `fuggerbot_icon.png` (recommended)
   - `fuggerbot_icon.jpg`
   - `icon.png`
   - `portrait.png`

2. **Image Requirements:**
   - **Format**: PNG, JPG, JPEG, ICO, or WEBP
   - **Size**: Square recommended (512x512, 256x256, or 128x128 pixels)
   - **Aspect Ratio**: 1:1 (square) works best
   - **File Size**: Keep under 500KB for web performance

## Image Preparation Tips

### For Best Results:

1. **Crop to Square:**
   ```bash
   # Using ImageMagick
   convert input.jpg -gravity center -crop 1:1 -resize 512x512 assets/fuggerbot_icon.png
   
   # Using sips (macOS)
   sips -z 512 512 input.jpg --out assets/fuggerbot_icon.png
   ```

2. **Optimize for Web:**
   ```bash
   # Reduce file size while maintaining quality
   convert input.jpg -quality 85 -strip assets/fuggerbot_icon.png
   ```

3. **Create Multiple Sizes** (optional but recommended):
   - `fuggerbot_icon_512.png` - 512x512 (large)
   - `fuggerbot_icon_256.png` - 256x256 (medium)
   - `fuggerbot_icon_128.png` - 128x128 (small)
   - `fuggerbot_icon_32.png` - 32x32 (favicon)

## Current Setup

The dashboard will automatically detect and use your image file if it's named:
- `assets/fuggerbot_icon.png` (or .jpg, .jpeg, .ico, .webp)
- `assets/icon.png`
- `assets/portrait.png`

## Fallback Behavior

If no image file is found, the system will:
1. Try SVG icons (realistic portrait → modern → simple)
2. Fall back to emoji (🤖)

## Testing

After placing your image:
```bash
# Verify the file exists
ls -lh assets/fuggerbot_icon.*

# Restart Streamlit to see the new icon
streamlit run dash/streamlit_app.py
```

The icon will appear in:
- Browser tab
- Streamlit sidebar (if configured)
- App title area

## Recommended Image Specifications

For the portrait you described:
- **Crop**: Focus on head and shoulders (chest up)
- **Background**: Keep the blue background or make transparent
- **Size**: 512x512 pixels for best quality
- **Format**: PNG with transparency (if you want transparent background)

## Example: Creating from the Portrait

If you have the full portrait image:

1. **Crop to square** focusing on the face and cap
2. **Resize to 512x512** (or 256x256 for smaller file)
3. **Save as PNG** in the assets folder
4. **Name it** `fuggerbot_icon.png`

The dashboard will automatically use it!




