"""
Configuration module.

Provides settings management and asset universe configuration for the application.
"""
from config.settings import Settings, get_settings, reload_settings
from config.universe import (
    CRYPTO_CORE,
    TECH_GIANTS,
    MACRO_ETF,
    FOREX_MAJORS,
    FULL_TEST_SUITE,
    get_asset_class,
    get_all_assets,
    get_asset_count,
    ASSET_CLASSES
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "reload_settings",
    # Universe
    "CRYPTO_CORE",
    "TECH_GIANTS",
    "MACRO_ETF",
    "FOREX_MAJORS",
    "FULL_TEST_SUITE",
    "get_asset_class",
    "get_all_assets",
    "get_asset_count",
    "ASSET_CLASSES",
]

