# -*- coding: utf-8 -*-
"""Celery uygulama yapılandırması"""

from celery import Celery
from core.task_status import REDIS_URL

# Celery uygulamasini olustur
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

    # Gorev calistirma ayarlari
    task_acks_late=True,  # Görev tamamlandıktan sonra onayla
    task_reject_on_worker_lost=True,  # Worker çökerse yeniden dene
    task_time_limit=7200,  # 2 saatlik kesin limit
    task_soft_time_limit=6900,  # Duzgun kapatma icin yumusak limit

    # Worker ayarları
    worker_prefetch_multiplier=1,  # Ayni anda tek gorev (kazima yogun kaynak kullanir)
    worker_concurrency=1,  # Kazıma için tek worker

    # Sonuç backend ayarları
    result_expires=86400,  # Sonuçlar 24 saat sonra sona erer
    result_extended=True,  # Genisletilmis gorev bilgisini sakla

    # Görev takibi
    task_track_started=True,  # Gorev basladiginda takip et
    task_send_sent_event=True,  # Gorev gonderildiginde olay gonder

    # Yeniden deneme ayarları
    task_default_retry_delay=60,  # Yeniden denemeler arası 1 dakika gecikme
    task_max_retries=3,
)

# Loglama için özel görev temel sınıfı
class LoggingTask(celery_app.Task):
    """Gelismis loglama destekli temel gorev sinifi."""

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
