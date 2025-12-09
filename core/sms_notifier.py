"""Twilio SMS notification module for FuggerBot core functionality."""
import os
from typing import Optional
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from .logger import logger

# Load environment variables
load_dotenv()


class SMSNotifier:
    """Handles SMS notifications via Twilio."""
    
    def __init__(self):
        """Initialize SMS notifier with Twilio credentials from environment."""
        # Reload .env to pick up any changes
        load_dotenv(override=True)
        
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_FROM")
        self.to_number = os.getenv("TWILIO_TO_NUMBER") or os.getenv("TWILIO_TO")
        
        self._client: Optional[Client] = None
        self._is_configured = self._validate_config()
    
    def _validate_config(self) -> bool:
        """Validate that all required Twilio credentials are present."""
        required = [self.account_sid, self.auth_token, self.from_number, self.to_number]
        if not all(required):
            missing = []
            if not self.account_sid:
                missing.append("TWILIO_ACCOUNT_SID or TWILIO_SID")
            if not self.auth_token:
                missing.append("TWILIO_AUTH_TOKEN or TWILIO_TOKEN")
            if not self.from_number:
                missing.append("TWILIO_FROM_NUMBER or TWILIO_FROM")
            if not self.to_number:
                missing.append("TWILIO_TO_NUMBER or TWILIO_TO")
            
            logger.warning(f"Twilio SMS not configured. Missing: {', '.join(missing)}")
            return False
        return True
    
    @property
    def client(self) -> Optional[Client]:
        """Get or create Twilio client."""
        if not self._is_configured:
            return None
        
        if self._client is None:
            try:
                self._client = Client(self.account_sid, self.auth_token)
                logger.debug("Twilio client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                return None
        
        return self._client
    
    def send(self, message: str) -> bool:
        """
        Send an SMS message.
        
        Args:
            message: The message body to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self._is_configured:
            logger.warning("SMS not sent: Twilio not configured")
            return False
        
        if not message or not message.strip():
            logger.warning("SMS not sent: empty message")
            return False
        
        client = self.client
        if not client:
            return False
        
        try:
            result = client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            logger.info(f"SMS sent successfully. SID: {result.sid}, To: {self.to_number}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending SMS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if SMS notifications are available (configured)."""
        return self._is_configured
    
    def get_recent_messages(self, limit: int = 10) -> list:
        """
        Get recent incoming SMS messages.
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dicts with 'body', 'from', 'date_sent', etc.
        """
        if not self._is_configured:
            return []
        
        client = self.client
        if not client:
            return []
        
        try:
            # Get messages sent TO our Twilio number (incoming messages)
            messages = client.messages.list(
                to=self.from_number,
                limit=limit
            )
            
            result = []
            for msg in messages:
                result.append({
                    'body': msg.body,
                    'from': msg.from_,
                    'to': msg.to,
                    'date_sent': msg.date_sent,
                    'sid': msg.sid
                })
            
            return result
        except Exception as e:
            logger.error(f"Error fetching recent messages: {e}")
            return []


# Global instance
_sms_notifier: Optional[SMSNotifier] = None


def get_sms_notifier(force_reload: bool = False) -> SMSNotifier:
    """
    Get the global SMS notifier instance.
    
    Args:
        force_reload: If True, recreate the notifier instance (useful after .env changes)
        
    Returns:
        SMSNotifier instance
    """
    global _sms_notifier
    if _sms_notifier is None or force_reload:
        _sms_notifier = SMSNotifier()
    return _sms_notifier


def send_sms(message: str) -> bool:
    """
    Convenience function to send an SMS.
    
    Args:
        message: The message body to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    return get_sms_notifier().send(message)

