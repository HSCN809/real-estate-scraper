import unicodedata
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

BASE_HOST = "https://www.hepsiemlak.com"


def normalize_location_slug(text: str) -> str:
    value = unicodedata.normalize("NFC", text or "")
    replacements = {
        "İ": "i",
        "I": "i",
        "Ğ": "g",
        "Ü": "u",
        "Ş": "s",
        "Ö": "o",
        "Ç": "c",
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }
    for tr_char, en_char in replacements.items():
        value = value.replace(tr_char, en_char)
    return value.lower().replace(" ", "-")


def category_or_subtype_slug(
    listing_type: str,
    category: str,
    subtype_path: str | None,
    categories: dict | None = None,
) -> str:
    if subtype_path:
        parts = subtype_path.strip("/").split("/")
        return parts[-1] if len(parts) >= 2 else ""
    category_path = (categories or {}).get(listing_type, {}).get(category, "")
    parts = category_path.strip("/").split("/") if category_path else []
    return parts[-1] if len(parts) >= 2 else ""


def build_location_url(
    location_name: str,
    listing_type: str,
    category: str = "konut",
    subtype_path: str | None = None,
    categories: dict | None = None,
) -> str:
    location_slug = normalize_location_slug(location_name)
    suffix = category_or_subtype_slug(
        listing_type, category, subtype_path, categories
    )
    base_url = f"{BASE_HOST}/{location_slug}-{listing_type}"
    return f"{base_url}/{suffix}" if suffix else base_url


def build_page_url(base_url: str, page_num: int) -> str:
    if page_num <= 1:
        return base_url
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_num)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def page_number_from_url(url: str) -> int:
    try:
        page_values = parse_qs(urlparse(url).query).get("page")
        if page_values and page_values[0].isdigit():
            return int(page_values[0])
    except Exception:  # nosec
        pass
    return 1
