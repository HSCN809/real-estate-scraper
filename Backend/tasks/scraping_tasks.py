# -*- coding: utf-8 -*-
"""Celery kazima gorevleri - ayri worker konteynerinde calisir."""

import os
from typing import Dict, List, Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded

from celery_app import celery_app
from api.schemas import SUPPORTED_SCRAPING_METHODS
from core.task_status import TASK_STATUS_RUNNING, TaskStatusStore
from utils.logger import get_logger

logger = get_logger("celery.scraping")


def _validate_scraping_method(scraping_method: str) -> Optional[str]:
    if scraping_method == "go_proxy":
        return (
            "scraping_method='go_proxy' is deprecated. "
            "Use a regular method with proxy_enabled=true."
        )
    if scraping_method not in SUPPORTED_SCRAPING_METHODS:
        return (
            f"Unsupported scraping_method: {scraping_method}. "
            f"Supported values: {', '.join(SUPPORTED_SCRAPING_METHODS)}"
        )
    return None


class TaskProgressManager:
    """Redis üzerinden görev ilerleme güncellemelerini yönetir"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.store = TaskStatusStore()

    def update(
        self,
        message: str = None,
        progress: int = None,
        current: int = None,
        total: int = None,
        details: str = None,
        status: str = TASK_STATUS_RUNNING,
        error: Optional[str] = None,
        platform: Optional[str] = None,
    ):
        """Redis'teki görev ilerlemesini güncelle."""
        data = self.store.update(
            self.task_id,
            status=status,
            message=message,
            progress=progress,
            current=current,
            total=total,
            details=details,
            error=error,
            platform=platform,
        )

        current_task.update_state(
            state="PROGRESS",
            meta={
                "message": data["message"],
                "progress": data["progress"],
                "current": data["current"],
                "total": data["total"],
            }
        )

    def complete(self, message: str = "Tamamlandı", success: bool = True):
        """Görevi tamamlanmış olarak işaretle."""
        if success:
            self.store.mark_completed(self.task_id, message=message)
        else:
            self.fail(message)

    def fail(self, error: str):
        """Görevi başarısız olarak işaretle."""
        self.store.mark_failed(
            self.task_id,
            message="Tarama başarısız oldu.",
            error=error,
            details=error,
        )

@celery_app.task(bind=True, name="scrape_hepsiemlak")
def scrape_hepsiemlak_task(
    self,
    listing_type: str,
    category: str,
    subtype_path: Optional[str],
    cities: List[str],
    districts: Optional[Dict[str, List[str]]],
    max_pages: int = 50,
    scraping_method: str = "selenium",
    proxy_enabled: bool = False,
):
    """Celery worker'da calisan HepsiEmlak kazima gorevi."""
    task_id = self.request.id
    progress_manager = TaskProgressManager(task_id)

    logger.info(
        f"[Task {task_id}] Starting HepsiEmlak scrape: {listing_type}/{category}, "
        f"method={scraping_method}, proxy_enabled={proxy_enabled}, cities={cities}"
    )
    progress_manager.update(
        message="HepsiEmlak taramasi baslatiliyor...",
        progress=0,
        status=TASK_STATUS_RUNNING,
        platform="hepsiemlak",
    )

    # Dongusel import'lari onlemek ve dogru baslatmayi saglamak icin burada import et
    from core.driver_manager import DriverManager
    from core.failed_pages_tracker import failed_pages_tracker
    from database.connection import get_db_session
    from database import crud

    manager = None
    driver = None
    db = None
    scrape_session = None
    scraper = None

    try:
        method_error = _validate_scraping_method(scraping_method)
        if method_error:
            logger.warning(f"[Task {task_id}] Invalid scraping method: {method_error}")
            raise ValueError(method_error)
        db = get_db_session()

        # Basarisiz sayfa takipcisini sifirla
        failed_pages_tracker.reset()

        # subtype_path'tan alt_kategori çıkar
        alt_kategori = None
        if subtype_path:
            parts = subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                alt_kategori = parts[-1].replace('-', '_')

        # Veritabaninda kazima oturumu olustur
        scrape_session = crud.create_scrape_session(
            db,
            platform="hepsiemlak",
            kategori=category,
            ilan_tipi=listing_type,
            alt_kategori=alt_kategori,
            target_cities=cities,
            target_districts=districts
        )
        db.commit()
        logger.info(f"[Task {task_id}] ScrapeSession created: ID={scrape_session.id}")

        # Redis'i guncelleyen ilerleme geri cagirima fonksiyonu
        def progress_callback(message, current=0, total=0, progress=0):
            progress_manager.update(
                message=message,
                current=current,
                total=total,
                progress=progress
            )
            # Durdurma istegini kontrol et

        # Kazıyıcı için durdurma kontrol fonksiyonu

        # Kaziyiciyi olustur
        go_proxy_url = os.getenv("GO_PROXY_URL", "http://invisible-proxy:8080")
        if scraping_method == "selenium":
            from scrapers.hepsiemlak.main import HepsiemlakScraper
            manager = DriverManager(proxy_url=go_proxy_url if proxy_enabled else None)
            driver = manager.start()

            scraper = HepsiemlakScraper(
                driver=driver,
                listing_type=listing_type,
                category=category,
                subtype_path=subtype_path,
                selected_cities=cities,
                selected_districts=districts
            )
        else:
            from scrapers.hepsiemlak.scrapling_scraper import HepsiemlakScraplingScraper

            scraper = HepsiemlakScraplingScraper(
                listing_type=listing_type,
                category=category,
                subtype_path=subtype_path,
                selected_cities=cities,
                selected_districts=districts,
                scraping_method=scraping_method,
                headless=True,
                proxy_enabled=proxy_enabled,
                proxy_url=go_proxy_url,
            )

        # Veritabanı oturumunu ayarla
        scraper.db = db
        scraper.scrape_session_id = scrape_session.id

        logger.info(
            f"[Task {task_id}] Starting scraping API call with "
            f"method={scraping_method}, proxy_enabled={proxy_enabled}"
        )

        # Kaziyiciyi durdurma kontroluyle calistir
        scraper.start_scraping_api(
            max_pages=max_pages,
            progress_callback=progress_callback,
        )

        _final_status = "completed"

        progress_manager.complete(
            message=f"Tarama tamamlandı! {getattr(scraper, 'total_scraped_count', 0)} ilan bulundu."
        )

        return {
            "status": "completed",
            "task_id": task_id,
            "total_listings": getattr(scraper, 'total_scraped_count', 0),
            "new_listings": getattr(scraper, 'new_listings_count', 0),
            "duplicates": getattr(scraper, 'duplicate_count', 0)
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[Task {task_id}] Task exceeded time limit")
        progress_manager.fail("Zaman limiti asildi")
        _final_status = "failed"
        _error_msg = "Zaman limiti asildi"
        raise

    except Exception as e:
        logger.error(f"[Task {task_id}] Task failed with error: {e}", exc_info=True)
        progress_manager.fail(str(e))
        _final_status = "failed"
        _error_msg = str(e)
        raise

    finally:
        # Her durumda (SIGTERM dahil) session'ı kapat ve kaydet
        try:
            if scrape_session and db:
                total_listings = getattr(scraper, 'total_scraped_count', 0) if scraper else 0
                new_listings = getattr(scraper, 'new_listings_count', 0) if scraper else 0
                duplicate_listings = getattr(scraper, 'duplicate_count', 0) if scraper else 0

                crud.update_scrape_session(
                    db, scrape_session.id,
                    total_listings=total_listings,
                    new_listings=new_listings,
                    duplicate_listings=duplicate_listings
                )
                status = locals().get('_final_status', 'failed')
                error_msg = locals().get('_error_msg', None)
                crud.complete_scrape_session(db, scrape_session.id, status=status, error_message=error_msg)
                db.commit()
                logger.info(f"[Task {task_id}] Finally: session closed (status={status}, total={total_listings})")
        except Exception as save_err:
            logger.error(f"[Task {task_id}] Finally save failed: {save_err}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if db:
                db.close()
            if manager:
                manager.stop()


@celery_app.task(bind=True, name="scrape_emlakjet")
def scrape_emlakjet_task(
    self,
    listing_type: str,
    category: str,
    subtype_path: Optional[str],
    cities: List[str],
    districts: Optional[Dict[str, List[str]]],
    max_listings: int = 0,
    max_pages: int = 50,  # kullanim disi, geriye uyumluluk icin tutuldu
    scraping_method: str = "selenium",
    proxy_enabled: bool = False,
):
    """Celery worker'da calisan EmlakJet kazima gorevi."""
    task_id = self.request.id
    progress_manager = TaskProgressManager(task_id)

    logger.info(
        f"[Task {task_id}] Starting EmlakJet scrape: {listing_type}/{category}, "
        f"method={scraping_method}, proxy_enabled={proxy_enabled}"
    )
    progress_manager.update(
        message="EmlakJet taramasi baslatiliyor...",
        progress=0,
        status=TASK_STATUS_RUNNING,
        platform="emlakjet",
    )

    from core.driver_manager import DriverManager
    from core.config import get_emlakjet_config
    from database.connection import get_db_session
    from database import crud

    manager = None
    db = None
    scrape_session = None
    scraper = None

    try:
        method_error = _validate_scraping_method(scraping_method)
        if method_error:
            logger.warning(f"[Task {task_id}] Invalid scraping method: {method_error}")
            raise ValueError(method_error)
        db = get_db_session()
        config = get_emlakjet_config()

        # subtype_path'tan alt_kategori çıkar
        alt_kategori = None
        if subtype_path:
            parts = subtype_path.strip('/').split('-')
            if len(parts) >= 2:
                alt_kategori = parts[-1].replace('-', '_')

        # Veritabaninda kazima oturumu olustur
        scrape_session = crud.create_scrape_session(
            db,
            platform="emlakjet",
            kategori=category,
            ilan_tipi=listing_type,
            alt_kategori=alt_kategori,
            target_cities=cities,
            target_districts=districts
        )
        db.commit()
        logger.info(f"[Task {task_id}] ScrapeSession created: ID={scrape_session.id}")

        # Temel URL'yi olustur
        if subtype_path:
            base_url = config.base_url + subtype_path
        else:
            category_path = config.categories[listing_type].get(category, '')
            base_url = config.base_url + category_path

        # Ilerleme geri cagirima fonksiyonu
        def progress_callback(message, current=0, total=0, progress=0):
            progress_manager.update(
                message=message,
                current=current,
                total=total,
                progress=progress
            )

        # Kazıyıcı için durdurma kontrol fonksiyonu

        go_proxy_url = os.getenv("GO_PROXY_URL", "http://invisible-proxy:8080")
        if scraping_method == "selenium":
            from scrapers.emlakjet.main import EmlakJetScraper

            manager = DriverManager(proxy_url=go_proxy_url if proxy_enabled else None)
            driver = manager.start()
            scraper = EmlakJetScraper(
                driver=driver,
                base_url=base_url,
                category=category,
                listing_type=listing_type,
                subtype_path=subtype_path
            )
        else:
            from scrapers.emlakjet.scrapling_scraper import EmlakJetScraplingScraper

            scraper = EmlakJetScraplingScraper(
                listing_type=listing_type,
                category=category,
                subtype_path=subtype_path,
                selected_cities=cities,
                selected_districts=districts,
                scraping_method=scraping_method,
                headless=True,
                proxy_enabled=proxy_enabled,
                proxy_url=go_proxy_url,
            )

        # Veritabanı oturumunu kazıyıcıya ayarla
        scraper.db = db
        scraper.scrape_session_id = scrape_session.id

        scraper.start_scraping_api(
            cities=cities,
            districts=districts,
            max_listings=max_listings,
            max_pages=max_pages,
            progress_callback=progress_callback,
        )

        _final_status = "completed"

        total_listings = len(getattr(scraper, 'all_listings', []))
        logger.info(f"[Task {task_id}] Scraping completed: {total_listings} listings collected")
        progress_manager.complete(
            message=f"EmlakJet taraması tamamlandı! {total_listings} ilan bulundu."
        )

        return {
            "status": "completed",
            "task_id": task_id,
            "total_listings": total_listings,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[Task {task_id}] Task exceeded time limit")
        progress_manager.fail("Zaman limiti asildi")
        _final_status = "failed"
        _error_msg = "Zaman limiti asildi"
        raise

    except Exception as e:
        logger.error(f"[Task {task_id}] Task failed: {e}", exc_info=True)
        progress_manager.fail(str(e))
        _final_status = "failed"
        _error_msg = str(e)
        raise

    finally:
        # Her durumda (SIGTERM dahil) session'ı kapat
        # Listing'ler zaten sayfa bazlı kaydedildi, tekrar kaydetmeye gerek yok
        try:
            if scrape_session and db:
                total_listings = len(getattr(scraper, 'all_listings', [])) if scraper else 0

                crud.update_scrape_session(
                    db, scrape_session.id,
                    total_listings=total_listings,
                )
                status = locals().get('_final_status', 'failed')
                error_msg = locals().get('_error_msg', None)
                crud.complete_scrape_session(db, scrape_session.id, status=status, error_message=error_msg)
                db.commit()
                logger.info(f"[Task {task_id}] Finally: session closed (status={status}, total={total_listings})")
        except Exception as save_err:
            logger.error(f"[Task {task_id}] Finally save failed: {save_err}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            if db:
                db.close()
            if manager:
                manager.stop()
