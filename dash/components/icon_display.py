"""Helper component to display FuggerBot icon."""
import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

def display_icon_in_sidebar():
    """Display icon image in sidebar if available."""
    assets_dir = project_root / "assets"
    
    # Look for image files
    for ext in [".png", ".jpg", ".jpeg", ".ico", ".webp", ".PNG", ".JPG", ".JPEG"]:
        for name in ["fuggerbot_icon", "icon", "portrait", "favicon", "logo"]:
            img_path = assets_dir / f"{name}{ext}"
            if img_path.exists():
                try:
                    # Display icon centered
                    col1, col2, col3 = st.sidebar.columns([1, 2, 1])
                    with col2:
                        st.image(str(img_path), width=100, use_container_width=False)
                    return True
                except Exception as e:
                    # If image fails, don't show error, just return False
                    return False
    
    return False

def get_icon_path_for_page_config():
    """Get icon path for st.set_page_config."""
    assets_dir = project_root / "assets"
    
    # Prefer ICO for browser tab, then PNG
    for ext in [".ico", ".png", ".jpg", ".jpeg", ".webp", ".ICO", ".PNG", ".JPG", ".JPEG"]:
        for name in ["fuggerbot_icon", "icon", "portrait", "favicon"]:
            img_path = assets_dir / f"{name}{ext}"
            if img_path.exists():
                return str(img_path)
    
    return None

