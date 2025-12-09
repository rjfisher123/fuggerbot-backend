"""Streamlit wrapper for SMS notifications using the core SMS notifier."""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from core.sms_notifier import send_sms as core_send_sms, get_sms_notifier


def send_sms(message: str):
    """
    Send an SMS using Twilio credentials stored in environment variables.
    This is a Streamlit-aware wrapper around the core SMS functionality.
    """
    try:
        notifier = get_sms_notifier()
        
        if not notifier.is_available():
            st.warning("Twilio environment variables missing — please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, TWILIO_TO_NUMBER")
            return False

        success = core_send_sms(message)
        
        if success:
            st.success(f"📱 SMS sent to {notifier.to_number}")
        else:
            st.error("❌ SMS failed — check logs for details")
        
        return success

    except Exception as e:
        st.error(f"❌ SMS failed: {e}")
        return False