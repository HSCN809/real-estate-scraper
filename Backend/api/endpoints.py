from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from api.schemas import ScrapeRequest, ScrapeResponse
from core.driver_manager import DriverManager
from core.config import get_emlakjet_config, get_hepsiemlak_config
from api.status import task_status
from sqlalchemy.orm import Session
from database.connection import get_db
from database import crud
from database.models import Listing, Location, ScrapeSession
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import os
import io
import redis

# Celery imports
from celery.result import AsyncResult
from tasks.scraping_tasks import scrape_hepsiemlak_task, scrape_emlakjet_task
from celery_app import celery_app

# Redis client for task status
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = None

def get_redis_client():
    """Get or create Redis client"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(REDIS_URL)
            redis_client.ping()  # Test connection
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}. Falling back to in-memory status.")
            return None
    return redis_client

# Districts data directory
DISTRICTS_DIR = Path(__file__).parent.parent / "data" / "districts"

# In-memory cache for district GeoJSON data
_districts_cache: Dict[str, Any] = {}
_districts_index: Optional[Dict[str, Any]] = None

# Import scrapers (will need refactoring to import cleanly)
# We will do dynamic imports or ensure the refactor makes them importable
# from scrapers.emlakjet.main import EmlakJetScraper
# from scrapers.hepsiemlak.main import HepsiemlakScraper

router = APIRouter()
logger = logging.getLogger("api")

# Category name mappings for display
CATEGORY_NAMES = {
    "konut": "Konut",
    "arsa": "Arsa",
    "isyeri": "İşyeri",
    "devremulk": "Devremülk",
    "turistik_isletme": "Turistik İşletme",
    "turistik_tesis": "Turistik Tesis",
    "kat_karsiligi_arsa": "Kat Karşılığı Arsa",
    "devren_isyeri": "Devren İşyeri",
    "gunluk_kiralik": "Günlük Kiralık"
}

@router.get("/config/categories")
async def get_categories():
    """Get all platform categories from config"""
    emlakjet = get_emlakjet_config()
    hepsiemlak = get_hepsiemlak_config()
    
    def format_categories(categories_dict):
        return [
            {"id": k, "name": CATEGORY_NAMES.get(k, k.replace("_", " ").title())}
            for k in categories_dict.keys()
        ]
    
    return {
        "emlakjet": {
            "satilik": format_categories(emlakjet.categories["satilik"]),
            "kiralik": format_categories(emlakjet.categories["kiralik"])
        },
        "hepsiemlak": {
            "satilik": format_categories(hepsiemlak.categories["satilik"]),
            "kiralik": format_categories(hepsiemlak.categories["kiralik"])
        }
    }

@router.get("/config/subtypes")
async def get_subtypes(listing_type: str, category: str, platform: str = "hepsiemlak"):
    """
    Belirli bir kategori için alt tipleri JSON dosyasından oku.
    JSON dosyası yoksa boş liste döner.
    Örnek: /config/subtypes?listing_type=kiralik&category=arsa&platform=hepsiemlak
    """
    if platform == "emlakjet":
        from scrapers.emlakjet.subtype_fetcher import fetch_subtypes, SUBCATEGORIES_JSON_PATH
    else:
        from scrapers.hepsiemlak.subtype_fetcher import fetch_subtypes, SUBCATEGORIES_JSON_PATH

    # JSON dosyasından oku
    subtypes = fetch_subtypes(listing_type, category)

    if not SUBCATEGORIES_JSON_PATH.exists():
        return {
            "subtypes": [],
            "error": f"{platform} subcategories JSON dosyası bulunamadı."
        }

    return {"subtypes": subtypes, "cached": True}

def run_emlakjet_task(request: ScrapeRequest):
    from scrapers.emlakjet.main import EmlakJetScraper

    manager = DriverManager()
    try:
        driver = manager.start()
        config = get_emlakjet_config()

        # Reset and start status
        task_status.reset()
        task_status.set_running(True)
        task_status.update("EmlakJet scraper başlatılıyor...", progress=0)

        def progress_callback(message, current=0, total=0, progress=0):
            task_status.update(message=message, current=current, total=total, progress=progress)

        # Construct base URL based on inputs
        # subtype_path varsa onu kullan, yoksa ana kategori
        if request.subtype_path:
            base_url = config.base_url + request.subtype_path
            logger.info(f"Using subtype path: {request.subtype_path}")
        else:
            category_path = config.categories[request.listing_type].get(request.category, '')
            base_url = config.base_url + category_path

        scraper = EmlakJetScraper(
            driver=driver,
            base_url=base_url,
            category=request.category,
            listing_type=request.listing_type,
            subtype_path=request.subtype_path
        )

        print(f"DEBUG API: listing_type={request.listing_type}, category={request.category}, subtype_path={request.subtype_path}, cities={request.cities}")

        if hasattr(scraper, 'start_scraping_api'):
            scraper.start_scraping_api(
                cities=request.cities,
                districts=request.districts,
                max_pages=request.max_pages,
                progress_callback=progress_callback
            )
        else:
            logger.warning("Scraper api method not found (Refactor needed)")

    except Exception as e:
        logger.error(f"EmlakJet task error: {e}")
    finally:
        task_status.set_running(False)
        task_status.update("İşlem tamamlandı", progress=100)
        manager.stop()

def run_hepsiemlak_task(request: ScrapeRequest):
    from scrapers.hepsiemlak.main import HepsiemlakScraper
    from core.failed_pages_tracker import failed_pages_tracker
    from database.connection import get_db_session
    from database import crud

    manager = DriverManager()
    db = None
    scrape_session = None

    try:
        driver = manager.start()
        db = get_db_session()

        # Reset trackers
        task_status.reset()
        failed_pages_tracker.reset()

        task_status.set_running(True)
        task_status.update("HepsiEmlak scraper başlatılıyor...", progress=0)

        # Alt kategori adını çıkar
        alt_kategori = None
        if request.subtype_path:
            parts = request.subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                alt_kategori = parts[-1].replace('-', '_')

        # Veritabanında scrape session oluştur
        scrape_session = crud.create_scrape_session(
            db,
            platform="hepsiemlak",
            kategori=request.category,
            ilan_tipi=request.listing_type,
            alt_kategori=alt_kategori,
            target_cities=request.cities,
            target_districts=request.districts
        )
        db.commit()
        logger.info(f"ScrapeSession created: ID={scrape_session.id}")

        def progress_callback(message, current=0, total=0, progress=0):
            task_status.update(message=message, current=current, total=total, progress=progress)

        scraper = HepsiemlakScraper(
            driver=driver,
            listing_type=request.listing_type,
            category=request.category,
            subtype_path=request.subtype_path,
            selected_cities=request.cities,
            selected_districts=request.districts
        )

        # Scraper'a DB session'ı ve session_id'yi ekle
        scraper.db = db
        scraper.scrape_session_id = scrape_session.id

        print(f"DEBUG API: listing_type={request.listing_type}, category={request.category}, subtype_path={request.subtype_path}, cities={request.cities}")

        if hasattr(scraper, 'start_scraping_api'):
            scraper.start_scraping_api(max_pages=request.max_pages, progress_callback=progress_callback)
        else:
            logger.warning("Scraper api method not found (Refactor needed)")

        # Scrape tamamlandıktan sonra session'ı güncelle
        if scrape_session:
            # Scraper'dan toplam ilan sayısını al
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
            logger.info(f"ScrapeSession completed: ID={scrape_session.id}, total={total_listings}")

    except Exception as e:
        logger.error(f"HepsiEmlak task error: {e}")
        if scrape_session and db:
            crud.complete_scrape_session(db, scrape_session.id, status="failed", error_message=str(e))
            db.commit()
    finally:
        task_status.set_running(False)
        task_status.update("İşlem tamamlandı", progress=100)
        if db:
            db.close()
        manager.stop()

@router.post("/scrape/emlakjet", response_model=ScrapeResponse)
async def scrape_emlakjet(request: ScrapeRequest):
    """Start EmlakJet scraping task via Celery"""
    # Submit task to Celery
    task = scrape_emlakjet_task.apply_async(
        kwargs={
            "listing_type": request.listing_type,
            "category": request.category,
            "subtype_path": request.subtype_path,
            "cities": request.cities,
            "districts": request.districts,
            "max_pages": request.max_pages
        },
        queue="scraping"
    )

    # Initialize task status in Redis
    r = get_redis_client()
    if r:
        initial_status = {
            "task_id": task.id,
            "status": "pending",
            "message": "EmlakJet taraması başlatılıyor...",
            "progress": 0,
            "current": 0,
            "total": 0,
            "details": "",
            "started_at": datetime.now().isoformat(),
            "should_stop": False,
            "stopped_early": False,
        }
        r.setex(f"scrape_task:{task.id}", 86400, json.dumps(initial_status))

    # Also update in-memory status for backward compatibility
    task_status.reset()
    task_status.set_running(True)
    task_status.update("EmlakJet taraması başlatılıyor...", progress=0)

    return ScrapeResponse(
        status="accepted",
        message="EmlakJet scraping task started",
        task_id=task.id,
        data_count=0,
        output_files=[]
    )

@router.post("/scrape/hepsiemlak", response_model=ScrapeResponse)
async def scrape_hepsiemlak(request: ScrapeRequest):
    """Start HepsiEmlak scraping task via Celery"""
    # Validate cities
    if not request.cities or len(request.cities) == 0:
        raise HTTPException(status_code=400, detail="En az bir şehir seçmelisiniz")

    # Validate districts if provided
    if request.districts:
        for city, districts in request.districts.items():
            if city not in request.cities:
                raise HTTPException(
                    status_code=400,
                    detail=f"İlçe seçilen şehir ({city}) şehir listesinde yok"
                )

    # Submit task to Celery
    task = scrape_hepsiemlak_task.apply_async(
        kwargs={
            "listing_type": request.listing_type,
            "category": request.category,
            "subtype_path": request.subtype_path,
            "cities": request.cities,
            "districts": request.districts,
            "max_pages": request.max_pages
        },
        queue="scraping"
    )

    # Initialize task status in Redis
    r = get_redis_client()
    if r:
        initial_status = {
            "task_id": task.id,
            "status": "pending",
            "message": "HepsiEmlak taraması başlatılıyor...",
            "progress": 0,
            "current": 0,
            "total": 0,
            "details": "",
            "started_at": datetime.now().isoformat(),
            "should_stop": False,
            "stopped_early": False,
        }
        r.setex(f"scrape_task:{task.id}", 86400, json.dumps(initial_status))

    # Also update in-memory status for backward compatibility
    task_status.reset()
    task_status.set_running(True)
    task_status.update("HepsiEmlak taraması başlatılıyor...", progress=0)

    return ScrapeResponse(
        status="accepted",
        message="HepsiEmlak scraping task started",
        task_id=task.id,
        data_count=0,
        output_files=[]
    )

@router.post("/stop")
async def stop_scraping(task_id: Optional[str] = None):
    """Aktif tarama işlemini durdur ve mevcut verileri kaydet"""
    r = get_redis_client()

    # If task_id provided, stop that specific task
    if task_id and r:
        key = f"scrape_task:{task_id}"
        data = r.get(key)
        if data:
            data = json.loads(data)
            data["should_stop"] = True
            data["message"] = "Durdurma isteği alındı, mevcut veriler kaydediliyor..."
            r.setex(key, 86400, json.dumps(data))
            return {
                "status": "stopping",
                "message": "Durdurma isteği gönderildi. Mevcut veriler kaydediliyor...",
                "task_id": task_id
            }

    # Try to find and stop active task from Redis
    if r:
        for key in r.scan_iter("scrape_task:*"):
            data = r.get(key)
            if data:
                data = json.loads(data)
                if data.get("status") == "running":
                    data["should_stop"] = True
                    data["message"] = "Durdurma isteği alındı, mevcut veriler kaydediliyor..."
                    r.setex(key, 86400, json.dumps(data))
                    return {
                        "status": "stopping",
                        "message": "Durdurma isteği gönderildi. Mevcut veriler kaydediliyor...",
                        "task_id": data.get("task_id")
                    }

    # Fallback to in-memory status
    if task_status.is_running:
        task_status.request_stop()
        return {"status": "stopping", "message": "Durdurma isteği gönderildi. Mevcut veriler kaydediliyor..."}
    else:
        return {"status": "idle", "message": "Aktif bir tarama işlemi yok."}

@router.get("/analytics/prices")
async def get_price_analytics(
    platform: str = None,
    category: str = None,
    listing_type: str = None,
    db: Session = Depends(get_db)
):
    """Veritabanından fiyat verilerini çek - grafikler için (filtrelenebilir)"""
    # Platform/category/listing_type mapping for display names
    platform_map = {"hepsiemlak": "HepsiEmlak", "emlakjet": "Emlakjet"}
    category_map = {"konut": "Konut", "arsa": "Arsa", "isyeri": "İşyeri", "devremulk": "Devremülk"}
    listing_type_map = {"satilik": "Satılık", "kiralik": "Kiralık"}

    # Convert display names back to db values for filtering
    db_platform = None
    db_category = None
    db_listing_type = None

    if platform and platform != "all":
        db_platform = platform.lower().replace("hepsiemlak", "hepsiemlak").replace("emlakjet", "emlakjet")
        if platform == "HepsiEmlak":
            db_platform = "hepsiemlak"
        elif platform == "Emlakjet":
            db_platform = "emlakjet"

    if category and category != "all":
        for k, v in category_map.items():
            if v == category:
                db_category = k
                break
        if not db_category:
            db_category = category.lower()

    if listing_type and listing_type != "all":
        for k, v in listing_type_map.items():
            if v == listing_type:
                db_listing_type = k
                break
        if not db_listing_type:
            db_listing_type = listing_type.lower()

    result = crud.get_price_analytics(
        db,
        platform=db_platform,
        kategori=db_category,
        ilan_tipi=db_listing_type
    )

    # Transform to display names
    prices = []
    for p in result["prices"]:
        prices.append({
            "city": p["city"],
            "platform": platform_map.get(p["platform"], p["platform"]),
            "category": category_map.get(p["category"], p["category"]),
            "listing_type": listing_type_map.get(p["listing_type"], p["listing_type"]),
            "price": p["price"]
        })

    return {"prices": prices, "summary": result["summary"]}

@router.get("/analytics/city/{city_name}")
async def get_city_analytics(
    city_name: str,
    platform: str = None,
    category: str = None,
    listing_type: str = None,
    subtype: str = None,
    db: Session = Depends(get_db)
):
    """Veritabanından belirli bir şehrin ilanlarını ve istatistiklerini döndür"""
    # Convert display names to db values
    db_platform = None
    db_category = None
    db_listing_type = None

    if platform and platform != "all":
        if platform == "HepsiEmlak":
            db_platform = "hepsiemlak"
        elif platform == "Emlakjet":
            db_platform = "emlakjet"
        else:
            db_platform = platform.lower()

    if category and category != "all":
        category_map = {"Konut": "konut", "Arsa": "arsa", "İşyeri": "isyeri", "Devremülk": "devremulk"}
        db_category = category_map.get(category, category.lower())

    if listing_type and listing_type != "all":
        listing_map = {"Satılık": "satilik", "Kiralık": "kiralik"}
        db_listing_type = listing_map.get(listing_type, listing_type.lower())

    return crud.get_city_analytics(
        db,
        city_name=city_name,
        platform=db_platform,
        kategori=db_category,
        ilan_tipi=db_listing_type
    )

@router.get("/analytics/stats")
async def get_listing_statistics(
    platform: str = None,
    kategori: str = None,
    ilan_tipi: str = None,
    city: str = None,
    district: str = None,
    db: Session = Depends(get_db)
):
    """Veritabanından detaylı istatistikler - describe + fiyat aralıkları"""
    import statistics

    # Build query
    query = db.query(Listing.fiyat).filter(Listing.fiyat.isnot(None), Listing.fiyat > 0)

    # Apply filters
    if platform and platform != "all":
        platform_map = {"HepsiEmlak": "hepsiemlak", "Emlakjet": "emlakjet"}
        db_platform = platform_map.get(platform, platform.lower())
        query = query.filter(Listing.platform == db_platform)

    if kategori and kategori != "all":
        category_map = {"Konut": "konut", "Arsa": "arsa", "İşyeri": "isyeri", "Devremülk": "devremulk"}
        db_kategori = category_map.get(kategori, kategori.lower())
        query = query.filter(Listing.kategori == db_kategori)

    if ilan_tipi and ilan_tipi != "all":
        type_map = {"Satılık": "satilik", "Kiralık": "kiralik"}
        db_type = type_map.get(ilan_tipi, ilan_tipi.lower())
        query = query.filter(Listing.ilan_tipi == db_type)

    # City/district filter
    if city or district:
        location_query = db.query(Location.id)
        if city and city != "Belirtilmemiş":
            location_query = location_query.filter(Location.il == city)
        if district and district != "Belirtilmemiş":
            location_query = location_query.filter(Location.ilce == district)
        location_ids = [loc_id for (loc_id,) in location_query.all()]
        if location_ids:
            query = query.filter(Listing.location_id.in_(location_ids))

    # Get prices
    prices = [p[0] for p in query.all()]

    if not prices:
        return {"error": "Fiyat verisi bulunamadı", "stats": None}

    # Sort prices for percentile calculations
    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    # Calculate percentiles (quartiles)
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if c < len(data) else data[f]

    # Descriptive statistics (like pandas describe)
    describe_stats = {
        "count": n,
        "mean": round(statistics.mean(prices), 2),
        "std": round(statistics.stdev(prices), 2) if n > 1 else 0,
        "min": round(min(prices), 2),
        "q25": round(percentile(sorted_prices, 25), 2),
        "median": round(statistics.median(prices), 2),
        "q75": round(percentile(sorted_prices, 75), 2),
        "max": round(max(prices), 2)
    }

    # Dynamic price range distribution using quantile-based binning
    num_bins = 5
    bin_edges = [percentile(sorted_prices, i * 100 / num_bins) for i in range(num_bins + 1)]

    # Ensure unique edges
    unique_edges = []
    for e in bin_edges:
        if not unique_edges or e > unique_edges[-1]:
            unique_edges.append(e)

    # If not enough unique edges, fall back to equal-width bins
    if len(unique_edges) < 3:
        min_p, max_p = min(prices), max(prices)
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]

    # Count items in each bin
    price_ranges = []
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]

        # Format the range label
        def format_price(p):
            if p >= 1000000:
                return f"{p/1000000:.1f}M"
            elif p >= 1000:
                return f"{p/1000:.0f}K"
            else:
                return f"{p:.0f}"

        label = f"{format_price(low)} - {format_price(high)}"

        # Count items in range
        if i == len(unique_edges) - 2:  # Last bin includes upper edge
            count = sum(1 for p in prices if low <= p <= high)
        else:
            count = sum(1 for p in prices if low <= p < high)

        price_ranges.append({
            "range": label,
            "count": count,
            "percentage": round(count / n * 100, 1)
        })

    return {
        "stats": describe_stats,
        "price_ranges": price_ranges,
        "total_listings": n
    }

@router.delete("/clear-results")
async def clear_results(db: Session = Depends(get_db)):
    """Veritabanındaki tüm ilanları ve outputs klasöründeki dosyaları sil"""
    import os
    import shutil

    deleted_listings = 0
    deleted_files = 0

    # 1. Veritabanındaki tüm ilanları sil
    try:
        deleted_listings = db.query(Listing).delete()
        # ScrapeSession'ları da sil
        db.query(ScrapeSession).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"Veritabanı temizleme hatası: {str(e)}", "deleted_listings": 0, "deleted_files": 0}

    # 2. Outputs klasöründeki dosyaları da sil
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    output_dir = os.path.join(project_root, "outputs")

    if not os.path.exists(output_dir):
        output_dir = os.path.join(project_root, "Outputs")

    if os.path.exists(output_dir):
        try:
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    deleted_files += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    deleted_files += 1
        except Exception as e:
            logger.warning(f"Dosya silme hatası: {e}")

    return {
        "status": "success",
        "message": f"{deleted_listings} ilan ve {deleted_files} dosya/klasör silindi",
        "deleted_listings": deleted_listings,
        "deleted_files": deleted_files
    }



@router.get("/results")
async def get_results(db: Session = Depends(get_db)):
    """
    Veritabanından sonuçları döndür.
    Şehir/platform/kategori bazında gruplanmış ilan özetleri.
    """
    return crud.get_results_for_frontend(db)

@router.get("/listings/preview")
async def get_listings_preview(
    platform: str = None,
    kategori: str = None,
    ilan_tipi: str = None,
    city: str = None,
    district: str = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Veritabanından filtrelenmiş ilanların önizlemesini döndür"""
    listings, total = crud.get_listings(
        db,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        city=city,
        district=district,
        page=1,
        limit=limit
    )

    data = [l.to_dict() for l in listings]
    return {"data": data, "total": total, "showing": len(data)}

@router.get("/status")
async def get_status(task_id: Optional[str] = None):
    """Get task status - supports both Redis-based Celery tasks and in-memory status"""
    r = get_redis_client()

    # If task_id provided, get that specific task
    if task_id and r:
        key = f"scrape_task:{task_id}"
        data = r.get(key)
        if data:
            status_data = json.loads(data)
            # Map status to is_running for frontend compatibility
            status_data["is_running"] = status_data.get("status") in ["pending", "running"]
            return status_data
        else:
            # Task ID verildi ama Redis'te bulunamadı - henüz başlamamış demek
            # "pending" olarak dön, başka task'ın status'unu dönme!
            return {
                "task_id": task_id,
                "status": "pending",
                "is_running": True,
                "message": "Task başlatılıyor...",
                "progress": 0,
                "current": 0,
                "total": 0,
                "details": ""
            }

    # task_id yoksa: Try to find active task from Redis
    if r:
        for key in r.scan_iter("scrape_task:*"):
            data = r.get(key)
            if data:
                status_data = json.loads(data)
                if status_data.get("status") in ["pending", "running"]:
                    status_data["is_running"] = True
                    return status_data

    # Fallback to in-memory status
    return task_status.to_dict()


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get detailed status for a specific Celery task"""
    r = get_redis_client()

    # Get from Redis
    if r:
        key = f"scrape_task:{task_id}"
        data = r.get(key)
        if data:
            status_data = json.loads(data)
            status_data["is_running"] = status_data.get("status") in ["pending", "running"]
            return status_data

    # Get from Celery directly
    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.status,
        "is_running": result.status in ["PENDING", "STARTED", "PROGRESS"],
        "result": result.result if result.ready() else None,
        "info": result.info if hasattr(result, 'info') else None
    }


@router.get("/tasks/active")
async def get_active_tasks():
    """Get all active/pending tasks"""
    r = get_redis_client()
    active_tasks = []

    if r:
        for key in r.scan_iter("scrape_task:*"):
            data = r.get(key)
            if data:
                status_data = json.loads(data)
                if status_data.get("status") in ["pending", "running"]:
                    active_tasks.append(status_data)

    return {"active_tasks": active_tasks, "count": len(active_tasks)}

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Veritabanından genel istatistikleri döndür"""
    return crud.get_stats_summary(db)



# ==================== NEW DB-BASED ENDPOINTS ====================

@router.get("/listings")
async def get_listings(
    platform: str = None,
    kategori: str = None,
    ilan_tipi: str = None,
    alt_kategori: str = None,
    city: str = None,
    district: str = None,
    min_price: float = None,
    max_price: float = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Veritabanından ilanları listele (filtre ve pagination destekli)"""
    listings, total = crud.get_listings(
        db,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        city=city,
        district=district,
        min_price=min_price,
        max_price=max_price,
        page=page,
        limit=limit
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "items": [l.to_dict() for l in listings]
    }


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Tek bir ilan detayını getir"""
    listing = crud.get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")
    return listing.to_dict()


@router.get("/sessions")
async def get_scrape_sessions(
    platform: str = None,
    status: str = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Tarama oturumlarını listele"""
    sessions, total = crud.get_scrape_sessions(
        db,
        platform=platform,
        status=status,
        page=page,
        limit=limit
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [s.to_dict() for s in sessions]
    }


@router.get("/cities")
async def get_cities(db: Session = Depends(get_db)):
    """Veritabanındaki tüm şehirleri listele"""
    cities = crud.get_all_cities(db)
    return {"cities": cities}


@router.get("/cities/{city}/districts")
async def get_districts(city: str, db: Session = Depends(get_db)):
    """Bir şehrin ilçelerini listele"""
    districts = crud.get_districts_by_city(db, city)
    return {"city": city, "districts": districts}


@router.post("/export/excel")
async def export_to_excel(
    platform: str = None,
    kategori: str = None,
    ilan_tipi: str = None,
    city: str = None,
    district: str = None,
    db: Session = Depends(get_db)
):
    """Filtrelere göre verileri Excel'e aktar ve indir"""
    import pandas as pd
    from datetime import datetime as dt

    # Get listings (max 10000 for export)
    listings, total = crud.get_listings(
        db,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        city=city,
        district=district,
        page=1,
        limit=10000
    )

    if not listings:
        raise HTTPException(status_code=404, detail="Dışa aktarılacak veri bulunamadı")

    # Convert to dataframe
    data = []
    for l in listings:
        row = {
            "Başlık": l.baslik,
            "Fiyat": l.fiyat_text or l.fiyat,
            "Platform": l.platform,
            "Kategori": l.kategori,
            "İlan Tipi": l.ilan_tipi,
            "Alt Kategori": l.alt_kategori,
            "İl": l.location.il if l.location else "",
            "İlçe": l.location.ilce if l.location else "",
            "Mahalle": l.location.mahalle if l.location else "",
            "İlan URL": l.ilan_url,
            "Emlak Ofisi": l.emlak_ofisi,
            "Tarih": l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
        }
        # Add details
        if l.details:
            for k, v in l.details.items():
                row[k] = v
        data.append(row)

    df = pd.DataFrame(data)

    # Create temp file
    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    filename = f"export_{timestamp}.xlsx"

    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    output_dir = os.path.join(project_root, "outputs", "exports")
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, filename)
    df.to_excel(filepath, index=False, engine='openpyxl')

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.delete("/listings/group")
async def delete_listing_group(
    platform: str = Query(default=None),
    kategori: str = Query(default=None),
    ilan_tipi: str = Query(default=None),
    city: str = Query(default=None),
    district: str = Query(default=None),
    alt_kategori: str = Query(default=None),
    db: Session = Depends(get_db)
):
    """Filtrelere göre ilan grubunu sil"""
    from database.models import Listing, Location

    query = db.query(Listing)

    # Platform filter (convert display name to db name)
    if platform:
        platform_map = {"HepsiEmlak": "hepsiemlak", "Emlakjet": "emlakjet"}
        db_platform = platform_map.get(platform, platform.lower())
        query = query.filter(Listing.platform == db_platform)

    # Category filter
    if kategori:
        category_map = {"Konut": "konut", "Arsa": "arsa", "İşyeri": "isyeri",
                       "Devremülk": "devremulk", "Turistik İşletme": "turistik_isletme"}
        db_kategori = category_map.get(kategori, kategori.lower())
        query = query.filter(Listing.kategori == db_kategori)

    # Listing type filter
    if ilan_tipi:
        type_map = {"Satılık": "satilik", "Kiralık": "kiralik"}
        db_type = type_map.get(ilan_tipi, ilan_tipi.lower())
        query = query.filter(Listing.ilan_tipi == db_type)

    # Alt kategori filter
    if alt_kategori:
        # Convert "Cafe Bar" to "cafe_bar"
        db_alt = alt_kategori.lower().replace(' ', '_')
        query = query.filter(Listing.alt_kategori == db_alt)

    # City/district filter - get location IDs first
    if city or district:
        location_query = db.query(Location.id)
        if city and city != "Belirtilmemiş":
            location_query = location_query.filter(Location.il == city)
        if district and district != "Belirtilmemiş":
            location_query = location_query.filter(Location.ilce == district)
        location_ids = [loc_id for (loc_id,) in location_query.all()]
        if location_ids:
            query = query.filter(Listing.location_id.in_(location_ids))
        else:
            raise HTTPException(status_code=404, detail="Silinecek ilan bulunamadı")

    # Get count and delete
    count = query.count()
    if count == 0:
        raise HTTPException(status_code=404, detail="Silinecek ilan bulunamadı")

    query.delete(synchronize_session=False)
    db.commit()

    return {"status": "success", "message": f"{count} ilan silindi", "deleted_count": count}


@router.delete("/listings/{listing_id}")
async def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    """Bir ilanı sil"""
    listing = crud.get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    db.delete(listing)
    db.commit()

    return {"status": "success", "message": f"İlan {listing_id} silindi"}


# ==================== DISTRICTS GeoJSON ENDPOINTS ====================

def _load_districts_index() -> Dict[str, Any]:
    """Load and cache the districts index.json"""
    global _districts_index
    if _districts_index is not None:
        return _districts_index

    index_path = DISTRICTS_DIR / "index.json"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Districts index not found")

    with open(index_path, "r", encoding="utf-8") as f:
        _districts_index = json.load(f)

    return _districts_index


def _load_district_geojson(province_name: str) -> Dict[str, Any]:
    """Load and cache a province's GeoJSON data"""
    # Check cache first
    if province_name in _districts_cache:
        return _districts_cache[province_name]

    # Get filename from index
    index = _load_districts_index()
    province_info = index.get(province_name)

    if not province_info:
        raise HTTPException(status_code=404, detail=f"Province '{province_name}' not found in index")

    filename = province_info.get("file")
    if not filename:
        raise HTTPException(status_code=404, detail=f"No file specified for province '{province_name}'")

    filepath = DISTRICTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"GeoJSON file not found: {filename}")

    with open(filepath, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # Cache it
    _districts_cache[province_name] = geojson_data

    return geojson_data


@router.get("/districts/index")
async def get_districts_index():
    """Get the districts index with all provinces and their district counts"""
    return _load_districts_index()


@router.get("/districts/{province_name}")
async def get_district_geojson(province_name: str):
    """
    Get GeoJSON data for a specific province's districts.
    Uses in-memory caching for fast subsequent requests.
    """
    return _load_district_geojson(province_name)


@router.get("/districts/info/{province_name}")
async def get_district_info(province_name: str):
    """Get district list and metadata for a province (without full GeoJSON geometry)"""
    index = _load_districts_index()
    province_info = index.get(province_name)

    if not province_info:
        raise HTTPException(status_code=404, detail=f"Province '{province_name}' not found")

    return {
        "province": province_name,
        "file": province_info.get("file"),
        "count": province_info.get("count"),
        "districts": province_info.get("districts", [])
    }


@router.post("/districts/cache/clear")
async def clear_districts_cache():
    """Clear the in-memory districts cache (admin endpoint)"""
    global _districts_cache, _districts_index
    cache_size = len(_districts_cache)
    _districts_cache = {}
    _districts_index = None
    return {"status": "success", "message": f"Cache cleared. {cache_size} provinces removed from cache."}


@router.get("/districts/cache/status")
async def get_cache_status():
    """Get current cache status"""
    return {
        "cached_provinces": list(_districts_cache.keys()),
        "cache_size": len(_districts_cache),
        "index_loaded": _districts_index is not None
    }
