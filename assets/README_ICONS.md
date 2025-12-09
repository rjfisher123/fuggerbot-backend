# FuggerBot Icon Assets

## Icon Files

Four SVG icon versions are provided, all based on the historical portrait inspiration:

### 1. `fuggerbot_icon_portrait.svg` ⭐ **RECOMMENDED**
- **Most faithful to the original portrait**
- Detailed facial features (eyes looking left, prominent nose, thin lips)
- Brown cap with texture/folds
- Dark cloak with wide collar and white undergarment sliver
- Blue textured background matching the portrait
- Subtle trading elements integrated
- Best for representing the historical inspiration

### 2. `fuggerbot_icon_modern.svg`
- Modernized version of the portrait
- Cleaner lines while maintaining key features
- Brown cap, dark cloak, blue background
- Trading chart line and currency accent
- Good balance of historical and modern

### 3. `fuggerbot_icon_simple.svg`
- Minimalist, modern version
- Simplified portrait silhouette
- Cleaner design for small icon sizes
- Trending line accent (trading theme)
- "F" letter accent for FuggerBot

### 4. `fuggerbot_icon.svg`
- Original detailed version
- Includes decorative chart lines
- Dollar sign accent
- More traditional portrait style

## Usage

### For Web/Dashboard:
- Use `fuggerbot_icon_simple.svg` for Streamlit dashboard
- Update `dash/streamlit_app.py`:
  ```python
  st.set_page_config(
      page_title="FuggerBot Dashboard",
      page_icon="assets/fuggerbot_icon_simple.svg",
      ...
  )
  ```

### For App Icons:
Convert SVG to PNG at various sizes:
- 16x16, 32x32, 48x48 (favicons)
- 128x128, 256x256, 512x512 (app icons)

### Conversion Tools:
```bash
# Using ImageMagick
convert -background none -resize 512x512 assets/fuggerbot_icon_simple.svg assets/fuggerbot_icon_512.png

# Using Inkscape (if installed)
inkscape --export-filename=fuggerbot_icon_512.png --export-width=512 --export-height=512 assets/fuggerbot_icon_simple.svg
```

## Design Notes

- **Color Scheme**: Deep blue background (#1a237e) - professional, trustworthy
- **Portrait**: Brown cap, dark cloak - inspired by historical portrait
- **Accents**: Green trending line (trading success), gold/yellow accent (wealth)
- **Style**: Modern minimalist while honoring the historical inspiration

## Customization

The SVG files can be easily edited to:
- Change colors
- Adjust proportions
- Add/remove elements
- Modify accents

All elements are vector-based for scalability.

