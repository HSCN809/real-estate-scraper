# -*- coding: utf-8 -*-
"""
CRUD operations for database models
"""

import re
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError

from .models import Location, Listing, ScrapeSession, FailedPage, PriceHistory


# ============== Hash Utilities ==============

def compute_content_hash(data: Dict[str, Any]) -> str:
    """
    Compute MD5 hash of listing content (excluding price).
    Used for detecting non-price changes in listings.
    """
    # Fields to include in hash (everything except price)
    hash_fields = [
        'baslik',
        'oda_sayisi', 'metrekare', 'bina_yasi', 'kat',
        'arsa_metrekare', 'imar_durumu', 'arsa_tipi',
        'isyeri_tipi', 'tesis_tipi', 'yatak_sayisi',
        'emlak_ofisi', 'tip'
    ]

    # Build content string
    content_parts = []
    for field in hash_fields:
        value = data.get(field)
        if value is not None:
            content_parts.append(f"{field}:{value}")

    # Include details if present
    details = data.get('details')
    if details and isinstance(details, dict):
        content_parts.append(f"details:{json.dumps(details, sort_keys=True)}")

    content_str = "|".join(sorted(content_parts))
    return hashlib.md5(content_str.encode('utf-8')).hexdigest()


# ============== Location CRUD ==============

def get_or_create_location(
    db: Session,
    il: str,
    ilce: Optional[str] = None,
    mahalle: Optional[str] = None
) -> Location:
    """
    Get existing location or create new one.
    Uses the unique constraint to prevent duplicates.
    """
    # Normalize inputs
    il = il.strip() if il else None
    ilce = ilce.strip() if ilce else None
    mahalle = mahalle.strip() if mahalle else None

    if not il:
        il = "Belirtilmemiş"

    # Try to find existing
    location = db.query(Location).filter(
        Location.il == il,
        Location.ilce == ilce if ilce else Location.ilce.is_(None),
        Location.mahalle == mahalle if mahalle else Location.mahalle.is_(None)
    ).first()

    if location:
        return location

    # Create new
    location = Location(il=il, ilce=ilce, mahalle=mahalle)
    db.add(location)

    try:
        db.flush()  # Get the ID without committing
    except IntegrityError:
        db.rollback()
        # Race condition - fetch the one that was just created
        location = db.query(Location).filter(
            Location.il == il,
            Location.ilce == ilce if ilce else Location.ilce.is_(None),
            Location.mahalle == mahalle if mahalle else Location.mahalle.is_(None)
        ).first()

    return location


def get_all_cities(db: Session) -> List[str]:
    """Get all unique city names"""
    result = db.query(Location.il).distinct().order_by(Location.il).all()
    return [r[0] for r in result if r[0]]


def get_districts_by_city(db: Session, city: str) -> List[str]:
    """Get all districts for a city"""
    result = db.query(Location.ilce).filter(
        Location.il == city,
        Location.ilce.isnot(None)
    ).distinct().order_by(Location.ilce).all()
    return [r[0] for r in result if r[0]]


# ============== Listing CRUD ==============

def parse_price(price_str: str) -> Optional[float]:
    """
    Parse Turkish price string to float.
    Handles formats like "1.500.000 TL", "1,500,000", "1500000"
    """
    if not price_str or str(price_str).strip().lower() in ['belirtilmemiş', 'belirtilmemis', '']:
        return None

    try:
        val_str = str(price_str).strip()
        val_str = re.sub(r'\s+', '', val_str)
        val_str = val_str.replace('TL', '').replace('₺', '')

        # Handle Turkish number format
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif '.' in val_str and val_str.count('.') > 1:
            val_str = val_str.replace('.', '')
        elif '.' in val_str and len(val_str.split('.')[-1]) == 3:
            val_str = val_str.replace('.', '')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')

        price = float(val_str)
        return price if price > 0 else None
    except (ValueError, TypeError):
        return None


def create_listing(
    db: Session,
    data: Dict[str, Any],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: Optional[str] = None,
    scrape_session_id: Optional[int] = None
) -> Tuple[Optional[Listing], bool]:
    """
    Create a new listing. Returns (listing, is_new).
    If listing with same ilan_url exists, returns (None, False).
    """
    # Get ilan_url for deduplication
    ilan_url = data.get('ilan_linki') or data.get('ilan_url')

    # Check for duplicate
    if ilan_url:
        existing = db.query(Listing).filter(Listing.ilan_url == ilan_url).first()
        if existing:
            return (None, False)  # Duplicate

    # Get or create location
    il = data.get('il')
    ilce = data.get('ilce')
    mahalle = data.get('mahalle')

    if not il or il == 'Belirtilmemiş':
        # Fallback: lokasyon alanından parse et
        lokasyon = data.get('lokasyon', '')
        if lokasyon:
            # EmlakJet formatı: "İstanbul / Kadıköy / Caferağa"
            # HepsiEmlak formatı: "İstanbul, Kadıköy"
            if '/' in lokasyon:
                parts = [p.strip() for p in lokasyon.split('/')]
            else:
                parts = [p.strip() for p in lokasyon.split(',')]
            il = parts[0] if len(parts) > 0 else None
            if not ilce and len(parts) > 1:
                ilce = parts[1]
            if not mahalle and len(parts) > 2:
                mahalle = parts[2]
    if not il:
        il = 'Belirtilmemiş'

    location = get_or_create_location(db, il, ilce, mahalle)

    # Parse price
    fiyat_text = data.get('fiyat', '')
    fiyat = parse_price(fiyat_text)

    # Extract category-specific details
    details = {}
    detail_fields = [
        'oda_sayisi', 'metrekare', 'bina_yasi', 'kat',
        'arsa_metrekare', 'metrekare_fiyat', 'imar_durumu', 'arsa_tipi',
        'isyeri_tipi', 'tesis_tipi', 'yatak_sayisi', 'otel_tipi',
        'tip', 'one_cikan', 'yeni'
    ]
    for field in detail_fields:
        if field in data and data[field]:
            details[field] = data[field]

    # Parse ilan_tarihi
    ilan_tarihi = None
    if data.get('ilan_tarihi'):
        try:
            # Try common formats
            date_str = str(data['ilan_tarihi']).strip()
            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    ilan_tarihi = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    # Compute content hash
    content_hash = compute_content_hash(data)

    # Create listing
    listing = Listing(
        baslik=data.get('baslik', 'Başlık Yok'),
        fiyat=fiyat,
        fiyat_text=str(fiyat_text) if fiyat_text else None,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        location_id=location.id,
        ilan_url=ilan_url,
        ilan_tarihi=ilan_tarihi,
        emlak_ofisi=data.get('emlak_ofisi'),
        resim_url=data.get('resim_url'),
        details=details if details else None,
        scrape_session_id=scrape_session_id,
        content_hash=content_hash
    )

    db.add(listing)

    try:
        db.flush()
        return (listing, True)
    except IntegrityError:
        db.rollback()
        return (None, False)  # Duplicate URL


def upsert_listing(
    db: Session,
    data: Dict[str, Any],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: Optional[str] = None,
    scrape_session_id: Optional[int] = None
) -> Tuple[Optional[Listing], str]:
    """
    Upsert a listing - insert if new, update if exists.
    Uses hash-based change detection for performance.
    Tracks price changes in price_history table.

    Returns: (listing, status) where status is 'created', 'updated', 'unchanged', or 'error'
    """
    # Get ilan_url for deduplication
    ilan_url = data.get('ilan_linki') or data.get('ilan_url')

    if not ilan_url:
        # No URL means we can't deduplicate - just create
        listing, is_new = create_listing(db, data, platform, kategori, ilan_tipi, alt_kategori, scrape_session_id)
        if listing:
            listing.content_hash = compute_content_hash(data)
        return (listing, 'created' if is_new else 'error')

    # Check for existing listing
    existing = db.query(Listing).filter(Listing.ilan_url == ilan_url).first()

    if not existing:
        # New listing - create it
        listing, is_new = create_listing(db, data, platform, kategori, ilan_tipi, alt_kategori, scrape_session_id)
        if listing:
            listing.content_hash = compute_content_hash(data)
        return (listing, 'created' if is_new else 'error')

    # Existing listing found - compute new hash
    new_content_hash = compute_content_hash(data)
    new_fiyat_text = data.get('fiyat', '')
    new_fiyat = parse_price(new_fiyat_text)

    # Check for price change
    price_changed = False
    old_price = existing.fiyat
    if new_fiyat is not None and existing.fiyat != new_fiyat:
        price_changed = True

    # Check for content change using hash
    content_changed = (existing.content_hash != new_content_hash)

    # If nothing changed, skip update
    if not price_changed and not content_changed:
        existing.scrape_session_id = scrape_session_id
        return (existing, 'unchanged')

    # Record price change if applicable
    if price_changed and old_price is not None and new_fiyat is not None:
        price_change = new_fiyat - old_price
        price_change_percent = (price_change / old_price) * 100 if old_price > 0 else 0

        price_record = PriceHistory(
            listing_id=existing.id,
            old_price=old_price,
            new_price=new_fiyat,
            price_change=price_change,
            price_change_percent=round(price_change_percent, 2)
        )
        db.add(price_record)

    # Update the listing
    new_baslik = data.get('baslik')
    if new_baslik:
        existing.baslik = new_baslik
    if new_fiyat is not None:
        existing.fiyat = new_fiyat
        existing.fiyat_text = str(new_fiyat_text) if new_fiyat_text else None

    new_emlak_ofisi = data.get('emlak_ofisi')
    if new_emlak_ofisi:
        existing.emlak_ofisi = new_emlak_ofisi

    new_resim_url = data.get('resim_url')
    if new_resim_url:
        existing.resim_url = new_resim_url

    # Update details if present
    new_details = {}
    detail_fields = [
        'oda_sayisi', 'metrekare', 'bina_yasi', 'kat',
        'arsa_metrekare', 'metrekare_fiyat', 'imar_durumu', 'arsa_tipi',
        'isyeri_tipi', 'tesis_tipi', 'yatak_sayisi', 'otel_tipi',
        'tip', 'one_cikan', 'yeni'
    ]
    for field in detail_fields:
        if field in data and data[field]:
            new_details[field] = data[field]

    if new_details:
        existing.details = {**(existing.details or {}), **new_details}

    # Update hash and metadata
    existing.content_hash = new_content_hash
    existing.updated_at = datetime.utcnow()
    existing.scrape_session_id = scrape_session_id

    db.flush()
    return (existing, 'updated')


def get_listings(
    db: Session,
    platform: Optional[str] = None,
    kategori: Optional[str] = None,
    ilan_tipi: Optional[str] = None,
    alt_kategori: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 50
) -> Tuple[List[Listing], int]:
    """
    Get listings with filters and pagination.
    Returns (listings, total_count).
    """
    query = db.query(Listing)

    # Apply filters
    if platform and platform != 'all':
        query = query.filter(Listing.platform == platform)
    if kategori and kategori != 'all':
        query = query.filter(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != 'all':
        query = query.filter(Listing.ilan_tipi == ilan_tipi)
    if alt_kategori and alt_kategori != 'all':
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

    # Get total count
    total = query.count()

    # Pagination
    offset = (page - 1) * limit
    listings = query.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()

    return (listings, total)


def get_listing_by_id(db: Session, listing_id: int) -> Optional[Listing]:
    """Get a single listing by ID"""
    return db.query(Listing).filter(Listing.id == listing_id).first()


def get_listings_count(db: Session) -> int:
    """Get total number of listings"""
    return db.query(Listing).count()


# ============== ScrapeSession CRUD ==============

def create_scrape_session(
    db: Session,
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: Optional[str] = None,
    target_cities: Optional[List[str]] = None,
    target_districts: Optional[Dict[str, List[str]]] = None
) -> ScrapeSession:
    """Create a new scrape session"""
    session = ScrapeSession(
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        target_cities=target_cities,
        target_districts=target_districts,
        status="running"
    )
    db.add(session)
    db.flush()
    return session


def update_scrape_session(
    db: Session,
    session_id: int,
    **kwargs
) -> Optional[ScrapeSession]:
    """Update scrape session fields"""
    session = db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
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
    status: str = "completed",
    error_message: Optional[str] = None
) -> Optional[ScrapeSession]:
    """Mark a scrape session as completed"""
    session = db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
    if not session:
        return None

    session.status = status
    session.completed_at = datetime.utcnow()
    if session.started_at:
        session.duration_seconds = int((session.completed_at - session.started_at).total_seconds())
    if error_message:
        session.error_message = error_message

    db.flush()
    return session


def get_scrape_sessions(
    db: Session,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50
) -> Tuple[List[ScrapeSession], int]:
    """Get scrape sessions with filters"""
    query = db.query(ScrapeSession)

    if platform and platform != 'all':
        query = query.filter(ScrapeSession.platform == platform)
    if status and status != 'all':
        query = query.filter(ScrapeSession.status == status)

    total = query.count()
    offset = (page - 1) * limit
    sessions = query.order_by(ScrapeSession.started_at.desc()).offset(offset).limit(limit).all()

    return (sessions, total)


# ============== Analytics ==============

def get_price_analytics(
    db: Session,
    platform: Optional[str] = None,
    kategori: Optional[str] = None,
    ilan_tipi: Optional[str] = None,
    city: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get price analytics with optional filters.
    Returns prices and summary statistics.
    """
    query = db.query(
        Listing.fiyat,
        Location.il.label('city'),
        Listing.platform,
        Listing.kategori,
        Listing.ilan_tipi
    ).join(Location).filter(
        Listing.fiyat.isnot(None),
        Listing.fiyat > 0
    )

    if platform and platform != 'all':
        query = query.filter(Listing.platform == platform)
    if kategori and kategori != 'all':
        query = query.filter(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != 'all':
        query = query.filter(Listing.ilan_tipi == ilan_tipi)
    if city:
        query = query.filter(Location.il == city)

    results = query.limit(50000).all()  # Limit for performance

    prices = [
        {
            "city": r.city,
            "platform": r.platform,
            "category": r.kategori,
            "listing_type": r.ilan_tipi,
            "price": r.fiyat
        }
        for r in results
    ]

    price_values = [r.fiyat for r in results]

    summary = {
        "total_count": len(price_values),
        "avg_price": round(sum(price_values) / len(price_values), 2) if price_values else 0,
        "min_price": min(price_values) if price_values else 0,
        "max_price": max(price_values) if price_values else 0
    }

    return {"prices": prices, "summary": summary}


def get_city_analytics(
    db: Session,
    city_name: str,
    platform: Optional[str] = None,
    kategori: Optional[str] = None,
    ilan_tipi: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed analytics for a specific city.
    """
    import statistics

    # Normalize city name for comparison
    def normalize_turkish(text):
        replacements = {
            'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's', 'ğ': 'g', 'Ğ': 'g',
            'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
        }
        for tr_char, ascii_char in replacements.items():
            text = text.replace(tr_char, ascii_char)
        return text.lower()

    city_normalized = normalize_turkish(city_name)

    # Find matching location
    locations = db.query(Location).all()
    matching_location_ids = []
    for loc in locations:
        if normalize_turkish(loc.il) == city_normalized:
            matching_location_ids.append(loc.id)

    if not matching_location_ids:
        return {
            "city": city_name,
            "total_listings": 0,
            "districts": [],
            "error": "Şehir bulunamadı",
            "stats": None,
            "price_ranges": []
        }

    # Query listings
    query = db.query(Listing).filter(
        Listing.location_id.in_(matching_location_ids)
    )

    if platform and platform != 'all':
        query = query.filter(Listing.platform == platform)
    if kategori and kategori != 'all':
        query = query.filter(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != 'all':
        query = query.filter(Listing.ilan_tipi == ilan_tipi)

    listings = query.all()

    # Get districts
    districts = db.query(Location.ilce).filter(
        Location.id.in_(matching_location_ids),
        Location.ilce.isnot(None)
    ).distinct().all()
    district_names = sorted([d[0] for d in districts if d[0]])

    # Calculate price statistics
    prices = [l.fiyat for l in listings if l.fiyat and l.fiyat > 0]

    if not prices:
        return {
            "city": city_name,
            "total_listings": len(listings),
            "districts": district_names,
            "error": "Fiyat verisi bulunamadı",
            "stats": None,
            "price_ranges": []
        }

    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if c < len(data) else data[f]

    stats = {
        "count": n,
        "mean": round(statistics.mean(prices), 2),
        "std": round(statistics.stdev(prices), 2) if n > 1 else 0,
        "min": round(min(prices), 2),
        "q25": round(percentile(sorted_prices, 25), 2),
        "median": round(statistics.median(prices), 2),
        "q75": round(percentile(sorted_prices, 75), 2),
        "max": round(max(prices), 2)
    }

    # Price range distribution
    num_bins = 5
    bin_edges = [percentile(sorted_prices, i * 100 / num_bins) for i in range(num_bins + 1)]

    unique_edges = []
    for e in bin_edges:
        if not unique_edges or e > unique_edges[-1]:
            unique_edges.append(e)

    if len(unique_edges) < 3:
        min_p, max_p = min(prices), max(prices)
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]

    def format_price(p):
        if p >= 1000000:
            return f"{p/1000000:.1f}M"
        elif p >= 1000:
            return f"{p/1000:.0f}K"
        else:
            return f"{p:.0f}"

    price_ranges = []
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]
        label = f"{format_price(low)} - {format_price(high)}"

        if i == len(unique_edges) - 2:
            count = sum(1 for p in prices if low <= p <= high)
        else:
            count = sum(1 for p in prices if low <= p < high)

        price_ranges.append({
            "range": label,
            "count": count,
            "percentage": round(count / n * 100, 1)
        })

    return {
        "city": city_name,
        "total_listings": len(listings),
        "districts": district_names,
        "stats": stats,
        "price_ranges": price_ranges
    }


def get_stats_summary(db: Session) -> Dict[str, Any]:
    """Get overall statistics for dashboard"""
    from datetime import timedelta

    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_listings = db.query(Listing).count()
    total_sessions = db.query(ScrapeSession).count()

    this_week = db.query(ScrapeSession).filter(ScrapeSession.started_at >= week_ago).count()
    this_month = db.query(ScrapeSession).filter(ScrapeSession.started_at >= month_ago).count()

    last_session = db.query(ScrapeSession).order_by(ScrapeSession.started_at.desc()).first()
    last_scrape = last_session.started_at.strftime('%d.%m.%Y %H:%M') if last_session else "-"

    return {
        "total_scrapes": total_sessions,
        "total_listings": total_listings,
        "this_week": this_week,
        "this_month": this_month,
        "last_scrape": last_scrape
    }


def get_results_for_frontend(db: Session) -> List[Dict[str, Any]]:
    """
    Get results aggregated by city for the frontend.
    Groups listings by city and returns summary for each.
    This replaces the old Excel-based /results endpoint.
    """
    # Category/listing type display mappings
    platform_map = {"hepsiemlak": "HepsiEmlak", "emlakjet": "Emlakjet"}
    category_map = {"konut": "Konut", "arsa": "Arsa", "isyeri": "İşyeri", "devremulk": "Devremülk",
                    "turistik_isletme": "Turistik İşletme", "turistik_tesis": "Turistik Tesis"}
    listing_type_map = {"satilik": "Satılık", "kiralik": "Kiralık"}

    # İl + İlçe bazında gruplama (mahalle aggregate ediliyor)
    results = []

    combinations = db.query(
        Location.il,
        Location.ilce,
        Listing.platform,
        Listing.kategori,
        Listing.ilan_tipi,
        Listing.alt_kategori,
        func.count(Listing.id).label('count'),
        func.avg(Listing.fiyat).label('avg_price'),
        func.max(Listing.created_at).label('last_date')
    ).join(Location).group_by(
        Location.il,
        Location.ilce,
        Listing.platform,
        Listing.kategori,
        Listing.ilan_tipi,
        Listing.alt_kategori
    ).order_by(func.max(Listing.created_at).desc()).all()

    for idx, row in enumerate(combinations):
        city = row.il or "Bilinmiyor"
        district = row.ilce

        # Format display names
        platform_display = platform_map.get(row.platform, row.platform)
        category_display = category_map.get(row.kategori, row.kategori)
        listing_type_display = listing_type_map.get(row.ilan_tipi, row.ilan_tipi)
        subtype_display = row.alt_kategori.replace('_', ' ').title() if row.alt_kategori else None

        # Format date
        date_str = row.last_date.strftime('%d.%m.%Y %H:%M') if row.last_date else "-"

        # Create unique ID
        result_id = f"db_{row.platform}_{row.kategori}_{row.ilan_tipi}_{city}_{district or 'all'}_{idx}"

        results.append({
            "id": result_id,
            "platform": platform_display,
            "category": category_display,
            "subtype": subtype_display,
            "listing_type": listing_type_display,
            "city": city,
            "district": district,
            "date": date_str,
            "count": row.count,
            "avg_price": round(row.avg_price, 2) if row.avg_price else None,
            "file_size": 0,
            "file_size_mb": 0,
            "status": "completed",
            "files": []
        })

    return results


# ============== FailedPage CRUD ==============

def create_failed_page(
    db: Session,
    scrape_session_id: int,
    url: str,
    page_number: Optional[int] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    error_message: Optional[str] = None
) -> FailedPage:
    """Record a failed page"""
    failed = FailedPage(
        scrape_session_id=scrape_session_id,
        url=url,
        page_number=page_number,
        city=city,
        district=district,
        error_message=error_message
    )
    db.add(failed)
    db.flush()
    return failed
