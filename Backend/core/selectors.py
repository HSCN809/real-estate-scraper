# -*- coding: utf-8 -*-
"""
CSS/XPath Selectors for each platform and category
Centralized selector management for easy maintenance
"""

from typing import Dict, Any, Optional


# ============================================================================
# EMLAKJET SELECTORS
# ============================================================================

EMLAKJET_SELECTORS = {
    "common": {
        # Listing selectors
        "listing_container": "a.styles_wrapper__587DT",
        "title": "h3.styles_title__aKEGQ",
        "location": "span.styles_location__OwJiQ",
        "price": "span.styles_price__F3pMQ",
        "image": "img.styles_imageClass___SLvt",
        "badge_wrapper": "div.styles_badgewrapper__pS0rt",
        "quick_info": "div.styles_quickinfoWrapper__Vsnk5",
        
        # Pagination
        "pagination_list": "ul.styles_list__zqOeW li",
        "active_page": "span.styles_selected__hilA_",
        
        # Location navigation
        "location_links": "section.styles_section__xzOd3 a.styles_link__7WOOd",
        
        # Category menu
        "category_button": "div[role='button']",
        "sub_menu": "ul.styles_wrapper__xd9_i",
        "sub_category": "ul.styles_ulSubMenu__E0zyf li.styles_subMenu2__BskGl",
        "ad_count": "span.styles_adCount__M4_Qr",
    },
    
    "konut": {
        "fields": ["tip", "oda_sayisi", "kat", "metrekare"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "tip", "oda_sayisi", "kat", "metrekare", "tarih"
        ],
    },
    
    "arsa": {
        "fields": ["arsa_tipi", "metrekare", "imar_durumu"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "arsa_tipi", "metrekare", "imar_durumu", "tarih"
        ],
    },
    
    "isyeri": {
        "fields": ["isyeri_tipi", "metrekare", "kat"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "isyeri_tipi", "metrekare", "kat", "tarih"
        ],
    },
    
    "turistik_tesis": {
        "fields": ["tesis_tipi", "oda_sayisi", "yatak_sayisi"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "tesis_tipi", "oda_sayisi", "yatak_sayisi", "tarih"
        ],
    },
    
    "kat_karsiligi_arsa": {
        "fields": ["arsa_tipi", "metrekare", "imar_durumu"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "arsa_tipi", "metrekare", "imar_durumu", "tarih"
        ],
    },
    
    "devren_isyeri": {
        "fields": ["isyeri_tipi", "metrekare"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "isyeri_tipi", "metrekare", "tarih"
        ],
    },
    
    "gunluk_kiralik": {
        "fields": ["tip", "oda_sayisi", "metrekare"],
        "csv_fields": [
            "baslik", "lokasyon", "fiyat", "ilan_url", "resim_url",
            "one_cikan", "yeni", "tip", "oda_sayisi", "metrekare", "tarih"
        ],
    },
}


# ============================================================================
# HEPSIEMLAK SELECTORS
# ============================================================================

HEPSIEMLAK_SELECTORS = {
    "common": {
        # Listing selectors
        "listing_container": "li.listing-item:not(.listing-item--promo)",
        "listing_results": "ul.list-items-container, .search-results",
        "title": "h3",
        "price": "span.list-view-price",
        "location": "span.list-view-location",
        "date": "span.list-view-date",
        "link": "a.card-link",
        "firm": "p.listing-card--owner-info__firm-name",
        
        # City dropdown
        "city_dropdown": "div.he-select-base__container, div[data-name='city']",
        "city_list": "div.he-select-base__list, div.he-select__list",
        "city_item": "li.he-select__list-item, li.he-select-base__list-item",
        "city_link": "a.js-city-filter__list-link, span.he-select-base__text",
        "city_radio": "div.he-radio, input[type='radio']",
        
        # Search button
        "search_buttons": [
            "a.btn.btn-red.btn-large",
            "button.btn.btn-red.btn-large",
            "a[data-tracking-label='SearchSubmit']",
            "button[type='submit']",
            ".btn-red"
        ],
        
        # Pagination
        "pagination": [
            "ul.he-pagination__links li.he-pagination__item a.he-pagination__link",
            ".pagination a",
            ".he-pagination a",
            "a[href*='page=']"
        ],
    },
    
    "konut": {
        "fields": ["oda_sayisi", "metrekare", "bina_yasi", "kat", "emlak_ofisi"],
        "room_count": "span.houseRoomCount",
        "size": "span.list-view-size",
        "building_age": "span.buildingAge",
        "floor": "span.floortype",
        "csv_fields": [
            "fiyat", "baslik", "il", "ilce", "mahalle", "ilan_linki",
            "ilan_tarihi", "oda_sayisi", "metrekare", "bina_yasi", "kat", "emlak_ofisi"
        ],
    },
    
    "arsa": {
        "fields": ["arsa_metrekare", "metrekare_fiyat", "emlak_ofisi"],
        "size": "span.celly.squareMeter.list-view-size",
        "csv_fields": [
            "fiyat", "baslik", "il", "ilce", "mahalle", "ilan_linki",
            "ilan_tarihi", "arsa_metrekare", "metrekare_fiyat", "emlak_ofisi"
        ],
    },
    
    "isyeri": {
        "fields": ["metrekare", "emlak_ofisi"],
        "size": "span.celly.squareMeter.list-view-size",
        "csv_fields": [
            "fiyat", "baslik", "il", "ilce", "mahalle", "ilan_linki",
            "ilan_tarihi", "metrekare", "emlak_ofisi"
        ],
    },
    
    "devremulk": {
        "fields": ["oda_sayisi", "metrekare", "bina_yasi", "kat"],
        "room_count": "span.houseRoomCount",
        "size": "span.celly.squareMeter.list-view-size",
        "building_age": "span.buildingAge",
        "floor": "span.floortype",
        "csv_fields": [
            "fiyat", "baslik", "il", "ilce", "mahalle", "ilan_linki",
            "ilan_tarihi", "oda_sayisi", "metrekare", "bina_yasi", "kat"
        ],
    },
    
    "turistik_isletme": {
        "fields": ["oda_sayisi", "otel_tipi"],
        "room_count": "span.workRoomCount",
        "star_count": "span.startCount",
        "csv_fields": [
            "fiyat", "baslik", "il", "ilce", "mahalle", "ilan_linki",
            "ilan_tarihi", "oda_sayisi", "otel_tipi"
        ],
    },
}


# ============================================================================
# MAIN SELECTORS DICTIONARY
# ============================================================================

SELECTORS: Dict[str, Dict[str, Any]] = {
    "emlakjet": EMLAKJET_SELECTORS,
    "hepsiemlak": HEPSIEMLAK_SELECTORS,
}


def get_selectors(platform: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get selectors for a specific platform and optionally a category.
    
    Args:
        platform: Platform name ('emlakjet' or 'hepsiemlak')
        category: Optional category name ('konut', 'arsa', etc.)
    
    Returns:
        Dictionary of selectors
    """
    if platform not in SELECTORS:
        raise ValueError(f"Unknown platform: {platform}")
    
    platform_selectors = SELECTORS[platform]
    
    if category is None:
        return platform_selectors
    
    if category not in platform_selectors:
        raise ValueError(f"Unknown category '{category}' for platform '{platform}'")
    
    # Merge common selectors with category-specific ones
    result = {**platform_selectors["common"]}
    result.update(platform_selectors[category])
    
    return result


def get_common_selectors(platform: str) -> Dict[str, Any]:
    """Get common selectors for a platform"""
    if platform not in SELECTORS:
        raise ValueError(f"Unknown platform: {platform}")
    
    return SELECTORS[platform]["common"]


def get_category_selectors(platform: str, category: str) -> Dict[str, Any]:
    """Get category-specific selectors only"""
    if platform not in SELECTORS:
        raise ValueError(f"Unknown platform: {platform}")
    
    if category not in SELECTORS[platform]:
        raise ValueError(f"Unknown category '{category}' for platform '{platform}'")
    
    return SELECTORS[platform][category]
