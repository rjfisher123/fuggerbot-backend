# Routes alerts via Twilio or other notifiers
from typing import Optional, Dict, Any
from .sms_notifier import get_sms_notifier
from .logger import logger


class AlertRouter:
    """Routes alerts via various channels (SMS, etc.)."""
    
    def __init__(self):
        self.sms_notifier = get_sms_notifier()
    
    def send_price_alert(
        self,
        symbol: str,
        price: float,
        trigger_type: str,
        trigger_value: float
    ) -> bool:
        """
        Send a price alert via SMS.
        
        Args:
            symbol: Trading symbol
            price: Current price
            trigger_type: Type of trigger (below, above, etc.)
            trigger_value: Trigger threshold value
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        if not self.sms_notifier.is_available():
            logger.warning("SMS notifier not available")
            return False
        
        message = (
            f"🚨 Price Alert: {symbol}\n"
            f"Current: ${price:.2f}\n"
            f"Trigger: {trigger_type} ${trigger_value:.2f}"
        )
        
        try:
            self.sms_notifier.send(message)
            logger.info(f"Price alert sent for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to send price alert: {e}")
            return False
    
    def send_alert(
        self,
        message: str,
        level: str = "info",
        channel: str = "sms"
    ) -> bool:
        """
        Send a generic alert message.
        
        Args:
            message: Alert message text
            level: Alert level (info, warning, error)
            channel: Channel to use (sms, slack, etc.)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if channel == "sms":
            if not self.sms_notifier.is_available():
                logger.warning("SMS notifier not available")
                return False
            try:
                self.sms_notifier.send(message)
                logger.info(f"Alert sent via SMS: {message[:50]}...")
                return True
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
                return False
        else:
            logger.warning(f"Unknown alert channel: {channel}")
            return False


# Global instance
_alert_router: Optional[AlertRouter] = None


def get_alert_router() -> AlertRouter:
    """Get or create the global alert router instance."""
    global _alert_router
    if _alert_router is None:
        _alert_router = AlertRouter()
    return _alert_router


def send_alert(message: str, channel: str = "sms") -> bool:
    """
    Send an alert message.
    
    Args:
        message: Alert message
        channel: Channel to use (currently only "sms")
        
    Returns:
        True if sent successfully, False otherwise
    """
    router = get_alert_router()
    if channel == "sms":
        if router.sms_notifier.is_available():
            try:
                router.sms_notifier.send(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
                return False
    return False
