from scrapers.emlakjet.filters import extract_primary_slug_from_url, matches_filters
from scrapers.emlakjet.listings import extract_listings_from_html, extract_total_pages
from scrapers.emlakjet.urls import (
    build_city_url,
    build_page_url,
    extract_location_name,
    page_number_from_url,
    slugify_location,
)

EMLAKJET_FIXTURE = """
<html><body>
<article data-listing-id="99">
  <h3 data-listing-title>
    <a href="/ilan/satilik-daire-istanbul-kadikoy-123">Kadikoy 2+1 Daire</a>
  </h3>
  <p class="text-xs">İstanbul, Kadıköy, Moda</p>
  <p class="text-xs">Daire | 2+1 | 3. Kat | 95 m²</p>
  <span class="shrink-0 whitespace-nowrap">5.100.000 TL</span>
  <img src="/listing/photo.jpg" />
  <span class="px-2 py-0.5">Yeni</span>
</article>
<a href="/satilik-konut/istanbul?sayfa=2">2</a>
<a href="/satilik-konut/istanbul?sayfa=50">50</a>
<span aria-current="page">1</span>
</body></html>
"""


def test_emlakjet_url_builder():
    assert slugify_location("Kadıköy") == "kadikoy"
    assert (
        build_city_url(
            "İstanbul",
            base_url="https://www.emlakjet.com/satilik-konut",
            site_base="https://www.emlakjet.com",
        )
        == "https://www.emlakjet.com/satilik-konut/istanbul"
    )
    assert (
        build_page_url("https://www.emlakjet.com/satilik-konut/istanbul", 4)
        == "https://www.emlakjet.com/satilik-konut/istanbul?sayfa=4"
    )
    assert page_number_from_url(
        "https://www.emlakjet.com/satilik-konut/istanbul?sayfa=9"
    ) == 9
    assert extract_location_name("Kadıköy 1.234 ilan") == "Kadıköy"


def test_emlakjet_filters():
    url = "https://www.emlakjet.com/satilik-daire/istanbul"
    assert extract_primary_slug_from_url(url) == "satilik-daire"
    assert matches_filters(
        url,
        "satilik",
        "konut",
        "daire",
        {"satilik-daire"},
        {"satilik-isyeri"},
    )
    assert not matches_filters(
        url,
        "satilik",
        "konut",
        "villa",
        {"satilik-villa"},
        {"satilik-isyeri"},
    )


def test_emlakjet_listings_and_pagination():
    listings = extract_listings_from_html(
        EMLAKJET_FIXTURE,
        page_url="https://www.emlakjet.com/satilik-konut/istanbul",
        category="konut",
        city="İstanbul",
        scraping_method="test",
    )
    assert len(listings) == 1
    item = listings[0]
    assert item["baslik"] == "Kadikoy 2+1 Daire"
    assert item["fiyat"] == "5.100.000 TL"
    assert item["lokasyon"] == "İstanbul, Kadıköy, Moda"
    assert item["ilan_url"].endswith("/ilan/satilik-daire-istanbul-kadikoy-123")
    assert item["oda_sayisi"] == "2+1"
    assert item["yeni"] is True
    assert item["il"] == "İstanbul"
    assert extract_total_pages(EMLAKJET_FIXTURE) == 50


def test_emlakjet_skips_similar_listings():
    html = """
    <html><body>
    <article data-listing-id="1">
      <h3 data-listing-title><a href="/satilik-daire/1">Ana ilan</a></h3>
      <p class="text-xs">İstanbul, Kadıköy</p>
      <span class="shrink-0 whitespace-nowrap">1.000.000 TL</span>
    </article>
    <div class="similarListing">
      <article data-listing-id="2">
        <h3 data-listing-title><a href="/satilik-daire/2">Benzer ilan</a></h3>
        <p class="text-xs">İstanbul, Üsküdar</p>
        <span class="shrink-0 whitespace-nowrap">2.000.000 TL</span>
      </article>
    </div>
    </body></html>
    """
    listings = extract_listings_from_html(html, category="konut")
    assert [item["baslik"] for item in listings] == ["Ana ilan"]
