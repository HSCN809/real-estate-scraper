# -*- coding: utf-8 -*-
"""
Logging utilities for the scraper
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

# Import from core module
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from core.config import get_config


def setup_logger(
    name: str = "scraper",
    level: Optional[str] = None,
    log_to_file: Optional[bool] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_file: Log file path
        
    Returns:
        Configured logger instance
    """
    config = get_config()
    
    # Use config values as defaults
    level = level or config.log_level
    log_to_file = log_to_file if log_to_file is not None else config.log_to_file
    log_file = log_file or config.log_file
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colorful format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_to_file:
        # Create logs directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "scraper") -> logging.Logger:
    """
    Get an existing logger or create a new one.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up
    if not logger.handlers:
        return setup_logger(name)
    
    return logger


class ScraperLogger:
    """
    Custom logger class with emoji-enhanced output for scraper operations.
    """
    
    def __init__(self, name: str = "scraper"):
        self.logger = get_logger(name)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(f"⚠️  {message}")
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(f"❌ {message}")
    
    def success(self, message: str):
        """Log success message (info level with checkmark)"""
        self.logger.info(f"✅ {message}")
    
    def start_operation(self, operation: str):
        """Log start of an operation"""
        self.logger.info(f"🚀 {operation} başlatılıyor...")
    
    def complete_operation(self, operation: str):
        """Log completion of an operation"""
        self.logger.info(f"✅ {operation} tamamlandı!")
    
    def scrape_page(self, page: int, total: int, count: int):
        """Log page scraping progress"""
        self.logger.info(f"📄 Sayfa {page}/{total}: {count} ilan bulundu")
    
    def navigate(self, url: str):
        """Log navigation"""
        self.logger.info(f"🌐 Navigating to: {url}")
    
    def save_data(self, filename: str, count: int):
        """Log data save"""
        self.logger.info(f"💾 {count} kayıt {filename} dosyasına kaydedildi")


# Create default logger instance
default_logger = ScraperLogger()
