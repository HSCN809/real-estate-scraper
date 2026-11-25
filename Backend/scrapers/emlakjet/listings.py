import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from core.selectors import get_common_selectors
from scrapling.parser import Selector

from scrapers.common.html import as_html
from scrapers.common.pagination import max_page_from_hrefs, max_page_from_texts

from .parsers import ArsaParser, IsyeriParser, KonutParser, TuristikTesisParser
from .urls import normalize_text

_LISTING_HREF_RE = re.compile(r"/ilan/[^/?#]+-\d+(?:/)?(?:[?#]|$)")

CATEGORY_PARSERS = {
    "konut": KonutParser,
    "arsa": ArsaParser,
    "isyeri": IsyeriParser,
    "turistik_tesis": TuristikTesisParser,
    "kat_karsiligi_arsa": ArsaParser,
    "devren_isyeri": IsyeriParser,
    "gunluk_kiralik": KonutParser,
}


def _to_selector(source) -> Selector:
    return source if isinstance(source, Selector) else Selector(as_html(source))


def _first(element, selector: str):
    matches = element.css(selector)
    return matches[0] if matches else None


def _has_similar_parent(element) -> bool:
    parent = getattr(element, "parent", None)
    while parent is not None:
        attrib = getattr(parent, "attrib", None) or {}
        if "similarlisting" in str(attrib.get("class") or "").lower():
            return True
        parent = getattr(parent, "parent", None)
    return False


def parse_category_details(category: str, quick_info: str, title: str) -> dict[str, Any]:
    parser_class = CATEGORY_PARSERS.get(category, KonutParser)
    return parser_class().parse_category_details(quick_info, title)


def _text(element, css_selector: str, default: str = "") -> str:
    if not css_selector:
        return default
    selected = _first(element, css_selector)
    if selected is None:
        return default
    value = " ".join(selected.get_all_text(" ", strip=True).split())
    return value or default


def _attr(element, css_selector: str, attribute: str, default: str = "") -> str:
    if not css_selector:
        return default
    selected = _first(element, css_selector)
    if selected is None:
        return default
    value = str(selected.attrib.get(attribute, "") or "").strip()
    return value or default


def _first_listing_href(element, css_selector: str) -> str:
    selectors = [part.strip() for part in (css_selector or "").split(",") if part.strip()]
    selectors.extend(["h3[data-listing-title] a", "a[data-listing-image]", "a[href*='/ilan/']"])
    seen: set[str] = set()
    for selector in selectors:
        if selector in seen:
            continue
        seen.add(selector)
        for node in element.css(selector):
            href = str(node.attrib.get("href", "") or "").strip()
            if href and "ilan-ver" not in href and _LISTING_HREF_RE.search(href):
                return href
    return ""


def extract_listing_from_card(
    element,
    *,
    page_url: str = "",
    category: str = "konut",
    city: str | None = None,
    district: str | None = None,
    neighborhood: str | None = None,
    scraping_method: str = "",
    scraped_at: str | None = None,
    common_selectors: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if common_selectors is None:
        common_selectors = get_common_selectors("emlakjet")
    title = _text(element, common_selectors.get("title", "h3[data-listing-title] a"))
    text_p_elements = element.css(common_selectors.get("location", "p.text-xs"))
    location = ""
    quick_info = ""
    if text_p_elements:
        location = " ".join(text_p_elements[0].get_all_text(" ", strip=True).split())
    if len(text_p_elements) > 1:
        quick_info = " ".join(text_p_elements[1].get_all_text(" ", strip=True).split())

    price = _text(
        element, common_selectors.get("price", "span.shrink-0.whitespace-nowrap")
    )
    if not all([title, location, price]):
        return None

    listing_url = _first_listing_href(element, common_selectors.get("link", ""))
    if listing_url and page_url:
        listing_url = urljoin(page_url, listing_url)

    badges = []
    for badge in element.css(
        common_selectors.get("badge_wrapper", "span[class*='px-2 py-0.5']")
    ):
        badge_text = " ".join(badge.get_all_text(" ", strip=True).split())
        if badge_text:
            badges.append(normalize_text(badge_text))

    data: dict[str, Any] = {
        "baslik": title,
        "lokasyon": location,
        "fiyat": price,
        "ilan_url": listing_url,
        "resim_url": _attr(
            element, common_selectors.get("image", "img[src*='/listing/']"), "src"
        ),
        "one_cikan": any("one cikan" in badge for badge in badges),
        "yeni": any(badge == "yeni" or badge.startswith("yeni ") for badge in badges),
    }
    data.update(parse_category_details(category, quick_info, title))
    data["tarih"] = scraped_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if scraping_method:
        data["scraping_method"] = scraping_method
    if city:
        data["il"] = city
    if district:
        data["ilce"] = district
    if neighborhood:
        data["mahalle"] = neighborhood
    return data


def extract_listings_from_html(
    source,
    *,
    page_url: str = "",
    category: str = "konut",
    city: str | None = None,
    district: str | None = None,
    neighborhood: str | None = None,
    scraping_method: str = "",
) -> list[dict[str, Any]]:
    tree = _to_selector(source)
    common_selectors = get_common_selectors("emlakjet")
    listing_selector = common_selectors.get(
        "listing_container", "article[data-listing-id]"
    )
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    listings: list[dict[str, Any]] = []
    for element in tree.css(listing_selector):
        if _has_similar_parent(element):
            continue
        data = extract_listing_from_card(
            element,
            page_url=page_url,
            category=category,
            city=city,
            district=district,
            neighborhood=neighborhood,
            scraping_method=scraping_method,
            scraped_at=scraped_at,
            common_selectors=common_selectors,
        )
        if data:
            listings.append(data)
    return listings


def extract_total_pages(source) -> int:
    tree = _to_selector(source)
    links = tree.css("a[href*='sayfa=']")
    hrefs = []
    texts = []
    for link in links:
        hrefs.append(link.attrib.get("href"))
        texts.append(" ".join(link.get_all_text(" ", strip=True).split()))
    page_numbers = [
        max_page_from_hrefs(hrefs, "sayfa"),
        max_page_from_texts(texts),
    ]
    active = _first(tree, "span[aria-current='page']")
    if active is not None:
        page_numbers.append(
            max_page_from_texts([" ".join(active.get_all_text(" ", strip=True).split())])
        )
    return max(page_numbers) if page_numbers else 1
