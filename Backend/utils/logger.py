# -*- coding: utf-8 -*-
"""
Enhanced logging utilities for the scraper with Celery task support
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

# Import from core module
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from core.config import get_config


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add task_id if present
        if hasattr(record, 'task_id'):
            log_data["task_id"] = record.task_id

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        # Add task_id prefix if present
        if hasattr(record, 'task_id') and record.task_id:
            record.msg = f"[{record.task_id[:8]}] {record.msg}"

        return super().format(record)


class TaskContextFilter(logging.Filter):
    """Filter that adds task context to log records"""

    def __init__(self, task_id: Optional[str] = None):
        super().__init__()
        self.task_id = task_id

    def filter(self, record):
        # Try to get task_id from Celery current_task
        if not hasattr(record, 'task_id'):
            try:
                from celery import current_task
                if current_task and current_task.request:
                    record.task_id = current_task.request.id
                else:
                    record.task_id = self.task_id
            except ImportError:
                record.task_id = self.task_id
        return True


def setup_logger(
    name: str = "scraper",
    level: Optional[str] = None,
    log_to_file: Optional[bool] = None,
    log_file: Optional[str] = None,
    structured: bool = False,
    task_id: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_file: Log file path
        structured: Use JSON structured logging for files
        task_id: Optional task ID for context

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

    # Add task context filter
    logger.addFilter(TaskContextFilter(task_id))

    # Console handler with colored format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
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

        # Use rotating file handler (max 10MB, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(task_id)s] - %(filename)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)

        logger.addHandler(file_handler)

    # Structured JSON log file (separate from regular logs)
    if log_to_file:
        json_log_path = log_file.replace('.log', '_structured.jsonl')
        json_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(StructuredFormatter())
        logger.addHandler(json_handler)

    return logger


def get_logger(name: str = "scraper", task_id: Optional[str] = None) -> logging.Logger:
    """
    Get an existing logger or create a new one.

    Args:
        name: Logger name
        task_id: Optional task ID for context

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # If logger has no handlers, set it up
    if not logger.handlers:
        return setup_logger(name, task_id=task_id)

    # Add task context filter if not present
    has_task_filter = any(isinstance(f, TaskContextFilter) for f in logger.filters)
    if not has_task_filter:
        logger.addFilter(TaskContextFilter(task_id))

    return logger


class ScraperLogger:
    """
    Custom logger class with emoji-enhanced output for scraper operations.
    Supports task ID tracking for Celery tasks.
    """

    def __init__(self, name: str = "scraper", task_id: Optional[str] = None):
        self.logger = get_logger(name, task_id)
        self.task_id = task_id

    def _log_with_context(self, level: str, message: str, **extra):
        """Log with extra context data"""
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            "",
            0,
            message,
            (),
            None
        )
        if extra:
            record.extra_data = extra
        if self.task_id:
            record.task_id = self.task_id
        self.logger.handle(record)

    def info(self, message: str, **extra):
        """Log info message"""
        self.logger.info(message, extra=extra if extra else None)

    def debug(self, message: str, **extra):
        """Log debug message"""
        self.logger.debug(message, extra=extra if extra else None)

    def warning(self, message: str, **extra):
        """Log warning message"""
        self.logger.warning(f"{message}", extra=extra if extra else None)

    def error(self, message: str, exc_info: bool = False, **extra):
        """Log error message"""
        self.logger.error(f"{message}", exc_info=exc_info, extra=extra if extra else None)

    def success(self, message: str, **extra):
        """Log success message (info level with checkmark)"""
        self.logger.info(f"{message}", extra=extra if extra else None)

    def start_operation(self, operation: str, **extra):
        """Log start of an operation"""
        self.logger.info(f"{operation} baslatiliyor...", extra=extra if extra else None)

    def complete_operation(self, operation: str, **extra):
        """Log completion of an operation"""
        self.logger.info(f"{operation} tamamlandi!", extra=extra if extra else None)

    def scrape_page(self, page: int, total: int, count: int, **extra):
        """Log page scraping progress"""
        self.logger.info(
            f"Sayfa {page}/{total}: {count} ilan bulundu",
            extra={"page": page, "total": total, "count": count, **(extra or {})}
        )

    def navigate(self, url: str, **extra):
        """Log navigation"""
        self.logger.info(f"Navigating to: {url}", extra={"url": url, **(extra or {})})

    def save_data(self, filename: str, count: int, **extra):
        """Log data save"""
        self.logger.info(
            f"{count} kayit {filename} dosyasina kaydedildi",
            extra={"filename": filename, "count": count, **(extra or {})}
        )

    def task_progress(self, progress: int, message: str, **extra):
        """Log task progress update"""
        self.logger.info(
            f"[%{progress}] {message}",
            extra={"progress": progress, **(extra or {})}
        )


# Create default logger instance
default_logger = ScraperLogger()


def get_task_logger(task_id: str) -> ScraperLogger:
    """
    Get a logger instance for a specific Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        ScraperLogger configured for the task
    """
    return ScraperLogger(f"celery.task.{task_id[:8]}", task_id)
