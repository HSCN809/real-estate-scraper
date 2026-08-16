import re


def max_page_from_hrefs(hrefs: list[str | None], param: str) -> int:
    max_page = 1
    pattern = re.compile(rf"[?&]{re.escape(param)}=(\d+)")
    for href in hrefs:
        if not href:
            continue
        match = pattern.search(href)
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page


def max_page_from_texts(texts: list[str | None]) -> int:
    max_page = 1
    for text in texts:
        value = (text or "").strip()
        if value.isdigit():
            max_page = max(max_page, int(value))
    return max_page


def pages_from_listing_count(count_text: str | None, per_page: int) -> int:
    if not count_text:
        return 1
    clean = count_text.replace(".", "").replace(",", "")
    match = re.search(r"(\d+)", clean)
    if not match:
        return 1
    total = int(match.group(1))
    if total <= per_page:
        return 1
    return max(1, (total + per_page - 1) // per_page)
