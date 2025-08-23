"""
Centralized logging configuration for the application.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    """Configure application-wide logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            RotatingFileHandler(
                log_dir / "app.log", 
                maxBytes=10485760,  # 10MB
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )
    
    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    # Set up application loggers
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, log_level.upper()))
    
    return app_logger

# Global logger instance
logger = setup_logging()
