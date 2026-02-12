# -*- coding: utf-8 -*-
"""Celery görev destekli gelişmiş loglama araçları"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

# Core modülünden içe aktarım
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..'))
from core.config import get_config


class StructuredFormatter(logging.Formatter):
    """Yapılandırılmış loglama için JSON biçimlendirici"""

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

        # Varsa task_id ekle
        if hasattr(record, 'task_id'):
            log_data["task_id"] = record.task_id

        # Ek alanları ekle
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Varsa hata bilgisini ekle
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Renkli konsol biçimlendirici"""

    COLORS = {
        'DEBUG': '\033[36m',     # Camgöbeği
        'INFO': '\033[32m',      # Yeşil
        'WARNING': '\033[33m',   # Sarı
        'ERROR': '\033[31m',     # Kırmızı
        'CRITICAL': '\033[35m',  # Eflatun
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        # Varsa task_id öneki ekle
        if hasattr(record, 'task_id') and record.task_id:
            record.msg = f"[{record.task_id[:8]}] {record.msg}"

        return super().format(record)


class TaskContextFilter(logging.Filter):
    """Log kayıtlarına görev bağlamı ekleyen filtre"""

    def __init__(self, task_id: Optional[str] = None):
        super().__init__()
        self.task_id = task_id

    def filter(self, record):
        # Celery current_task'tan task_id almayı dene
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
    """Konsol ve isteğe bağlı dosya handler'ları ile logger yapılandırır ve döndürür."""
    config = get_config()

    # Varsayılan değerler olarak config değerlerini kullan
    level = level or config.log_level
    log_to_file = log_to_file if log_to_file is not None else config.log_to_file
    log_file = log_file or config.log_file

    # Logger oluştur
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Mevcut handler'ları temizle
    logger.handlers.clear()

    # Görev bağlamı filtresini ekle
    logger.addFilter(TaskContextFilter(task_id))

    # Renkli biçimli konsol handler'ı
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Dosya handler'ı (isteğe bağlı)
    if log_to_file:
        # Gerekirse log dizinini oluştur
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Dönen dosya handler'ı kullan (maks 10MB, 5 yedek)
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

    # Yapılandırılmış JSON log dosyası (normal loglardan ayrı)
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
    """Mevcut bir logger döndürür veya yoksa yeni bir tane oluşturur."""
    logger = logging.getLogger(name)

    # Logger'da handler yoksa yapılandır
    if not logger.handlers:
        return setup_logger(name, task_id=task_id)

    # Görev bağlamı filtresi yoksa ekle
    has_task_filter = any(isinstance(f, TaskContextFilter) for f in logger.filters)
    if not has_task_filter:
        logger.addFilter(TaskContextFilter(task_id))

    return logger


class ScraperLogger:
    """Scraper işlemleri için Celery görev takibi destekli özel logger sınıfı."""

    def __init__(self, name: str = "scraper", task_id: Optional[str] = None):
        self.logger = get_logger(name, task_id)
        self.task_id = task_id

    def _log_with_context(self, level: str, message: str, **extra):
        """Ek bağlam verisiyle logla"""
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
        """Bilgi mesajı logla"""
        self.logger.info(message, extra=extra if extra else None)

    def debug(self, message: str, **extra):
        """Debug mesajı logla"""
        self.logger.debug(message, extra=extra if extra else None)

    def warning(self, message: str, **extra):
        """Uyarı mesajı logla"""
        self.logger.warning(f"{message}", extra=extra if extra else None)

    def error(self, message: str, exc_info: bool = False, **extra):
        """Hata mesajı logla"""
        self.logger.error(f"{message}", exc_info=exc_info, extra=extra if extra else None)

    def success(self, message: str, **extra):
        """Başarı mesajı logla (info seviyesinde)"""
        self.logger.info(f"{message}", extra=extra if extra else None)

    def start_operation(self, operation: str, **extra):
        """Bir işlemin başlangıcını logla"""
        self.logger.info(f"{operation} baslatiliyor...", extra=extra if extra else None)

    def complete_operation(self, operation: str, **extra):
        """Bir işlemin tamamlanmasını logla"""
        self.logger.info(f"{operation} tamamlandi!", extra=extra if extra else None)

    def scrape_page(self, page: int, total: int, count: int, **extra):
        """Sayfa kazıma ilerlemesini logla"""
        self.logger.info(
            f"Sayfa {page}/{total}: {count} ilan bulundu",
            extra={"page": page, "total": total, "count": count, **(extra or {})}
        )

    def navigate(self, url: str, **extra):
        """Sayfa yönlendirmesini logla"""
        self.logger.info(f"Navigating to: {url}", extra={"url": url, **(extra or {})})

    def save_data(self, filename: str, count: int, **extra):
        """Veri kaydetmeyi logla"""
        self.logger.info(
            f"{count} kayit {filename} dosyasina kaydedildi",
            extra={"filename": filename, "count": count, **(extra or {})}
        )

    def task_progress(self, progress: int, message: str, **extra):
        """Görev ilerleme güncellemesini logla"""
        self.logger.info(
            f"[%{progress}] {message}",
            extra={"progress": progress, **(extra or {})}
        )


# Varsayılan logger örneğini oluştur
default_logger = ScraperLogger()


def get_task_logger(task_id: str) -> ScraperLogger:
    """Belirli bir Celery görevi için yapılandırılmış logger örneği döndürür."""
    return ScraperLogger(f"celery.task.{task_id[:8]}", task_id)
