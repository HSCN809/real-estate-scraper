# -*- coding: utf-8 -*-
"""
Celery application configuration
"""

from celery import Celery
import os

# Redis URL from environment or default
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery_app = Celery(
    "real_estate_scraper",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.scraping_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Retry if worker dies
    task_time_limit=7200,  # 2 hour hard limit
    task_soft_time_limit=6900,  # Soft limit for graceful shutdown

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time (scraping is resource-intensive)
    worker_concurrency=1,  # Single worker for scraping

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store extended task info

    # Task tracking
    task_track_started=True,  # Track when task starts
    task_send_sent_event=True,  # Send events when task is sent

    # Retry settings
    task_default_retry_delay=60,  # 1 minute delay between retries
    task_max_retries=3,
)

# Optional: Custom task base class for logging
class LoggingTask(celery_app.Task):
    """Base task class with enhanced logging"""

    def on_success(self, retval, task_id, args, kwargs):
        from utils.logger import get_logger
        logger = get_logger("celery.task")
        logger.info(f"Task {task_id} completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from utils.logger import get_logger
        logger = get_logger("celery.task")
        logger.error(f"Task {task_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        from utils.logger import get_logger
        logger = get_logger("celery.task")
        logger.warning(f"Task {task_id} retrying: {exc}")


# Set as default task class
celery_app.Task = LoggingTask
