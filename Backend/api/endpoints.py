# -*- coding: utf-8 -*-
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas import (
    ActiveTasksResponse,
    ScrapeRequest,
    ScrapeStartResponse,
    SUPPORTED_SCRAPING_METHODS,
    TaskStatusResponse,
)
from core.config import get_emlakjet_config, get_hepsiemlak_config
from core.task_status import get_task_status_store
from database.connection import get_db
from database import crud
from database.models import FailedPage, Listing, Location, PriceHistory, ScrapeSession
from tasks.scraping_tasks import scrape_emlakjet_task, scrape_hepsiemlak_task
import io
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# İlçe verileri dizini
DISTRICTS_DIR = Path(__file__).parent.parent / "data" / "districts"

# İlçe GeoJSON verileri için bellek içi önbellek
_districts_cache: Dict[str, Any] = {}
_districts_index: Optional[Dict[str, Any]] = None

router = APIRouter()
logger = logging.getLogger("api")

# Görüntüleme için kategori adı eşlemeleri
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


def _validate_scraping_method_or_raise(scraping_method: str) -> None:
    if scraping_method == "go_proxy":
        raise HTTPException(
            status_code=400,
            detail=(
                "scraping_method='go_proxy' artik desteklenmiyor. "
                "Bir scraping yontemi secip proxy_enabled=true gonderin."
            ),
        )
    if scraping_method not in SUPPORTED_SCRAPING_METHODS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Gecersiz scraping_method: {scraping_method}. "
                f"Desteklenenler: {', '.join(SUPPORTED_SCRAPING_METHODS)}"
            ),
        )


def _require_task_status_store():
    try:
        return get_task_status_store()
    except Exception as exc:
        logger.error("Task status store unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="Task status store unavailable") from exc


def _enqueue_scrape_task(task_callable, *, kwargs: Dict[str, Any], message: str, platform: str) -> TaskStatusResponse:
    store = _require_task_status_store()
    task_id = uuid4().hex
    task_callable.apply_async(kwargs=kwargs, queue="scraping", task_id=task_id)
    payload = store.create_queued_task(task_id, message=message, platform=platform)
    return TaskStatusResponse(**payload)


@router.get("/config/categories")
async def get_categories():
    """Tüm platform kategorilerini getir"""
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
    """Belirli kategori için alt tipleri JSON'dan oku"""
    if platform == "emlakjet":
        from scrapers.emlakjet.subtype_fetcher import SUBCATEGORIES_JSON_PATH, fetch_subtypes
    else:
        from scrapers.hepsiemlak.subtype_fetcher import SUBCATEGORIES_JSON_PATH, fetch_subtypes

    subtypes = fetch_subtypes(listing_type, category)

    if not SUBCATEGORIES_JSON_PATH.exists():
        return {
            "subtypes": [],
            "error": f"{platform} subcategories JSON dosyası bulunamadı."
        }

    return {"subtypes": subtypes, "cached": True}


@router.post("/scrape/emlakjet", response_model=ScrapeStartResponse)
async def scrape_emlakjet(request: ScrapeRequest):
    """Celery ile EmlakJet tarama görevi başlat."""
    _validate_scraping_method_or_raise(request.scraping_method)

    task_status = _enqueue_scrape_task(
        scrape_emlakjet_task,
        kwargs={
            "listing_type": request.listing_type,
            "category": request.category,
            "subtype_path": request.subtype_path,
            "cities": request.cities,
            "districts": request.districts,
            "max_listings": request.max_listings or 0,
            "max_pages": request.max_pages or 50,
            "scraping_method": request.scraping_method,
            "proxy_enabled": request.proxy_enabled,
        },
        message="EmlakJet taraması sıraya alındı.",
        platform="emlakjet",
    )

    return ScrapeStartResponse(
        task_id=task_status.task_id,
        status=task_status.status,
        message=task_status.message,
    )


@router.post("/scrape/hepsiemlak", response_model=ScrapeStartResponse)
async def scrape_hepsiemlak(request: ScrapeRequest):
    """Celery ile HepsiEmlak tarama görevi başlat."""
    _validate_scraping_method_or_raise(request.scraping_method)
    if not request.cities:
        raise HTTPException(status_code=400, detail="En az bir şehir seçmelisiniz")

    if request.districts:
        for city, districts in request.districts.items():
            if city not in request.cities:
                raise HTTPException(
                    status_code=400,
                    detail=f"İlçe seçilen şehir ({city}) şehir listesinde yok"
                )

    task_status = _enqueue_scrape_task(
        scrape_hepsiemlak_task,
        kwargs={
            "listing_type": request.listing_type,
            "category": request.category,
            "subtype_path": request.subtype_path,
            "cities": request.cities,
            "districts": request.districts,
            "max_pages": request.max_pages,
            "scraping_method": request.scraping_method,
            "proxy_enabled": request.proxy_enabled,
        },
        message="HepsiEmlak taraması sıraya alındı.",
        platform="hepsiemlak",
    )

    return ScrapeStartResponse(
        task_id=task_status.task_id,
        status=task_status.status,
        message=task_status.message,
    )


@router.get("/tasks/active", response_model=ActiveTasksResponse)
async def get_active_tasks():
    """Tüm aktif görevleri al."""
    store = _require_task_status_store()
    tasks = [TaskStatusResponse(**item) for item in store.get_active_tasks()]
    return ActiveTasksResponse(active_tasks=tasks, count=len(tasks))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Belirli bir scraping görevinin kanonik durumunu al."""
    store = _require_task_status_store()
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(**task)


@router.get("/analytics/prices")
async def get_price_analytics(
    platform: str = None,
    category: str = None,
    listing_type: str = None,
    db: Session = Depends(get_db)
):
    """Veritabanından fiyat verilerini çek - grafikler için (filtrelenebilir)"""
    # Goruntuleme adlari icin platform/kategori/ilan tipi eslemeleri
    platform_map = {"hepsiemlak": "HepsiEmlak", "emlakjet": "Emlakjet"}
    category_map = {"konut": "Konut", "arsa": "Arsa", "isyeri": "İşyeri", "devremulk": "Devremülk"}
    listing_type_map = {"satilik": "Satılık", "kiralik": "Kiralık"}

    # Filtreleme icin goruntuleme adlarini DB degerlerine cevir
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

    # Goruntuleme adlarina donustur
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
    """Veritabanindan belirli bir sehrin ilanlarini ve istatistiklerini dondur."""
    # Goruntuleme adlarini DB degerlerine cevir
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

    # Sorgu olustur
    query = db.query(Listing.fiyat).filter(Listing.fiyat.isnot(None), Listing.fiyat > 0)

    # Filtreleri uygula
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

    # Şehir/ilçe filtresi
    if city or district:
        location_query = db.query(Location.id)
        if city and city != "Belirtilmemiş":
            location_query = location_query.filter(Location.il == city)
        if district and district != "Belirtilmemiş":
            location_query = location_query.filter(Location.ilce == district)
        location_ids = [loc_id for (loc_id,) in location_query.all()]
        if location_ids:
            query = query.filter(Listing.location_id.in_(location_ids))

    # Fiyatları al
    prices = [p[0] for p in query.all()]

    if not prices:
        return {"error": "Fiyat verisi bulunamadı", "stats": None}

    # Yüzdelik hesaplamaları için fiyatları sırala
    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    # Yüzdelikleri (çeyreklikleri) hesapla
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if c < len(data) else data[f]

    # Tanımlayıcı istatistikler (pandas describe benzeri)
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

    # Yuzdelik tabanli gruplama ile dinamik fiyat araligi dagilimi
    num_bins = 5
    bin_edges = [percentile(sorted_prices, i * 100 / num_bins) for i in range(num_bins + 1)]

    # Benzersiz kenarlari sagla
    unique_edges = []
    for e in bin_edges:
        if not unique_edges or e > unique_edges[-1]:
            unique_edges.append(e)

    # Yeterli benzersiz kenar yoksa esit genislikli gruplara don
    if len(unique_edges) < 3:
        min_p, max_p = min(prices), max(prices)
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]

    # Her gruptaki ogeleri say
    price_ranges = []
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]

        # Aralık etiketini biçimlendir
        def format_price(p):
            if p >= 1000000:
                return f"{p/1000000:.1f}M"
            elif p >= 1000:
                return f"{p/1000:.0f}K"
            else:
                return f"{p:.0f}"

        label = f"{format_price(low)} - {format_price(high)}"

        # Araliktaki ogeleri say
        if i == len(unique_edges) - 2:  # Son grup üst sınırı dahil eder
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
    """Veritabanindaki tum ilanlari ve outputs klasorundeki dosyalari sil"""
    import os
    import shutil

    deleted_failed_pages = 0
    deleted_price_history = 0
    deleted_listings = 0
    deleted_sessions = 0
    deleted_files = 0

    # 1. Delete database records in FK-safe order
    try:
        deleted_failed_pages = db.query(FailedPage).delete(synchronize_session=False)
        deleted_price_history = db.query(PriceHistory).delete(synchronize_session=False)
        deleted_listings = db.query(Listing).delete(synchronize_session=False)
        deleted_sessions = db.query(ScrapeSession).delete(synchronize_session=False)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Veritabani temizleme hatasi: {str(e)}"
        )

    # 2. Outputs klasorundeki dosyalari da sil
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
            logger.warning(f"Dosya silme hatasi: {e}")

    return {
        "status": "success",
        "message": (
            f"{deleted_failed_pages} failed page, "
            f"{deleted_price_history} fiyat gecmisi, "
            f"{deleted_listings} ilan, "
            f"{deleted_sessions} oturum ve "
            f"{deleted_files} dosya/klasor silindi"
        ),
        "deleted_failed_pages": deleted_failed_pages,
        "deleted_price_history": deleted_price_history,
        "deleted_listings": deleted_listings,
        "deleted_sessions": deleted_sessions,
        "deleted_files": deleted_files,
    }


@router.get("/results")
async def get_results(db: Session = Depends(get_db)):
    """Veritabanından sonuçları döndür"""
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
    """Veritabanindan filtrelenmis ilanlarin onizlemesini dondur."""
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
    """Veritabanindaki tum sehirleri listele."""
    cities = crud.get_all_cities(db)
    return {"cities": cities}


@router.get("/cities/{city}/districts")
async def get_districts(city: str, db: Session = Depends(get_db)):
    """Bir sehrin ilcelerini listele."""
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

    # Ilanlari al (disa aktarim icin maks 10000)
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

    # DataFrame'e donustur
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

    # Bellekte olustur, diske yazmadan stream olarak gonder
    from fastapi.responses import StreamingResponse

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    filename = f"export_{timestamp}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
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

    # Platform filtresi (goruntulenen adi veritabani adina donustur)
    if platform:
        platform_map = {"HepsiEmlak": "hepsiemlak", "Emlakjet": "emlakjet"}
        db_platform = platform_map.get(platform, platform.lower())
        query = query.filter(Listing.platform == db_platform)

    # Kategori filtresi
    if kategori:
        category_map = {"Konut": "konut", "Arsa": "arsa", "İşyeri": "isyeri",
                       "Devremülk": "devremulk", "Turistik İşletme": "turistik_isletme"}
        db_kategori = category_map.get(kategori, kategori.lower())
        query = query.filter(Listing.kategori == db_kategori)

    # İlan tipi filtresi
    if ilan_tipi:
        type_map = {"Satılık": "satilik", "Kiralık": "kiralik"}
        db_type = type_map.get(ilan_tipi, ilan_tipi.lower())
        query = query.filter(Listing.ilan_tipi == db_type)

    # Alt kategori filtresi
    if alt_kategori:
        # "Cafe Bar" -> "cafe_bar" donusumu
        db_alt = alt_kategori.lower().replace(' ', '_')
        query = query.filter(Listing.alt_kategori == db_alt)

    # Şehir/ilçe filtresi - önce lokasyon ID'lerini al
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

    # Sayıyı al ve sil
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


# ==================== ILCE GEOJSON ENDPOINTLER ====================

def _load_districts_index() -> Dict[str, Any]:
    """Ilce index.json dosyasini yukle ve onbellege al."""
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
    """Il GeoJSON verisini yukle ve onbellege al."""
    # Once onbellekte kontrol et
    if province_name in _districts_cache:
        return _districts_cache[province_name]

    # Index'ten dosya adını al
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

    # Onbellege al
    _districts_cache[province_name] = geojson_data

    return geojson_data


@router.get("/districts/index")
async def get_districts_index():
    """Tüm illerin ilçe sayılarıyla index'ini getir"""
    return _load_districts_index()


@router.get("/districts/{province_name}")
async def get_district_geojson(province_name: str):
    """Belirli bir ilin ilçe GeoJSON verisini getir"""
    return _load_district_geojson(province_name)


@router.get("/districts/info/{province_name}")
async def get_district_info(province_name: str):
    """İl için ilçe listesini ve meta verilerini getir"""
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
    """Bellek ici ilce onbelleğini temizle."""
    global _districts_cache, _districts_index
    cache_size = len(_districts_cache)
    _districts_cache = {}
    _districts_index = None
    return {"status": "success", "message": f"Cache cleared. {cache_size} provinces removed from cache."}


@router.get("/districts/cache/status")
async def get_cache_status():
    """Onbellek durumunu getir."""
    return {
        "cached_provinces": list(_districts_cache.keys()),
        "cache_size": len(_districts_cache),
        "index_loaded": _districts_index is not None
    }
