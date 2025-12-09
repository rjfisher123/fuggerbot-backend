#!/usr/bin/env python3
"""
Helper script to create favicon.ico from an image file.

Usage:
    python assets/create_favicon.py path/to/your/image.png
"""

import sys
from pathlib import Path
from PIL import Image

def create_favicon(input_path, output_path=None):
    """Create favicon.ico from input image."""
    if output_path is None:
        output_path = Path(__file__).parent / "favicon.ico"
    
    try:
        # Open and convert image
        img = Image.open(input_path)
        
        # Convert to RGB if necessary (ICO doesn't support all formats)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to common favicon sizes (16x16, 32x32, 48x48)
        sizes = [(16, 16), (32, 32), (48, 48)]
        images = []
        for size in sizes:
            resized = img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized)
        
        # Save as ICO
        images[0].save(output_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes])
        print(f"✅ Created favicon.ico at: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error creating favicon: {e}")
        print("Make sure Pillow is installed: pip install Pillow")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_favicon.py <input_image> [output_path]")
        print("Example: python create_favicon.py portrait.png")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"❌ Image not found: {input_path}")
        sys.exit(1)
    
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    create_favicon(input_path, output_path)




