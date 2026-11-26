"""Veritabani CRUD islemleri."""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, cast

from core.task_status import (
    SCRAPE_SESSION_STATUS_COMPLETED,
    SCRAPE_SESSION_STATUS_RUNNING,
    SCRAPE_SESSION_STATUS_VALUES,
    normalize_scrape_session_status,
)
from sqlalchemy import and_, case, func, select, true, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from utils.timezone import format_istanbul, latest_datetime, now_utc_naive

from .models import FailedPage, Listing, Location, PriceHistory, ScrapeSession

# ============== Hash Yardımcıları ==============


def compute_content_hash(data: dict[str, Any]) -> str:
    """İlan içerik hash'i hesapla (fiyat hariç)"""
    # Hash'e dahil edilecek alanlar (fiyat hariç)
    hash_fields = [
        "baslik",
        "oda_sayisi",
        "metrekare",
        "bina_yasi",
        "kat",
        "arsa_metrekare",
        "imar_durumu",
        "arsa_tipi",
        "isyeri_tipi",
        "tesis_tipi",
        "yatak_sayisi",
        "emlak_ofisi",
        "tip",
    ]

    # Icerik string'ini olustur
    content_parts = []
    for field in hash_fields:
        value = data.get(field)
        if value is not None:
            content_parts.append(f"{field}:{value}")

    # Detaylar varsa dahil et
    details = data.get("details")
    if details and isinstance(details, dict):
        content_parts.append(f"details:{json.dumps(details, sort_keys=True)}")

    content_str = "|".join(sorted(content_parts))
    return hashlib.md5(content_str.encode("utf-8"), usedforsecurity=False).hexdigest()


# ============== Lokasyon CRUD ==============


def get_or_create_location(
    db: Session, il: str, ilce: str | None = None, mahalle: str | None = None
) -> Location:
    """Mevcut lokasyonu getir veya yeni olustur."""
    # Girdileri normalize et
    il = il.strip() if il else None
    ilce = ilce.strip() if ilce else None
    mahalle = mahalle.strip() if mahalle else None

    if not il:
        il = "Belirtilmemiş"

    # Mevcut olani bulmaya calis
    location = (
        db.query(Location)
        .filter(
            Location.il == il,
            Location.ilce == ilce if ilce else Location.ilce.is_(None),
            Location.mahalle == mahalle if mahalle else Location.mahalle.is_(None),
        )
        .first()
    )

    if location:
        return location

    # Yeni olustur
    location = Location(il=il, ilce=ilce, mahalle=mahalle)
    db.add(location)

    try:
        db.flush()  # Commit etmeden ID al
    except IntegrityError:
        db.rollback()
        # Yaris durumu - yeni olusturulani getir
        location = (
            db.query(Location)
            .filter(
                Location.il == il,
                Location.ilce == ilce if ilce else Location.ilce.is_(None),
                Location.mahalle == mahalle if mahalle else Location.mahalle.is_(None),
            )
            .first()
        )

    return location


def get_all_cities(db: Session) -> list[str]:
    """Tum benzersiz sehir adlarini getir."""
    result = db.query(Location.il).distinct().order_by(Location.il).all()
    return [r[0] for r in result if r[0]]


def get_districts_by_city(db: Session, city: str) -> list[str]:
    """Bir sehrin tum ilcelerini getir."""
    result = (
        db.query(Location.ilce)
        .filter(Location.il == city, Location.ilce.isnot(None))
        .distinct()
        .order_by(Location.ilce)
        .all()
    )
    return [r[0] for r in result if r[0]]


# ============== İlan CRUD ==============


def parse_price(price_str: str) -> float | None:
    """Türkçe fiyat metnini float'a çevir"""
    if not price_str or str(price_str).strip().lower() in [
        "belirtilmemiş",
        "belirtilmemis",
        "",
    ]:
        return None

    try:
        val_str = str(price_str).strip()
        val_str = re.sub(r"\s+", "", val_str)
        val_str = val_str.replace("TL", "").replace("₺", "")

        # Turkce sayi formatini isle
        if "," in val_str and "." in val_str:
            val_str = val_str.replace(".", "").replace(",", ".")
        elif "." in val_str and val_str.count(".") > 1 or "." in val_str and len(val_str.split(".")[-1]) == 3:
            val_str = val_str.replace(".", "")
        elif "," in val_str:
            val_str = val_str.replace(",", ".")

        price = float(val_str)
        return price if price > 0 else None
    except (ValueError, TypeError):
        return None


_LocationKey = tuple[str, str | None, str | None]
_LISTING_BATCH_SIZE = 500
_LOCATION_BATCH_SIZE = 250


def _listing_url(data: dict[str, Any]) -> str | None:
    return data.get("ilan_linki") or data.get("ilan_url")


def _listing_location_key(data: dict[str, Any]) -> _LocationKey:
    il = data.get("il")
    ilce = data.get("ilce")
    mahalle = data.get("mahalle")

    if not il or il == "Belirtilmemiş":
        # Fallback: lokasyon alanından parse et
        lokasyon = data.get("lokasyon", "")
        if lokasyon:
            # EmlakJet formati: "İstanbul / Kadıköy / Caferağa"
            # HepsiEmlak formatı: "İstanbul, Kadıköy"
            if "/" in lokasyon:
                parts = [p.strip() for p in lokasyon.split("/")]
            else:
                parts = [p.strip() for p in lokasyon.split(",")]
            il = parts[0] if len(parts) > 0 else None
            if not ilce and len(parts) > 1:
                ilce = parts[1]
            if not mahalle and len(parts) > 2:
                mahalle = parts[2]
    return (
        (il or "").strip() or "Belirtilmemiş",
        (ilce or "").strip() or None,
        (mahalle or "").strip() or None,
    )


def _new_listing(
    data: dict[str, Any],
    location: Location,
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None,
    scrape_session_id: int | None,
) -> Listing:
    # Fiyati ayristir
    fiyat_text = data.get("fiyat", "")
    fiyat = parse_price(fiyat_text)

    # Kategoriye özel detayları çıkar
    details = {}
    detail_fields = [
        "oda_sayisi",
        "metrekare",
        "bina_yasi",
        "kat",
        "arsa_metrekare",
        "metrekare_fiyat",
        "imar_durumu",
        "arsa_tipi",
        "isyeri_tipi",
        "tesis_tipi",
        "yatak_sayisi",
        "otel_tipi",
        "tip",
        "one_cikan",
        "yeni",
    ]
    for field in detail_fields:
        if data.get(field):
            details[field] = data[field]

    # Ilan tarihini ayristir
    ilan_tarihi = None
    if data.get("ilan_tarihi"):
        try:
            # Yaygın formatları dene
            date_str = str(data["ilan_tarihi"]).strip()
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    ilan_tarihi = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        except Exception:  # nosec
            pass

    # İçerik hash'i hesapla
    content_hash = compute_content_hash(data)

    # Ilan olustur
    return Listing(
        baslik=data.get("baslik", "Başlık Yok"),
        fiyat=fiyat,
        fiyat_text=str(fiyat_text) if fiyat_text else None,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        location=location,
        ilan_url=_listing_url(data),
        ilan_tarihi=ilan_tarihi,
        emlak_ofisi=data.get("emlak_ofisi"),
        resim_url=data.get("resim_url"),
        details=details if details else None,
        scrape_session_id=scrape_session_id,
        content_hash=content_hash,
    )


def create_listing(
    db: Session,
    data: dict[str, Any],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
) -> tuple[Listing | None, bool]:
    """Yeni ilan olustur, (ilan, yeni_mi) dondur."""
    ilan_url = _listing_url(data)
    if ilan_url and db.query(Listing).filter(Listing.ilan_url == ilan_url).first():
        return None, False

    location = get_or_create_location(db, *_listing_location_key(data))
    listing = _new_listing(
        data, location, platform, kategori, ilan_tipi, alt_kategori, scrape_session_id
    )
    db.add(listing)
    try:
        db.flush()
        return listing, True
    except IntegrityError:
        db.rollback()
        return None, False


def _update_listing(
    db: Session,
    existing: Listing,
    data: dict[str, Any],
    scrape_session_id: int | None,
) -> str:
    # Mevcut ilan bulundu - yeni hash hesapla
    new_content_hash = compute_content_hash(data)
    new_fiyat_text = data.get("fiyat", "")
    new_fiyat = parse_price(new_fiyat_text)

    # Fiyat degisikligi kontrolu
    price_changed = False
    old_price = existing.fiyat
    if new_fiyat is not None and existing.fiyat != new_fiyat:
        price_changed = True

    # Hash kullanarak icerik degisikligi kontrolu
    content_changed = existing.content_hash != new_content_hash

    # Degisiklik yoksa ORM guncellemesini ve updated_at yazimini atla
    if not price_changed and not content_changed:
        return "unchanged"

    # Uygunsa fiyat degisikligini kaydet
    if price_changed and old_price is not None and new_fiyat is not None:
        price_change = new_fiyat - old_price
        price_change_percent = (price_change / old_price) * 100 if old_price > 0 else 0

        price_record = PriceHistory(
            listing=existing,
            old_price=old_price,
            new_price=new_fiyat,
            price_change=price_change,
            price_change_percent=round(price_change_percent, 2),
        )
        db.add(price_record)

    # İlanı güncelle
    new_baslik = data.get("baslik")
    if new_baslik:
        existing.baslik = new_baslik
    if new_fiyat is not None:
        existing.fiyat = new_fiyat
        existing.fiyat_text = str(new_fiyat_text) if new_fiyat_text else None

    new_emlak_ofisi = data.get("emlak_ofisi")
    if new_emlak_ofisi:
        existing.emlak_ofisi = new_emlak_ofisi

    new_resim_url = data.get("resim_url")
    if new_resim_url:
        existing.resim_url = new_resim_url

    # Detaylar varsa güncelle
    new_details = {}
    detail_fields = [
        "oda_sayisi",
        "metrekare",
        "bina_yasi",
        "kat",
        "arsa_metrekare",
        "metrekare_fiyat",
        "imar_durumu",
        "arsa_tipi",
        "isyeri_tipi",
        "tesis_tipi",
        "yatak_sayisi",
        "otel_tipi",
        "tip",
        "one_cikan",
        "yeni",
    ]
    for field in detail_fields:
        if data.get(field):
            new_details[field] = data[field]

    if new_details:
        existing.details = {**(existing.details or {}), **new_details}

    # Hash ve meta verileri güncelle
    existing.content_hash = new_content_hash
    existing.updated_at = datetime.utcnow()
    existing.scrape_session_id = scrape_session_id

    return "updated"


def upsert_listing(
    db: Session,
    data: dict[str, Any],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
) -> tuple[Listing | None, str]:
    """İlan upsert - yeniyse ekle, varsa güncelle."""
    url = _listing_url(data)
    if url:
        existing = db.query(Listing).filter(Listing.ilan_url == url).first()
        if existing is not None:
            status = _update_listing(db, existing, data, scrape_session_id)
            if status == "updated":
                db.flush()
            elif (
                scrape_session_id is not None
                and existing.scrape_session_id != scrape_session_id
            ):
                db.execute(
                    update(Listing)
                    .where(Listing.id == existing.id)
                    .values(scrape_session_id=scrape_session_id)
                )
                db.expire(existing, ["scrape_session_id"])
            return existing, status

    listing, is_new = create_listing(
        db, data, platform, kategori, ilan_tipi, alt_kategori, scrape_session_id
    )
    return listing, "created" if is_new else "error"


def _load_listing_locations(
    db: Session, location_keys: list[_LocationKey]
) -> dict[_LocationKey, Location]:
    locations: dict[_LocationKey, Location] = {}
    # Treat legacy empty strings and NULL as the same missing district or neighborhood.
    location_tuple = tuple_(
        Location.il,
        func.coalesce(Location.ilce, ""),
        func.coalesce(Location.mahalle, ""),
    )
    for start in range(0, len(location_keys), _LOCATION_BATCH_SIZE):
        keys = [
            (city, district or "", neighborhood or "")
            for city, district, neighborhood in location_keys[
                start : start + _LOCATION_BATCH_SIZE
            ]
        ]
        query = select(Location).where(location_tuple.in_(keys)).order_by(Location.id)
        for location in db.scalars(query):
            locations.setdefault(
                (location.il, location.ilce or None, location.mahalle or None), location
            )
    return locations


def upsert_listings(
    db: Session,
    listings: list[dict],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
) -> tuple[int, int, int]:
    """Upsert in input order and leave the transaction to the caller."""
    if not listings:
        return 0, 0, 0

    db.flush()
    counts: Counter[str] = Counter()
    for start in range(0, len(listings), _LISTING_BATCH_SIZE):
        batch = listings[start : start + _LISTING_BATCH_SIZE]
        urls = [_listing_url(data) for data in batch]
        unique_urls = {url for url in urls if url}
        existing: dict[str, Listing] = {}
        if unique_urls:
            # Serialize updates to existing prices so history uses the current value.
            query = (
                select(Listing)
                .where(Listing.ilan_url.in_(unique_urls))
                .order_by(Listing.ilan_url)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            existing = {listing.ilan_url: listing for listing in db.scalars(query)}

        # Only the first occurrence of a new URL decides its location.
        seen_urls = set(existing)
        keys_by_index = {}
        for index, (data, url) in enumerate(zip(batch, urls)):
            if not url or url not in seen_urls:
                keys_by_index[index] = _listing_location_key(data)
                if url:
                    seen_urls.add(url)
        locations = _load_listing_locations(
            db, list(dict.fromkeys(keys_by_index.values()))
        )

        unchanged_session_updates: list[Listing] = []
        for index, (data, url) in enumerate(zip(batch, urls)):
            listing = existing.get(url) if url else None
            if listing is not None:
                status = _update_listing(db, listing, data, scrape_session_id)
                counts[status] += 1
                if (
                    status == "unchanged"
                    and scrape_session_id is not None
                    and listing.scrape_session_id != scrape_session_id
                    and listing.id is not None
                ):
                    unchanged_session_updates.append(listing)
                continue

            key = keys_by_index[index]
            location = locations.get(key)
            if location is None:
                city, district, neighborhood = key
                location = Location(il=city, ilce=district, mahalle=neighborhood)
                locations[key] = location
            listing = _new_listing(
                data,
                location,
                platform,
                kategori,
                ilan_tipi,
                alt_kategori,
                scrape_session_id,
            )
            db.add(listing)
            if url:
                existing[url] = listing
            counts["created"] += 1

        db.flush()
        if unchanged_session_updates:
            # Tek toplu UPDATE ile scrape_session_id guncelle (updated_at bozulmaz)
            target_ids = list({item.id for item in unchanged_session_updates})
            db.execute(
                update(Listing)
                .where(Listing.id.in_(target_ids))
                .values(scrape_session_id=scrape_session_id)
            )
            for item in unchanged_session_updates:
                db.expire(item, ["scrape_session_id"])

    if counts["created"] or counts["updated"]:
        from .results import invalidate_results_cache

        invalidate_results_cache()

    return counts["created"], counts["updated"], counts["unchanged"]


def get_listings(
    db: Session,
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
) -> tuple[list[Listing], int]:
    """Filtreleme ve sayfalama ile ilanları getir"""
    query = db.query(Listing)

    # Filtreleri uygula
    if platform and platform != "all":
        query = query.filter(Listing.platform == platform)
    if kategori and kategori != "all":
        query = query.filter(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != "all":
        query = query.filter(Listing.ilan_tipi == ilan_tipi)
    if alt_kategori and alt_kategori != "all":
        query = query.filter(Listing.alt_kategori == alt_kategori)
    if city:
        query = query.join(Location).filter(Location.il == city)
    if district:
        if not city:
            query = query.join(Location)
        query = query.filter(Location.ilce == district)
    if min_price is not None:
        query = query.filter(Listing.fiyat >= min_price)
    if max_price is not None:
        query = query.filter(Listing.fiyat <= max_price)

    # Toplam sayıyı al
    total = query.count()

    # Sayfalama
    offset = (page - 1) * limit
    listings = (
        query.options(selectinload(Listing.location))
        .order_by(Listing.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return (listings, total)


def get_listing_by_id(db: Session, listing_id: int) -> Listing | None:
    """ID ile tek bir ilan getir"""
    return db.query(Listing).filter(Listing.id == listing_id).first()


def get_listings_count(db: Session) -> int:
    """Toplam ilan sayısını getir"""
    return db.query(Listing).count()


# ============== Tarama Oturumu CRUD ==============


def create_scrape_session(
    db: Session,
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    target_cities: list[str] | None = None,
    target_districts: dict[str, list[str]] | None = None,
) -> ScrapeSession:
    """Yeni tarama oturumu olustur."""
    session = ScrapeSession(
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        target_cities=target_cities,
        target_districts=target_districts,
        status=SCRAPE_SESSION_STATUS_RUNNING,
    )
    db.add(session)
    db.flush()
    return session


def update_scrape_session(
    db: Session, session_id: int, **kwargs
) -> ScrapeSession | None:
    """Tarama oturumu alanlarını güncelle"""
    session = cast(
        Any, db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
    )
    if not session:
        return None

    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)

    db.flush()
    return session


def complete_scrape_session(
    db: Session,
    session_id: int,
    status: str = SCRAPE_SESSION_STATUS_COMPLETED,
    error_message: str | None = None,
) -> ScrapeSession | None:
    """Tarama oturumunu tamamlandi olarak isaretle."""
    session = cast(
        Any, db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
    )
    if not session:
        return None

    normalized_status = normalize_scrape_session_status(status)
    if normalized_status not in SCRAPE_SESSION_STATUS_VALUES:
        raise ValueError(f"Unsupported scrape session status: {status}")

    session.status = normalized_status
    session.completed_at = datetime.utcnow()
    if session.started_at:
        session.duration_seconds = int(
            (session.completed_at - session.started_at).total_seconds()
        )
    if error_message:
        session.error_message = error_message

    db.flush()
    return session


def normalize_legacy_scrape_session_statuses(db: Session) -> int:
    """Eski status değerlerini kanonik sete dönüştür."""
    sessions = db.query(ScrapeSession).all()
    updated = 0
    for session in sessions:
        normalized = normalize_scrape_session_status(session.status)
        if normalized != session.status:
            session.status = normalized
            updated += 1
    if updated:
        db.flush()
    return updated


def get_scrape_sessions(
    db: Session,
    platform: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[ScrapeSession], int]:
    """Filtreli tarama oturumlarını getir"""
    query = db.query(ScrapeSession)

    if platform and platform != "all":
        query = query.filter(ScrapeSession.platform == platform)
    if status and status != "all":
        query = query.filter(ScrapeSession.status == status)

    total = query.count()
    offset = (page - 1) * limit
    sessions = (
        query.order_by(ScrapeSession.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return (sessions, total)


# ============== Analitik ==============


_TURKISH_ASCII_MAP = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc")


def _normalize_turkish(text: str) -> str:
    return text.translate(_TURKISH_ASCII_MAP).lower()


def compute_price_stats_and_ranges(
    sorted_prices: list[float], num_bins: int = 5
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Compute summary stats and quantile-based price ranges from sorted prices."""
    import bisect
    import math

    n = len(sorted_prices)

    def percentile(p: float) -> float:
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < n else f
        return sorted_prices[f] + (sorted_prices[c] - sorted_prices[f]) * (k - f)

    mid = n // 2
    median = (
        sorted_prices[mid]
        if n % 2 == 1
        else (sorted_prices[mid - 1] + sorted_prices[mid]) / 2.0
    )

    mean = math.fsum(sorted_prices) / n
    if n > 1:
        variance = math.fsum((p - mean) ** 2 for p in sorted_prices) / (n - 1)
        std = math.sqrt(variance)
    else:
        std = 0.0

    stats = {
        "count": n,
        "mean": round(mean, 2),
        "std": round(std, 2) if n > 1 else 0,
        "min": round(sorted_prices[0], 2),
        "q25": round(percentile(25), 2),
        "median": round(median, 2),
        "q75": round(percentile(75), 2),
        "max": round(sorted_prices[-1], 2),
    }

    bin_edges = [percentile(i * 100 / num_bins) for i in range(num_bins + 1)]
    unique_edges: list[float] = []
    for edge in bin_edges:
        if not unique_edges or edge > unique_edges[-1]:
            unique_edges.append(edge)

    if len(unique_edges) < 3:
        min_p, max_p = sorted_prices[0], sorted_prices[-1]
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]

    def format_price(p: float) -> str:
        if p >= 1_000_000:
            return f"{p / 1_000_000:.1f}M"
        if p >= 1_000:
            return f"{p / 1_000:.0f}K"
        return f"{p:.0f}"

    price_ranges: list[dict[str, Any]] = []
    last_idx = len(unique_edges) - 2
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]
        left = bisect.bisect_left(sorted_prices, low)
        right = (
            bisect.bisect_right(sorted_prices, high)
            if i == last_idx
            else bisect.bisect_left(sorted_prices, high)
        )
        count = max(0, right - left)
        price_ranges.append(
            {
                "range": f"{format_price(low)} - {format_price(high)}",
                "count": count,
                "percentage": round(count / n * 100, 1),
            }
        )

    return stats, price_ranges


def compute_price_stats_sql(
    db: Session, price_subquery: Any, num_bins: int = 5
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Compute summary stats and quantile-based price ranges directly in SQL."""
    import math

    price_col = price_subquery.c.price
    n, mean_val, min_val, max_val = db.execute(
        select(
            func.count(price_col),
            func.avg(price_col),
            func.min(price_col),
            func.max(price_col),
        ).select_from(price_subquery)
    ).one()

    if not n:
        return None, []

    n = int(n)
    mean = float(mean_val)
    min_p = float(min_val)
    max_p = float(max_val)

    def _interp_ranks(p: float) -> tuple[int, int, float]:
        k = (n - 1) * p / 100.0
        f = int(k)
        c = f + 1 if f + 1 < n else f
        return f + 1, c + 1, k - f

    needed_ranks: set[int] = set()
    for p in (25.0, 75.0):
        r1, r2, _ = _interp_ranks(p)
        needed_ranks.update((r1, r2))

    mid = n // 2
    if n % 2 == 1:
        needed_ranks.add(mid + 1)
    else:
        needed_ranks.update((mid, mid + 1))

    bin_specs = [_interp_ranks(i * 100.0 / num_bins) for i in range(num_bins + 1)]
    for r1, r2, _ in bin_specs:
        needed_ranks.update((r1, r2))

    ranked = select(
        price_col.label("price"),
        func.row_number().over(order_by=price_col).label("rn"),
    ).select_from(price_subquery).subquery()

    rank_map = {
        int(rn): float(val)
        for rn, val in db.execute(
            select(ranked.c.rn, ranked.c.price).where(ranked.c.rn.in_(needed_ranks))
        )
    }

    def percentile(p: float) -> float:
        r1, r2, frac = _interp_ranks(p)
        v1 = rank_map[r1]
        v2 = rank_map[r2]
        return v1 + (v2 - v1) * frac

    median = (
        rank_map[mid + 1]
        if n % 2 == 1
        else (rank_map[mid] + rank_map[mid + 1]) / 2.0
    )

    unique_edges: list[float] = []
    for r1, r2, frac in bin_specs:
        edge = rank_map[r1] + (rank_map[r2] - rank_map[r1]) * frac
        if not unique_edges or edge > unique_edges[-1]:
            unique_edges.append(edge)

    if len(unique_edges) < 3:
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]

    ss_expr = func.coalesce(func.sum((price_col - mean) * (price_col - mean)), 0.0)
    last_idx = len(unique_edges) - 2
    bin_exprs = []
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]
        upper = price_col <= high if i == last_idx else price_col < high
        bin_exprs.append(
            func.coalesce(
                func.sum(case((and_(price_col >= low, upper), 1), else_=0)), 0
            )
        )

    agg_row = db.execute(select(ss_expr, *bin_exprs).select_from(price_subquery)).one()
    ss = float(agg_row[0] or 0.0)
    std = math.sqrt(ss / (n - 1)) if n > 1 else 0.0

    stats = {
        "count": n,
        "mean": round(mean, 2),
        "std": round(std, 2) if n > 1 else 0,
        "min": round(min_p, 2),
        "q25": round(percentile(25.0), 2),
        "median": round(median, 2),
        "q75": round(percentile(75.0), 2),
        "max": round(max_p, 2),
    }

    def format_price(p: float) -> str:
        if p >= 1_000_000:
            return f"{p / 1_000_000:.1f}M"
        if p >= 1_000:
            return f"{p / 1_000:.0f}K"
        return f"{p:.0f}"

    price_ranges: list[dict[str, Any]] = []
    for i, count_val in enumerate(agg_row[1:]):
        low = unique_edges[i]
        high = unique_edges[i + 1]
        cnt = int(count_val or 0)
        price_ranges.append(
            {
                "range": f"{format_price(low)} - {format_price(high)}",
                "count": cnt,
                "percentage": round(cnt / n * 100, 1),
            }
        )

    return stats, price_ranges


def get_city_analytics(
    db: Session,
    city_name: str,
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    alt_kategori: str | None = None,
) -> dict[str, Any]:
    """Belirli bir sehrin detayli analizlerini getir."""
    city_normalized = _normalize_turkish(city_name)

    # Sadece benzersiz il adlarini cek (tum locations tablosu yerine ~81 satir)
    matching_cities = [
        loc_il
        for loc_il in db.scalars(select(Location.il).distinct())
        if loc_il and _normalize_turkish(loc_il) == city_normalized
    ]

    if not matching_cities:
        return {
            "city": city_name,
            "total_listings": 0,
            "districts": [],
            "error": "Şehir bulunamadı",
            "stats": None,
            "price_ranges": [],
        }

    district_names = list(
        db.scalars(
            select(Location.ilce)
            .where(Location.il.in_(matching_cities), Location.ilce.isnot(None))
            .distinct()
            .order_by(Location.ilce)
        )
    )

    conditions = [Location.il.in_(matching_cities)]
    if platform and platform != "all":
        conditions.append(Listing.platform == platform)
    if kategori and kategori != "all":
        conditions.append(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != "all":
        conditions.append(Listing.ilan_tipi == ilan_tipi)
    if alt_kategori and alt_kategori != "all":
        conditions.append(Listing.alt_kategori == alt_kategori)

    total_listings = (
        db.scalar(
            select(func.count(Listing.id))
            .join_from(Listing, Location)
            .where(*conditions)
        )
        or 0
    )

    price_subquery = (
        select(Listing.fiyat.label("price"))
        .join_from(Listing, Location)
        .where(*conditions, Listing.fiyat.isnot(None), Listing.fiyat > 0)
        .subquery()
    )
    stats, price_ranges = compute_price_stats_sql(db, price_subquery)

    if stats is None:
        return {
            "city": city_name,
            "total_listings": total_listings,
            "districts": district_names,
            "error": "Fiyat verisi bulunamadı",
            "stats": None,
            "price_ranges": [],
        }

    return {
        "city": city_name,
        "total_listings": total_listings,
        "districts": district_names,
        "stats": stats,
        "price_ranges": price_ranges,
    }


def get_last_scrape(db: Session) -> str:
    latest_listing = select(func.max(Listing.created_at).label("created_at")).subquery()
    latest_session = (
        select(ScrapeSession.started_at, ScrapeSession.completed_at)
        .order_by(ScrapeSession.started_at.desc())
        .limit(1)
        .subquery()
    )
    dates = db.execute(
        select(
            latest_listing.c.created_at,
            latest_session.c.started_at,
            latest_session.c.completed_at,
        ).select_from(latest_listing.outerjoin(latest_session, true()))
    ).one()
    return format_istanbul(latest_datetime(*dates))


def get_stats_summary(db: Session) -> dict[str, Any]:
    """Kontrol paneli için genel istatistikleri getir"""
    from datetime import timedelta

    now = now_utc_naive()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_listings = db.scalar(select(func.count(Listing.id))) or 0
    total_sessions, this_week, this_month = db.execute(
        select(
            func.count(ScrapeSession.id),
            func.coalesce(
                func.sum(case((ScrapeSession.started_at >= week_ago, 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((ScrapeSession.started_at >= month_ago, 1), else_=0)), 0
            ),
        )
    ).one()

    return {
        "total_scrapes": int(total_sessions or 0),
        "total_listings": int(total_listings),
        "this_week": int(this_week or 0),
        "this_month": int(this_month or 0),
        "last_scrape": get_last_scrape(db),
    }


# ============== Basarisiz Sayfa CRUD ==============


def create_failed_page(
    db: Session,
    scrape_session_id: int,
    url: str,
    page_number: int | None = None,
    city: str | None = None,
    district: str | None = None,
    error_message: str | None = None,
) -> FailedPage:
    """Basarisiz sayfayi kaydet."""
    failed = FailedPage(
        scrape_session_id=scrape_session_id,
        url=url,
        page_number=page_number,
        city=city,
        district=district,
        error_message=error_message,
    )
    db.add(failed)
    db.flush()
    return failed
