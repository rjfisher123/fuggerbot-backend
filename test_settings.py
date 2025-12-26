#!/usr/bin/env python3
"""
Quick test script to verify settings are loading correctly.
"""
from config import get_settings

def test_settings():
    """Test that settings load correctly."""
    try:
        settings = get_settings()
        print("✅ Settings loaded successfully!")
        print(f"   Model: {settings.deepseek_model}")
        print(f"   Environment: {settings.env_state}")
        print(f"   API Key: {'***' + settings.openrouter_api_key[-4:] if len(settings.openrouter_api_key) > 4 else '***'}")
        print(f"   Is Production: {settings.is_production}")
        print(f"   Is Development: {settings.is_development}")
        return True
    except ValueError as e:
        print(f"❌ Error loading settings: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_settings()








