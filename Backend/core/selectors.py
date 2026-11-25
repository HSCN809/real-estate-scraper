"""Platform ve kategori bazlı CSS/XPath seçiciler"""

from typing import Any

# ============================================================================
# EmlakJet seçicileri
# ============================================================================

EMLAKJET_SELECTORS = {
    "common": {
        # İlan seçicileri (Next.js güncel listing-row-card-* + eski fallback)
        "listing_container": "article[data-listing-id]",
        "title": "h3[data-listing-title] a",
        "link": "h3[data-listing-title] a, a[data-listing-image]",
        "location": "p.listing-row-card-meta, p.text-xs",
        "price": ".listing-row-card-price > span, span.shrink-0.whitespace-nowrap",
        "image": "img[src*='/listing/']",
        "badge_wrapper": ".property-card-badge-pill, span[class*='px-2 py-0.5']",
        "quick_info": "p.listing-row-card-meta, p.text-xs",
        # Sayfalama (yeni yapı: ?sayfa=N)
        "pagination_list": "a[href*='sayfa=']",
        "active_page": "span[aria-current='page']",
        "listing_count": "p.text-body span.font-semibold",
        # Lokasyon navigasyonu - kodda URL prefix'ine göre üretilir
        "location_links": "a[href]",
        # Kategori menüsü (eski yapı - korundu)
        "category_button": "div[role='button']",
        "sub_menu": "ul.styles_wrapper__xd9_i",
        "sub_category": "ul.styles_ulSubMenu__E0zyf li.styles_subMenu2__BskGl",
        "ad_count": "span.styles_adCount__M4_Qr",
    },
    "konut": {
        "fields": ["tip", "oda_sayisi", "kat", "metrekare"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "tip",
            "oda_sayisi",
            "kat",
            "metrekare",
            "tarih",
        ],
    },
    "arsa": {
        "fields": ["arsa_tipi", "metrekare", "imar_durumu"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "arsa_tipi",
            "metrekare",
            "imar_durumu",
            "tarih",
        ],
    },
    "isyeri": {
        "fields": ["isyeri_tipi", "metrekare", "kat"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "isyeri_tipi",
            "metrekare",
            "kat",
            "tarih",
        ],
    },
    "turistik_tesis": {
        "fields": ["tesis_tipi", "oda_sayisi", "yatak_sayisi"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "tesis_tipi",
            "oda_sayisi",
            "yatak_sayisi",
            "tarih",
        ],
    },
    "kat_karsiligi_arsa": {
        "fields": ["arsa_tipi", "metrekare", "imar_durumu"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "arsa_tipi",
            "metrekare",
            "imar_durumu",
            "tarih",
        ],
    },
    "devren_isyeri": {
        "fields": ["isyeri_tipi", "metrekare"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "isyeri_tipi",
            "metrekare",
            "tarih",
        ],
    },
    "gunluk_kiralik": {
        "fields": ["tip", "oda_sayisi", "metrekare"],
        "csv_fields": [
            "baslik",
            "lokasyon",
            "fiyat",
            "ilan_url",
            "resim_url",
            "one_cikan",
            "yeni",
            "tip",
            "oda_sayisi",
            "metrekare",
            "tarih",
        ],
    },
}


# ============================================================================
# HepsiEmlak seçicileri
# ============================================================================

HEPSIEMLAK_SELECTORS = {
    "common": {
        # İlan seçicileri (yeni Vue yapısı - Ağustos 2026)
        "listing_container": "article.listingCard__box",
        "listing_results": "article.listingCard__box, ul.list-items-container, .search-results",
        "title": "h3.listingCard__title",
        "price": "p.listingCard__price",
        "location": "span.listingCard__location address",
        "date": "time.listingCard__date",
        "link": "a.card-link",
        "firm": "p.listingCard__owner-firm",
        # Yeni özellik listesi (dl/dt/dd)
        "specs": "dl.listingCard__specs div.listingCard__spec-item",
        "spec_label": "dt.listingCard__spec-label",
        "spec_value": "dd",
        # İl açılır menüsü
        "city_dropdown": "div.he-select-base__container, div[data-name='city']",
        "city_list": "div.he-select-base__list, div.he-select__list",
        "city_item": "li.he-select__list-item, li.he-select-base__list-item",
        "city_link": "a.js-city-filter__list-link, span.he-select-base__text",
        "city_radio": "div.he-radio, input[type='radio']",
        # İlçe açılır menüsü
        "county_section": "section.filter-item-wrap.locationCountySec",
        "county_dropdown": "div.js-county-filter div.he-select-base__container",
        "county_placeholder": "span.he-select-base__placeholder",
        "county_list": "div.he-select__list, div.he-select-base__list",
        "county_item": "li.he-select__list-item, li.he-select-base__list-item",
        "county_text": "span.he-select-base__text",
        # Arama butonu
        "search_buttons": [
            "a.btn.btn-red.btn-large",
            "button.btn.btn-red.btn-large",
            "a[data-tracking-label='SearchSubmit']",
            "button[type='submit']",
            ".btn-red",
        ],
        # Sayfalama
        "pagination": [
            "ul.he-pagination__links a.he-pagination__link",
            "ul.he-pagination__links a",
            "a[href*='page=']",
            ".he-pagination a",
            ".pagination a",
        ],
    },
    "konut": {
        "fields": ["oda_sayisi", "metrekare", "bina_yasi", "kat", "emlak_ofisi"],
        "spec_map": {
            "oda_sayisi": ["Oda Sayısı"],
            "metrekare": ["Brüt m²", "Net m²"],
            "bina_yasi": ["Bina Yaşı"],
            "kat": ["Kat"],
        },
        "csv_fields": [
            "fiyat",
            "baslik",
            "il",
            "ilce",
            "mahalle",
            "ilan_linki",
            "ilan_tarihi",
            "oda_sayisi",
            "metrekare",
            "bina_yasi",
            "kat",
            "emlak_ofisi",
        ],
    },
    "arsa": {
        "fields": ["arsa_metrekare", "metrekare_fiyat", "emlak_ofisi"],
        "spec_map": {
            "arsa_metrekare": ["Brüt m²", "Net m²"],
            "metrekare_fiyat": ["m² Fiyatı"],
        },
        "csv_fields": [
            "fiyat",
            "baslik",
            "il",
            "ilce",
            "mahalle",
            "ilan_linki",
            "ilan_tarihi",
            "arsa_metrekare",
            "metrekare_fiyat",
            "emlak_ofisi",
        ],
    },
    "isyeri": {
        "fields": ["metrekare", "emlak_ofisi"],
        "spec_map": {
            "metrekare": ["Brüt m²", "Net m²"],
        },
        "csv_fields": [
            "fiyat",
            "baslik",
            "il",
            "ilce",
            "mahalle",
            "ilan_linki",
            "ilan_tarihi",
            "metrekare",
            "emlak_ofisi",
        ],
    },
    "devremulk": {
        "fields": ["oda_sayisi", "metrekare", "bina_yasi", "kat"],
        "spec_map": {
            "oda_sayisi": ["Oda Sayısı"],
            "metrekare": ["Brüt m²", "Net m²"],
            "bina_yasi": ["Bina Yaşı"],
            "kat": ["Kat"],
        },
        "csv_fields": [
            "fiyat",
            "baslik",
            "il",
            "ilce",
            "mahalle",
            "ilan_linki",
            "ilan_tarihi",
            "oda_sayisi",
            "metrekare",
            "bina_yasi",
            "kat",
        ],
    },
    "turistik_isletme": {
        "fields": ["oda_sayisi", "otel_tipi"],
        "spec_map": {
            "oda_sayisi": ["Oda Sayısı"],
            "otel_tipi": ["Yıldız Sayısı"],
        },
        "csv_fields": [
            "fiyat",
            "baslik",
            "il",
            "ilce",
            "mahalle",
            "ilan_linki",
            "ilan_tarihi",
            "oda_sayisi",
            "otel_tipi",
        ],
    },
}


# ============================================================================
# Ana seçici sözlüğü
# ============================================================================

SELECTORS: dict[str, dict[str, Any]] = {
    "emlakjet": EMLAKJET_SELECTORS,
    "hepsiemlak": HEPSIEMLAK_SELECTORS,
}


def get_selectors(platform: str, category: str | None = None) -> dict[str, Any]:
    """Platform ve kategori için seçicileri getir"""
    if platform not in SELECTORS:
        raise ValueError(f"Unknown platform: {platform}")

    platform_selectors = SELECTORS[platform]

    if category is None:
        return platform_selectors

    if category not in platform_selectors:
        raise ValueError(f"Unknown category '{category}' for platform '{platform}'")

    # Ortak seçicileri kategori seçicileriyle birleştir
    result = {**platform_selectors["common"]}
    result.update(platform_selectors[category])

    return result


def get_common_selectors(platform: str) -> dict[str, Any]:
    """Platform ortak seçicilerini getir"""
    if platform not in SELECTORS:
        raise ValueError(f"Unknown platform: {platform}")

    return SELECTORS[platform]["common"]


def get_category_selectors(platform: str, category: str) -> dict[str, Any]:
    """Kategori seçicilerini getir"""
    if platform not in SELECTORS:
        raise ValueError(f"Unknown platform: {platform}")

    if category not in SELECTORS[platform]:
        raise ValueError(f"Unknown category '{category}' for platform '{platform}'")

    return SELECTORS[platform][category]
