from scrapers.common.pagination import (
    max_page_from_hrefs,
    max_page_from_texts,
    pages_from_listing_count,
)


def test_hepsiemlak_hrefs_and_count():
    hrefs = [
        "https://www.hepsiemlak.com/istanbul-satilik",
        "https://www.hepsiemlak.com/istanbul-satilik?page=2",
        "https://www.hepsiemlak.com/istanbul-satilik?page=1369",
    ]
    assert max_page_from_hrefs(hrefs, "page") == 1369
    assert max_page_from_texts(["1", "2", "...", "1369"]) == 1369
    assert pages_from_listing_count("için 33.244 ilan bulundu", 24) == 1386


def test_emlakjet_sayfa_param():
    hrefs = [
        "/satilik-daire/istanbul?sayfa=2",
        "/satilik-daire/istanbul?sayfa=50",
    ]
    assert max_page_from_hrefs(hrefs, "sayfa") == 50
    assert pages_from_listing_count("1.200 ilan", 30) == 40
