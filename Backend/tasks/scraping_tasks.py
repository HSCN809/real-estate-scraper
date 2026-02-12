# -*- coding: utf-8 -*-
"""
Celery scraping tasks - runs in separate worker container
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from celery import current_task
from celery.exceptions import SoftTimeLimitExceeded

from celery_app import celery_app
from utils.logger import get_logger

logger = get_logger("celery.scraping")


class TaskProgressManager:
    """Manages task progress updates via Redis"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection"""
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis_client = redis.from_url(redis_url)

    def update(
        self,
        message: str = None,
        progress: int = None,
        current: int = None,
        total: int = None,
        details: str = None,
        status: str = "running"
    ):
        """Update task progress in Redis"""
        key = f"scrape_task:{self.task_id}"

        # Get existing data
        existing = self.redis_client.get(key)
        if existing:
            data = json.loads(existing)
        else:
            data = {
                "task_id": self.task_id,
                "status": "running",
                "message": "",
                "progress": 0,
                "current": 0,
                "total": 0,
                "details": "",
                "started_at": datetime.now().isoformat(),
                "should_stop": False,
                "stopped_early": False,
            }

        # Update fields if provided
        if message is not None:
            data["message"] = message
        if progress is not None:
            data["progress"] = progress
        if current is not None:
            data["current"] = current
        if total is not None:
            data["total"] = total
        if details is not None:
            data["details"] = details
        if status is not None:
            data["status"] = status

        data["updated_at"] = datetime.now().isoformat()

        # Store in Redis with 24h expiry
        self.redis_client.setex(key, 86400, json.dumps(data))

        # Also update Celery task state
        current_task.update_state(
            state="PROGRESS",
            meta={
                "message": data["message"],
                "progress": data["progress"],
                "current": data["current"],
                "total": data["total"],
            }
        )

    def is_stop_requested(self) -> bool:
        """Check if stop was requested"""
        key = f"scrape_task:{self.task_id}"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data).get("should_stop", False)
        return False

    def set_stopped_early(self):
        """Mark task as stopped early"""
        key = f"scrape_task:{self.task_id}"
        data = self.redis_client.get(key)
        if data:
            data = json.loads(data)
            data["stopped_early"] = True
            data["status"] = "stopped"
            self.redis_client.setex(key, 86400, json.dumps(data))

    def complete(self, message: str = "Tamamlandı", success: bool = True):
        """Mark task as completed"""
        self.update(
            message=message,
            progress=100,
            status="completed" if success else "failed"
        )

    def fail(self, error: str):
        """Mark task as failed"""
        self.update(
            message=f"Hata: {error}",
            status="failed"
        )


@celery_app.task(bind=True, name="scrape_hepsiemlak")
def scrape_hepsiemlak_task(
    self,
    listing_type: str,
    category: str,
    subtype_path: Optional[str],
    cities: List[str],
    districts: Optional[Dict[str, List[str]]],
    max_pages: int = 50
):
    """
    HepsiEmlak scraping task - runs in Celery worker

    Args:
        listing_type: 'satilik' or 'kiralik'
        category: e.g., 'konut', 'arsa'
        subtype_path: Optional subtype URL path
        cities: List of city names
        districts: Optional dict of city -> district list
        max_pages: Maximum pages to scrape per city
    """
    task_id = self.request.id
    progress_manager = TaskProgressManager(task_id)

    logger.info(f"[Task {task_id}] Starting HepsiEmlak scrape: {listing_type}/{category}, cities={cities}")
    progress_manager.update(
        message="HepsiEmlak taraması başlatılıyor...",
        progress=0,
        status="running"
    )

    # Import here to avoid circular imports and ensure proper initialization
    from scrapers.hepsiemlak.main import HepsiemlakScraper
    from core.driver_manager import DriverManager
    from core.failed_pages_tracker import failed_pages_tracker
    from database.connection import get_db_session
    from database import crud

    manager = DriverManager()
    db = None
    scrape_session = None

    try:
        driver = manager.start()
        db = get_db_session()

        # Reset failed pages tracker
        failed_pages_tracker.reset()

        # Extract alt_kategori from subtype_path
        alt_kategori = None
        if subtype_path:
            parts = subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                alt_kategori = parts[-1].replace('-', '_')

        # Create scrape session in database
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

        # Progress callback that updates Redis
        def progress_callback(message, current=0, total=0, progress=0):
            progress_manager.update(
                message=message,
                current=current,
                total=total,
                progress=progress
            )
            # Check for stop request
            if progress_manager.is_stop_requested():
                logger.info(f"[Task {task_id}] Stop requested, raising exception")
                raise StopRequested("User requested stop")

        # Stop checker function for scraper
        def stop_checker():
            return progress_manager.is_stop_requested()

        # Create scraper
        scraper = HepsiemlakScraper(
            driver=driver,
            listing_type=listing_type,
            category=category,
            subtype_path=subtype_path,
            selected_cities=cities,
            selected_districts=districts
        )

        # Set DB session
        scraper.db = db
        scraper.scrape_session_id = scrape_session.id

        logger.info(f"[Task {task_id}] Starting scraping API call")

        # Run scraper with stop checker
        scraper.start_scraping_api(
            max_pages=max_pages,
            progress_callback=progress_callback,
            stop_checker=stop_checker
        )

        # Update session with results
        if scrape_session:
            total_listings = getattr(scraper, 'total_scraped_count', 0)
            new_listings = getattr(scraper, 'new_listings_count', 0)
            duplicate_listings = getattr(scraper, 'duplicate_count', 0)

            crud.update_scrape_session(
                db,
                scrape_session.id,
                total_listings=total_listings,
                new_listings=new_listings,
                duplicate_listings=duplicate_listings
            )
            crud.complete_scrape_session(db, scrape_session.id, status="completed")
            db.commit()

            logger.info(f"[Task {task_id}] Scraping completed: total={total_listings}, new={new_listings}")

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

    except StopRequested:
        logger.info(f"[Task {task_id}] Task stopped by user request")
        progress_manager.set_stopped_early()

        if scrape_session and db:
            crud.complete_scrape_session(db, scrape_session.id, status="stopped")
            db.commit()

        return {
            "status": "stopped",
            "task_id": task_id,
            "message": "Kullanıcı tarafından durduruldu"
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[Task {task_id}] Task exceeded time limit")
        progress_manager.fail("Zaman limiti aşıldı")

        if scrape_session and db:
            crud.complete_scrape_session(db, scrape_session.id, status="timeout")
            db.commit()

        raise

    except Exception as e:
        logger.error(f"[Task {task_id}] Task failed with error: {e}", exc_info=True)
        progress_manager.fail(str(e))

        if scrape_session and db:
            crud.complete_scrape_session(db, scrape_session.id, status="failed", error_message=str(e))
            db.commit()

        raise

    finally:
        if db:
            db.close()
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
    max_pages: int = 50,  # deprecated, kept for backward compat
):
    """
    EmlakJet scraping task - runs in Celery worker
    """
    task_id = self.request.id
    progress_manager = TaskProgressManager(task_id)

    logger.info(f"[Task {task_id}] Starting EmlakJet scrape: {listing_type}/{category}")
    progress_manager.update(
        message="EmlakJet taraması başlatılıyor...",
        progress=0,
        status="running"
    )

    from scrapers.emlakjet.main import EmlakJetScraper
    from core.driver_manager import DriverManager
    from core.config import get_emlakjet_config

    manager = DriverManager()

    try:
        driver = manager.start()
        config = get_emlakjet_config()

        # Build base URL
        if subtype_path:
            base_url = config.base_url + subtype_path
        else:
            category_path = config.categories[listing_type].get(category, '')
            base_url = config.base_url + category_path

        # Progress callback
        def progress_callback(message, current=0, total=0, progress=0):
            progress_manager.update(
                message=message,
                current=current,
                total=total,
                progress=progress
            )
            if progress_manager.is_stop_requested():
                raise StopRequested("User requested stop")

        # Stop checker function for scraper
        def stop_checker():
            return progress_manager.is_stop_requested()

        scraper = EmlakJetScraper(
            driver=driver,
            base_url=base_url,
            category=category,
            listing_type=listing_type,
            subtype_path=subtype_path
        )

        scraper.start_scraping_api(
            cities=cities,
            districts=districts,
            max_listings=max_listings,
            progress_callback=progress_callback,
            stop_checker=stop_checker,
        )

        progress_manager.complete(message="EmlakJet taraması tamamlandı!")

        return {
            "status": "completed",
            "task_id": task_id
        }

    except StopRequested:
        logger.info(f"[Task {task_id}] Task stopped by user")
        progress_manager.set_stopped_early()
        return {"status": "stopped", "task_id": task_id}

    except Exception as e:
        logger.error(f"[Task {task_id}] Task failed: {e}", exc_info=True)
        progress_manager.fail(str(e))
        raise

    finally:
        manager.stop()


class StopRequested(Exception):
    """Exception raised when user requests task stop"""
    pass
