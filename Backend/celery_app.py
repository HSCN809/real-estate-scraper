# -*- coding: utf-8 -*-
"""Celery uygulama yapılandırması"""

from celery import Celery
import os

# Ortam değişkeninden veya varsayılandan Redis URL
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Celery uygulamasını oluştur
celery_app = Celery(
    "real_estate_scraper",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.scraping_tasks"]
)

# Celery yapılandırması
celery_app.conf.update(
    # Görev ayarları
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,

    # Görev çalıştırma ayarları
    task_acks_late=True,  # Görev tamamlandıktan sonra onayla
    task_reject_on_worker_lost=True,  # Worker çökerse yeniden dene
    task_time_limit=7200,  # 2 saatlik kesin limit
    task_soft_time_limit=6900,  # Düzgün kapatma için yumuşak limit

    # Worker ayarları
    worker_prefetch_multiplier=1,  # Aynı anda tek görev (kazıma yoğun kaynak kullanır)
    worker_concurrency=1,  # Kazıma için tek worker

    # Sonuç backend ayarları
    result_expires=86400,  # Sonuçlar 24 saat sonra sona erer
    result_extended=True,  # Genişletilmiş görev bilgisini sakla

    # Görev takibi
    task_track_started=True,  # Görev başladığında takip et
    task_send_sent_event=True,  # Görev gönderildiğinde olay gönder

    # Yeniden deneme ayarları
    task_default_retry_delay=60,  # Yeniden denemeler arası 1 dakika gecikme
    task_max_retries=3,
)

# Loglama için özel görev temel sınıfı
class LoggingTask(celery_app.Task):
    """Gelişmiş loglama destekli temel görev sınıfı"""

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


# Varsayılan görev sınıfı olarak ayarla
celery_app.Task = LoggingTask
