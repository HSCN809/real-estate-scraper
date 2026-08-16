import re
import unicodedata
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


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
