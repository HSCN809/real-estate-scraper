import re
import unicodedata
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from scrapling.parser import Selector

from scrapers.common.html import as_html

_EXCLUDED_LOCATION_SEGMENTS = {
    "projeler",
    "emlakcidan",
    "sahibinden",
    "muteahhitten",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    replacements = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc")
    return ascii_only.translate(replacements).casefold().strip()


def normalize_location_token(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_only = "".join(ch for ch in text if not unicodedata.combining(ch))
    ascii_only = ascii_only.translate(str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc"))
    return re.sub(r"\s+", " ", ascii_only).strip().casefold()


def extract_location_name(raw_text: str) -> str:
    compact = " ".join(str(raw_text or "").split())
    compact = re.sub(r"\s+\(?[\d\.\,]+\)?$", "", compact).strip()
    compact = re.sub(
        r"\s+\d[\d\.\,]*\s+ilan.*$", "", compact, flags=re.IGNORECASE
    ).strip()
    compact = re.sub(
        r"\s+(satılık|satilik|kiralık|kiralik)\b.*$", "", compact, flags=re.IGNORECASE
    ).strip()
    compact = re.sub(r"\s*[-–|•]+\s*$", "", compact).strip()
    return compact


def slugify_location(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name or ""))
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    ascii_only = ascii_only.translate(str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc"))
    return re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only).strip("-").lower()


def build_city_url(
    city_name: str,
    *,
    base_url: str,
    site_base: str,
    subtype_path: str | None = None,
) -> str:
    base_path = (subtype_path or base_url).strip()
    if base_path.startswith(("http://", "https://")):
        path_part = urlparse(base_path).path.strip("/")
    else:
        path_part = base_path.strip("/")

    if not path_part:
        return base_url

    city_slug = slugify_location(city_name)
    if not city_slug:
        return f"{site_base.rstrip('/')}/{path_part}"
    return f"{site_base.rstrip('/')}/{path_part}/{city_slug}"


def build_page_url(base_url: str, page_num: int) -> str:
    if page_num <= 1:
        return base_url
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["sayfa"] = [str(page_num)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def page_number_from_url(url: str) -> int:
    try:
        page_values = parse_qs(urlparse(url).query).get("sayfa")
        if page_values and page_values[0].isdigit():
            return int(page_values[0])
    except Exception:  # nosec
        pass
    return 1


def location_kind_from_type(location_type: str | None) -> str:
    compact = normalize_text(location_type or "")
    if "mahalle" in compact:
        return "mahalle"
    if "ilce" in compact:
        return "ilce"
    return "il"


def should_scrape_city_level(
    max_pages: int | None,
    listing_count: int | None,
    *,
    has_district_filter: bool,
    pagination_limit: int = 1500,
    page_size: int = 30,
) -> bool:
    if has_district_filter:
        return False
    # City pages can serve up to pagination_limit / page_size pages without district drilldown.
    if (
        max_pages is not None
        and max_pages > 0
        and max_pages * page_size <= pagination_limit
    ):
        return True
    return (listing_count or 0) <= pagination_limit


def _is_allowed_location_child(
    parent_segment: str, child_segment: str, kind: str
) -> bool:
    if not child_segment or child_segment in _EXCLUDED_LOCATION_SEGMENTS:
        return False
    if kind == "mahalle":
        return True

    parent = parent_segment.strip("-")
    child = child_segment.strip("-")
    prefix = f"{parent}-"
    if child.startswith(prefix):
        remainder = child[len(prefix) :]
    else:
        remainder = child

    if "mahalle" in remainder:
        return False
    return "-" not in remainder


def parse_location_options(
    source, current_url: str, location_type: str | None = None
) -> list[dict[str, str]]:
    selector = source if isinstance(source, Selector) else Selector(as_html(source))
    base_path = urlparse(current_url).path.rstrip("/")
    last_segment = base_path.rsplit("/", 1)[-1]
    kind = location_kind_from_type(location_type)
    options: list[dict[str, str]] = []
    seen_names: set[str] = set()

    for link in selector.css("a[href]"):
        href = str(link.attrib.get("href") or "").strip()
        if not href or "sayfa=" in href or "filtreler=" in href:
            continue
        absolute_url = urljoin(current_url, href)
        href_path = urlparse(absolute_url).path.rstrip("/")
        if href_path == base_path or not href_path.startswith(
            (base_path + "/", base_path + "-")
        ):
            continue
        child_segment = href_path.rsplit("/", 1)[-1]
        if not _is_allowed_location_child(last_segment, child_segment, kind):
            continue

        link_text = " ".join(str(link.get_all_text(separator=" ")).split())
        location_name = extract_location_name(link_text)
        normalized_segment = normalize_text(last_segment)
        normalized_name = normalize_text(location_name)
        if normalized_segment and normalized_name.startswith(normalized_segment + "-"):
            location_name = location_name[len(last_segment) :].strip()
        elif normalized_segment and normalized_name.startswith(normalized_segment + " "):
            location_name = location_name[len(last_segment) :].strip(" -")
        if not location_name:
            location_name = child_segment.replace("-", " ")
        if not location_name:
            continue
        normalized = normalize_text(location_name)
        if normalized in seen_names:
            continue
        seen_names.add(normalized)
        options.append({"name": location_name, "url": absolute_url})
    return options
