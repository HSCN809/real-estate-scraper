from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from core.selectors import get_common_selectors, get_selectors

from scrapers.common.html import as_html
from scrapers.common.pagination import (
    max_page_from_hrefs,
    max_page_from_texts,
    pages_from_listing_count,
)

_MISSING = "Belirtilmemis"
_LOCATION_SELECTORS = [
    "span.listingCard__location address",
    "span.list-view-location address",
    "span.list-view-location",
    ".list-view-location address",
    ".list-view-location",
    "address",
]
_LISTING_FALLBACKS = [
    "article.listingCard__box",
    "li.listing-item:not(.listing-item--promo)",
    "li.listing-item",
]


def _text(element, css_selector: str | list[str] | None, default: str = _MISSING) -> str:
    selectors = (
        [item for item in css_selector if item]
        if isinstance(css_selector, list)
        else ([css_selector] if css_selector else [])
    )
    for selector in selectors:
        selected = element.select_one(selector)
        if selected:
            value = " ".join(selected.get_text(" ", strip=True).split())
            if value:
                return value
    return default


def _attr(
    element,
    css_selector: str | list[str] | None,
    attribute: str,
    default: str = _MISSING,
) -> str:
    selectors = (
        [item for item in css_selector if item]
        if isinstance(css_selector, list)
        else ([css_selector] if css_selector else [])
    )
    for selector in selectors:
        selected = element.select_one(selector)
        if not selected:
            continue
        value = selected.get(attribute, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        value = str(value or "").strip()
        if value:
            return value
    return default


def _is_missing(value: Any) -> bool:
    return not value or str(value).lower().startswith("belirtilmem")


def _spec_values(element, common_selectors: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in element.select(
        common_selectors.get(
            "specs", "dl.listingCard__specs div.listingCard__spec-item"
        )
    ):
        label = _text(
            item,
            common_selectors.get("spec_label", "dt.listingCard__spec-label"),
            default="",
        )
        value = _text(item, common_selectors.get("spec_value", "dd"), default="")
        if label and value:
            values[label.strip()] = value.strip()
    return values


def _category_data(element, category: str, common_selectors: dict[str, Any]) -> dict[str, Any]:
    spec_map = get_selectors("hepsiemlak", category).get("spec_map") or {}
    values = _spec_values(element, common_selectors)
    return {
        field: next((values[label] for label in labels if label in values), _MISSING)
        for field, labels in spec_map.items()
    }


def extract_listing_from_card(
    element,
    *,
    page_url: str = "",
    category: str = "konut",
    city: str | None = None,
    district: str | None = None,
    scraping_method: str = "",
    scraped_at: str | None = None,
) -> dict[str, Any] | None:
    common_selectors = get_common_selectors("hepsiemlak")
    listing_link = _attr(element, common_selectors.get("link", "a.card-link"), "href")
    if _is_missing(listing_link):
        return None
    if page_url:
        listing_link = urljoin(page_url, listing_link)

    location_text = ""
    for loc_selector in _LOCATION_SELECTORS:
        location_text = _text(element, loc_selector, default="")
        if location_text and "/" in location_text:
            break
    location_parts = [part.strip() for part in location_text.split("/") if part.strip()]

    data: dict[str, Any] = {
        "fiyat": _text(element, common_selectors.get("price", "p.listingCard__price")),
        "baslik": _text(
            element,
            [
                common_selectors.get("title", "h3.listingCard__title"),
                "h3.listingCard__title",
                "h2",
                "a.card-link h2",
                "a.card-link h3",
            ],
        ),
        "il": location_parts[0] if location_parts else _MISSING,
        "ilce": location_parts[1] if len(location_parts) > 1 else _MISSING,
        "mahalle": location_parts[2] if len(location_parts) > 2 else _MISSING,
        "ilan_linki": listing_link,
        "ilan_tarihi": _text(
            element, common_selectors.get("date", "time.listingCard__date")
        ),
        "emlak_ofisi": _text(
            element, common_selectors.get("firm", "p.listingCard__owner-firm")
        ),
    }
    data.update(_category_data(element, category, common_selectors))

    if city and _is_missing(data.get("il")):
        data["il"] = city
    if district and _is_missing(data.get("ilce")):
        data["ilce"] = district
    data["scraped_at"] = scraped_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if scraping_method:
        data["scraping_method"] = scraping_method
    return data


def extract_listings_from_html(
    source,
    *,
    page_url: str = "",
    category: str = "konut",
    city: str | None = None,
    district: str | None = None,
    scraping_method: str = "",
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(as_html(source), "html.parser")
    common_selectors = get_common_selectors("hepsiemlak")
    selectors = [
        common_selectors.get("listing_container", "article.listingCard__box"),
        *_LISTING_FALLBACKS,
    ]
    listing_elements = []
    for selector in selectors:
        if not selector:
            continue
        listing_elements = soup.select(selector)
        if listing_elements:
            break

    listings: list[dict[str, Any]] = []
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for element in listing_elements:
        data = extract_listing_from_card(
            element,
            page_url=page_url,
            category=category,
            city=city,
            district=district,
            scraping_method=scraping_method,
            scraped_at=scraped_at,
        )
        if data:
            listings.append(data)
    return listings


def extract_total_pages(source) -> int:
    soup = BeautifulSoup(as_html(source), "html.parser")
    count_el = soup.select_one("span.applied-filters__count")
    count_text = count_el.get_text(" ", strip=True) if count_el else ""
    page_links = soup.select(
        "ul.he-pagination__links a, ul.he-pagination a, a[href*='page=']"
    )
    hrefs = []
    texts = []
    for link in page_links:
        raw_href = link.get("href")
        hrefs.append(raw_href[0] if isinstance(raw_href, list) else raw_href)
        texts.append(link.get_text(" ", strip=True))
    return max(
        max_page_from_hrefs(hrefs, "page"),
        max_page_from_texts(texts),
        pages_from_listing_count(count_text, 24),
    )
