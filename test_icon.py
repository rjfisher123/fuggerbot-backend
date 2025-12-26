#!/usr/bin/env python3
"""Test script to verify icon setup."""
from pathlib import Path

assets_dir = Path("assets")
print("🔍 Checking for icon files...\n")

# Check for image files
image_extensions = [".png", ".jpg", ".jpeg", ".ico", ".webp", ".PNG", ".JPG", ".JPEG", ".ICO"]
possible_names = ["fuggerbot_icon", "icon", "portrait", "favicon", "logo"]

found_files = []
for ext in image_extensions:
    for name in possible_names:
        img_path = assets_dir / f"{name}{ext}"
        if img_path.exists():
            found_files.append(img_path)
            print(f"✅ Found: {img_path} ({img_path.stat().st_size} bytes)")

if not found_files:
    print("❌ No image files found in assets/ folder")
    print("\n📋 To add your portrait image:")
    print("   1. Save your image file to: assets/fuggerbot_icon.png")
    print("   2. Supported formats: PNG, JPG, ICO, WEBP")
    print("   3. Supported names: fuggerbot_icon, icon, portrait, favicon, logo")
    print("\n💡 Quick test: Create a test image:")
    print("   touch assets/fuggerbot_icon.png")
    print("   (Then replace with your actual image)")
else:
    print(f"\n✅ Found {len(found_files)} image file(s)")
    print("   The dashboard should automatically use the first one found.")











