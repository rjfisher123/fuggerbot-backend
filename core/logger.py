# Standardized logger for use across modules
import logging
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent / "data" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Configure root logger
logger = logging.getLogger("fuggerbot")
logger.setLevel(logging.INFO)

# Remove existing handlers to avoid duplicates
logger.handlers.clear()

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(log_dir / "fuggerbot.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def setup_logger(name: str = "fuggerbot", level: int = logging.INFO) -> logging.Logger:
    """
    Setup a logger with the given name and level.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger
    """
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(level)
    return logger_instance
