from collections import OrderedDict
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import logging
import os
from pathlib import Path
from threading import Lock as ThreadLock
from typing import Annotated, Any
from uuid import uuid4

from anyio import Lock
from anyio.to_process import run_sync as run_in_process
from auth.dependencies import get_current_user
from celery_app import celery_app
from core.config import get_emlakjet_config, get_hepsiemlak_config
from core.task_status import get_task_status_store, is_final_task_status
from database import crud, results
from database.connection import get_db
from database.models import FailedPage, Listing, Location, PriceHistory, ScrapeSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from tasks.scraping_tasks import scrape_emlakjet_task, scrape_hepsiemlak_task

from api.schemas import (
    SUPPORTED_SCRAPING_METHODS,
    ActiveTasksResponse,
    ScrapeRequest,
    ScrapeStartResponse,
    TaskStatusResponse,
)

# İlçe verileri dizini
DISTRICTS_DIR = Path(__file__).parent.parent / "data" / "districts"
_DISTRICTS_CACHE_MAX_ENTRIES = 16


@dataclass(frozen=True, slots=True)
class _DistrictGeoJSONEntry:
    raw_bytes: bytes
    gzip_bytes: bytes
    etag: str


# İlçe GeoJSON verileri için sınırlı LRU byte önbelleği (dict/json.dumps + event-loop gzip yok)
_districts_cache: OrderedDict[str, _DistrictGeoJSONEntry] = OrderedDict()
_districts_index: dict[str, Any] | None = None
_districts_lock = ThreadLock()

router = APIRouter(dependencies=[Depends(get_current_user)])
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
    "gunluk_kiralik": "Günlük Kiralık",
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
        raise HTTPException(
            status_code=503, detail="Task status store unavailable"
        ) from exc


def _enqueue_scrape_task(
    task_callable, *, kwargs: dict[str, Any], message: str, platform: str
) -> TaskStatusResponse:
    store = _require_task_status_store()
    task_id = uuid4().hex
    task_callable.apply_async(kwargs=kwargs, queue="scraping", task_id=task_id)
    payload = store.create_queued_task(task_id, message=message, platform=platform)
    return TaskStatusResponse(**payload)


@router.get("/config/categories")
async def get_categories(response: Response):
    """Tüm platform kategorilerini getir"""
    response.headers["Cache-Control"] = "public, max-age=86400"
    emlakjet = get_emlakjet_config()
    hepsiemlak = get_hepsiemlak_config()

    def format_categories(categories_dict):
        return [
            {"id": k, "name": CATEGORY_NAMES.get(k, k.replace("_", " ").title())}
            for k in categories_dict
        ]

    return {
        "emlakjet": {
            "satilik": format_categories(emlakjet.categories["satilik"]),
            "kiralik": format_categories(emlakjet.categories["kiralik"]),
        },
        "hepsiemlak": {
            "satilik": format_categories(hepsiemlak.categories["satilik"]),
            "kiralik": format_categories(hepsiemlak.categories["kiralik"]),
        },
    }


@router.get("/config/subtypes")
def get_subtypes(listing_type: str, category: str, platform: str = "hepsiemlak"):
    """Belirli kategori için alt tipleri JSON'dan oku"""
    if platform == "emlakjet":
        from scrapers.emlakjet.subtype_fetcher import (
            SUBCATEGORIES_JSON_PATH,
            fetch_subtypes,
        )
    else:
        from scrapers.hepsiemlak.subtype_fetcher import (
            SUBCATEGORIES_JSON_PATH,
            fetch_subtypes,
        )

    subtypes = fetch_subtypes(listing_type, category)

    if not SUBCATEGORIES_JSON_PATH.exists():
        return {
            "subtypes": [],
            "error": f"{platform} subcategories JSON dosyası bulunamadı.",
        }

    return {"subtypes": subtypes, "cached": True}


@router.post("/scrape/emlakjet", response_model=ScrapeStartResponse)
def scrape_emlakjet(request: ScrapeRequest):
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
            "max_listings": 0,
            "max_pages": request.max_pages,
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
def scrape_hepsiemlak(request: ScrapeRequest):
    """Celery ile HepsiEmlak tarama görevi başlat."""
    _validate_scraping_method_or_raise(request.scraping_method)
    if not request.cities:
        raise HTTPException(status_code=400, detail="En az bir şehir seçmelisiniz")

    if request.districts:
        for city in request.districts:
            if city not in request.cities:
                raise HTTPException(
                    status_code=400,
                    detail=f"İlçe seçilen şehir ({city}) şehir listesinde yok",
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
def get_active_tasks():
    """Tüm aktif görevleri al."""
    store = _require_task_status_store()
    tasks = [TaskStatusResponse(**item) for item in store.get_active_tasks()]
    return ActiveTasksResponse(active_tasks=tasks, count=len(tasks))


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """Belirli bir scraping görevinin kanonik durumunu al."""
    store = _require_task_status_store()
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(**task)


@router.post("/tasks/{task_id}/cancel", response_model=TaskStatusResponse)
def cancel_task(task_id: str):
    store = _require_task_status_store()
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if is_final_task_status(task.get("status")):
        raise HTTPException(status_code=409, detail="Görev zaten sonlandı")

    payload = store.mark_cancelled(task_id)
    try:
        celery_app.control.revoke(task_id, terminate=True)
    except Exception as exc:
        logger.warning("Celery revoke failed for %s: %s", task_id, exc)
    return TaskStatusResponse(**payload)


@router.get("/analytics/prices")
def get_price_analytics(
    filters: Annotated[results.ResultsFilters, Query()],
    db: Session = Depends(get_db),
):
    """Return price averages and histogram bins for the active filters."""
    return results.cached_read(
        db,
        "api_prices",
        filters.model_dump_json(),
        lambda: results.get_price_summary(db, filters),
    )


@router.get("/analytics/city/{city_name}")
def get_city_analytics(
    city_name: str,
    platform: str | None = None,
    category: str | None = None,
    listing_type: str | None = None,
    subtype: str | None = None,
    db: Session = Depends(get_db),
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
        category_map = {
            "Konut": "konut",
            "Arsa": "arsa",
            "İşyeri": "isyeri",
            "Devremülk": "devremulk",
        }
        db_category = category_map.get(category, category.lower())

    if listing_type and listing_type != "all":
        listing_map = {"Satılık": "satilik", "Kiralık": "kiralik"}
        db_listing_type = listing_map.get(listing_type, listing_type.lower())

    db_subtype = None
    if subtype and subtype != "all":
        db_subtype = subtype.strip().lower().replace(" ", "_").replace("-", "_")

    return results.cached_read(
        db,
        "api_city_analytics",
        (city_name, db_platform, db_category, db_listing_type, db_subtype),
        lambda: crud.get_city_analytics(
            db,
            city_name=city_name,
            platform=db_platform,
            kategori=db_category,
            ilan_tipi=db_listing_type,
            alt_kategori=db_subtype,
        ),
    )


@router.get("/analytics/stats")
def get_listing_statistics(
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    city: str | None = None,
    district: str | None = None,
    db: Session = Depends(get_db),
):
    """Veritabanından detaylı istatistikler - describe + fiyat aralıkları"""
    conditions = [Listing.fiyat.isnot(None), Listing.fiyat > 0]

    if platform and platform != "all":
        platform_map = {"HepsiEmlak": "hepsiemlak", "Emlakjet": "emlakjet"}
        db_platform = platform_map.get(platform, platform.lower())
        conditions.append(Listing.platform == db_platform)

    if kategori and kategori != "all":
        category_map = {
            "Konut": "konut",
            "Arsa": "arsa",
            "İşyeri": "isyeri",
            "Devremülk": "devremulk",
        }
        db_kategori = category_map.get(kategori, kategori.lower())
        conditions.append(Listing.kategori == db_kategori)

    if ilan_tipi and ilan_tipi != "all":
        type_map = {"Satılık": "satilik", "Kiralık": "kiralik"}
        db_type = type_map.get(ilan_tipi, ilan_tipi.lower())
        conditions.append(Listing.ilan_tipi == db_type)

    has_city = bool(city and city != "Belirtilmemiş")
    has_district = bool(district and district != "Belirtilmemiş")
    stmt = select(Listing.fiyat.label("price"))
    if has_city or has_district:
        stmt = stmt.join_from(Listing, Location)
        if has_city:
            conditions.append(Location.il == city)
        if has_district:
            conditions.append(Location.ilce == district)
    else:
        stmt = stmt.select_from(Listing)

    price_subquery = stmt.where(*conditions).subquery()

    def _compute_stats():
        describe_stats, price_ranges = crud.compute_price_stats_sql(db, price_subquery)
        if describe_stats is None:
            return {"error": "Fiyat verisi bulunamadı", "stats": None}
        return {
            "stats": describe_stats,
            "price_ranges": price_ranges,
            "total_listings": describe_stats["count"],
        }

    return results.cached_read(
        db,
        "api_analytics_stats",
        (platform, kategori, ilan_tipi, city, district),
        _compute_stats,
    )


@router.delete("/clear-results")
def clear_results(db: Session = Depends(get_db)):
    """Veritabanindaki tum ilanlari ve outputs klasorundeki dosyalari sil"""
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
        results.invalidate_results_cache()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Veritabani temizleme hatasi: {e!s}"
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
def get_results(
    filters: Annotated[results.ResultsPageQuery, Query()],
    db: Session = Depends(get_db),
):
    """Return one page of grouped listing results."""
    return results.cached_read(
        db,
        "api_results",
        filters.model_dump_json(),
        lambda: results.get_results_page(db, filters),
    )


@router.get("/results/filters")
def get_result_filters(include_overview: bool = False, db: Session = Depends(get_db)):
    def _load_filters():
        metadata = results.get_results_filters(db, include_overview=include_overview)
        metadata["last_scrape"] = crud.get_last_scrape(db)
        return metadata

    return results.cached_read(db, "api_filters", include_overview, _load_filters)


@router.get("/results/overview")
def get_results_overview(
    filters: Annotated[results.ResultsFilters, Query()],
    db: Session = Depends(get_db),
):
    return results.cached_read(
        db,
        "api_overview",
        filters.model_dump_json(),
        lambda: results.get_results_overview(db, filters),
    )


@router.get("/listings/preview")
def get_listings_preview(
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    city: str | None = None,
    district: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
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
        limit=limit,
    )

    data = [listing.to_dict() for listing in listings]
    return {"data": data, "total": total, "showing": len(data)}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Veritabanından genel istatistikleri döndür"""
    return results.cached_read(db, "api_stats", (), lambda: crud.get_stats_summary(db))


# ==================== NEW DB-BASED ENDPOINTS ====================


@router.get("/listings")
def get_listings(
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    alt_kategori: str | None = None,
    city: str | None = None,
    district: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
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
        limit=limit,
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "items": [listing.to_dict() for listing in listings],
    }


@router.get("/listings/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Tek bir ilan detayını getir"""
    listing = crud.get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")
    return listing.to_dict()


@router.get("/sessions")
def get_scrape_sessions(
    platform: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Tarama oturumlarını listele"""
    sessions, total = crud.get_scrape_sessions(
        db, platform=platform, status=status, page=page, limit=limit
    )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [s.to_dict() for s in sessions],
    }


@router.get("/cities")
def get_cities(db: Session = Depends(get_db)):
    """Veritabanindaki tum sehirleri listele."""
    cities = crud.get_all_cities(db)
    return {"cities": cities}


@router.get("/cities/{city}/districts")
def get_districts(city: str, db: Session = Depends(get_db)):
    """Bir sehrin ilcelerini listele."""
    districts = crud.get_districts_by_city(db, city)
    return {"city": city, "districts": districts}


_excel_export_lock = Lock()


def _get_excel_rows(
    db: Session,
    platform: str | None,
    kategori: str | None,
    ilan_tipi: str | None,
    city: str | None,
    district: str | None,
) -> list[dict[str, Any]]:
    from utils.timezone import format_istanbul

    # Ilanlari al (disa aktarim icin maks 10000)
    listings, _total = crud.get_listings(
        db,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        city=city,
        district=district,
        page=1,
        limit=10000,
    )

    if not listings:
        raise HTTPException(status_code=404, detail="Dışa aktarılacak veri bulunamadı")

    # DataFrame'e donustur
    data = []
    for listing in listings:
        row = {
            "Başlık": listing.baslik,
            "Fiyat": listing.fiyat_text or listing.fiyat,
            "Platform": listing.platform,
            "Kategori": listing.kategori,
            "İlan Tipi": listing.ilan_tipi,
            "Alt Kategori": listing.alt_kategori,
            "İl": listing.location.il if listing.location else "",
            "İlçe": listing.location.ilce if listing.location else "",
            "Mahalle": listing.location.mahalle if listing.location else "",
            "İlan URL": listing.ilan_url,
            "Emlak Ofisi": listing.emlak_ofisi,
            "Tarih": format_istanbul(listing.created_at) if listing.created_at else "",
        }
        # Add details
        if listing.details:
            for k, v in listing.details.items():
                row[k] = v
        data.append(row)

    return data


def _build_excel_workbook(rows: list[dict[str, Any]]) -> bytes:
    import pandas as pd

    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


@router.post("/export/excel")
async def export_to_excel(
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    city: str | None = None,
    district: str | None = None,
    db: Session = Depends(get_db),
):
    """Filtrelere göre verileri Excel'e aktar ve indir"""
    from utils.timezone import now_istanbul

    # Bound concurrent exports before loading rows and keep XLSX CPU work off the API process.
    async with _excel_export_lock:
        rows = await run_in_threadpool(
            _get_excel_rows, db, platform, kategori, ilan_tipi, city, district
        )
        content = await run_in_process(_build_excel_workbook, rows)

    timestamp = now_istanbul().strftime("%Y%m%d_%H%M%S")
    filename = f"export_{timestamp}.xlsx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/listings/group")
def delete_listing_group(
    platform: str = Query(default=None),
    kategori: str = Query(default=None),
    ilan_tipi: str = Query(default=None),
    city: str = Query(default=None),
    district: str = Query(default=None),
    alt_kategori: str = Query(default=None),
    db: Session = Depends(get_db),
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
        category_map = {
            "Konut": "konut",
            "Arsa": "arsa",
            "İşyeri": "isyeri",
            "Devremülk": "devremulk",
            "Turistik İşletme": "turistik_isletme",
        }
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
        db_alt = alt_kategori.lower().replace(" ", "_")
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
    results.invalidate_results_cache()

    return {
        "status": "success",
        "message": f"{count} ilan silindi",
        "deleted_count": count,
    }


@router.delete("/listings/{listing_id}")
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    """Bir ilanı sil"""
    listing = crud.get_listing_by_id(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı")

    db.delete(listing)
    db.commit()
    results.invalidate_results_cache()

    return {"status": "success", "message": f"İlan {listing_id} silindi"}


# ==================== ILCE GEOJSON ENDPOINTLER ====================


def _load_districts_index() -> dict[str, Any]:
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


def _load_district_geojson(province_name: str) -> _DistrictGeoJSONEntry:
    """Il GeoJSON ham/sikistirilmis byte verisini yukle ve LRU onbellege al."""
    cached = _districts_cache.get(province_name)
    if cached is not None:
        _districts_cache.move_to_end(province_name)
        return cached

    # Index'ten dosya adını al
    index = _load_districts_index()
    province_info = index.get(province_name)

    if not province_info:
        raise HTTPException(
            status_code=404, detail=f"Province '{province_name}' not found in index"
        )

    filename = province_info.get("file")
    if not filename:
        raise HTTPException(
            status_code=404, detail=f"No file specified for province '{province_name}'"
        )

    filepath = DISTRICTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(
            status_code=404, detail=f"GeoJSON file not found: {filename}"
        )

    raw_bytes = filepath.read_bytes()
    gzip_bytes = gzip.compress(raw_bytes, compresslevel=6)
    etag = f'"{hashlib.sha256(raw_bytes).hexdigest()[:16]}"'
    entry = _DistrictGeoJSONEntry(
        raw_bytes=raw_bytes, gzip_bytes=gzip_bytes, etag=etag
    )

    _districts_cache[province_name] = entry
    while len(_districts_cache) > _DISTRICTS_CACHE_MAX_ENTRIES:
        _districts_cache.popitem(last=False)

    return entry


@router.get("/districts/index")
def get_districts_index(response: Response):
    """Tüm illerin ilçe sayılarıyla index'ini getir"""
    response.headers["Cache-Control"] = "public, max-age=86400"
    with _districts_lock:
        return _load_districts_index()


@router.get("/districts/{province_name}")
def get_district_geojson(province_name: str, request: Request):
    """Belirli bir ilin ilçe GeoJSON verisini getir"""
    with _districts_lock:
        entry = _load_district_geojson(province_name)

    headers = {
        "Cache-Control": "public, max-age=86400",
        "ETag": entry.etag,
        "Vary": "Accept-Encoding",
    }
    if request.headers.get("if-none-match") == entry.etag:
        return Response(status_code=304, headers=headers)

    if "gzip" in request.headers.get("accept-encoding", "").lower():
        headers["Content-Encoding"] = "gzip"
        return Response(
            content=entry.gzip_bytes,
            media_type="application/json",
            headers=headers,
        )

    return Response(
        content=entry.raw_bytes,
        media_type="application/json",
        headers=headers,
    )


@router.get("/districts/info/{province_name}")
def get_district_info(province_name: str, response: Response):
    """İl için ilçe listesini ve meta verilerini getir"""
    response.headers["Cache-Control"] = "public, max-age=86400"
    with _districts_lock:
        index = _load_districts_index()
    province_info = index.get(province_name)

    if not province_info:
        raise HTTPException(
            status_code=404, detail=f"Province '{province_name}' not found"
        )

    return {
        "province": province_name,
        "file": province_info.get("file"),
        "count": province_info.get("count"),
        "districts": province_info.get("districts", []),
    }


@router.post("/districts/cache/clear")
def clear_districts_cache():
    """Bellek ici ilce onbelleğini temizle."""
    global _districts_index
    with _districts_lock:
        cache_size = len(_districts_cache)
        _districts_cache.clear()
        _districts_index = None
    return {
        "status": "success",
        "message": f"Cache cleared. {cache_size} provinces removed from cache.",
    }


@router.get("/districts/cache/status")
def get_cache_status():
    """Onbellek durumunu getir."""
    with _districts_lock:
        return {
            "cached_provinces": list(_districts_cache.keys()),
            "cache_size": len(_districts_cache),
            "index_loaded": _districts_index is not None,
        }
