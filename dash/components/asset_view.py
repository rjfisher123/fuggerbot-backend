import streamlit as st
import json
from pathlib import Path

def show_assets():
    st.subheader("📊 Portfolio Overview")
    data_path = Path(__file__).parents[1] / "data" / "holdings.json"

    if not data_path.exists():
        st.warning("No holdings data found. Create data/holdings.json to populate your assets.")
        return

    with open(data_path, "r") as f:
        holdings = json.load(f)

    for asset in holdings:
        st.markdown(f"**{asset['symbol']}** — {asset.get('type', '')}")
        st.write(asset)
        st.divider()


def render_asset_view():
    """Render the asset view component (wrapper for show_assets)."""
    show_assets()