from scrapers.hepsiemlak.filters import extract_subtype_slug_from_url, matches_filters
from scrapers.hepsiemlak.listings import extract_listings_from_html, extract_total_pages
from scrapers.hepsiemlak.urls import (
    build_location_url,
    build_page_url,
    normalize_location_slug,
    page_number_from_url,
)

HEPSIEMLAK_FIXTURE = """
<html><body>
<span class="applied-filters__count">için 33.244 ilan bulundu</span>
<article class="listingCard__box">
  <a class="card-link" href="/istanbul-satilik/daire/123">
    <h3 class="listingCard__title">3+1 Daire Kadikoy</h3>
  </a>
  <p class="listingCard__price">4.250.000 TL</p>
  <span class="list-view-location"><address>Istanbul / Kadikoy / Moda</address></span>
  <time class="listingCard__date">Bugun</time>
  <p class="listingCard__owner-firm">Demo Emlak</p>
  <dl class="listingCard__specs">
    <div class="listingCard__spec-item">
      <dt class="listingCard__spec-label">Oda Sayısı</dt>
      <dd>3+1</dd>
    </div>
    <div class="listingCard__spec-item">
      <dt class="listingCard__spec-label">Brüt m²</dt>
      <dd>140</dd>
    </div>
  </dl>
</article>
<ul class="he-pagination__links">
  <a href="?page=1">1</a>
  <a href="?page=2">2</a>
  <a href="?page=1369">1369</a>
</ul>
</body></html>
"""


def test_hepsiemlak_url_builder():
    assert normalize_location_slug("İstanbul") == "istanbul"
    assert (
        build_location_url("İstanbul", "satilik")
        == "https://www.hepsiemlak.com/istanbul-satilik"
    )
    assert (
        build_location_url("İstanbul", "satilik", subtype_path="/satilik/daire")
        == "https://www.hepsiemlak.com/istanbul-satilik/daire"
    )
    assert (
        build_page_url("https://www.hepsiemlak.com/istanbul-satilik", 3)
        == "https://www.hepsiemlak.com/istanbul-satilik?page=3"
    )
    assert page_number_from_url("https://www.hepsiemlak.com/istanbul-satilik?page=8") == 8


def test_hepsiemlak_filters():
    url = "https://www.hepsiemlak.com/istanbul-satilik/daire/119379-758"
    assert extract_subtype_slug_from_url(url, "satilik") == "daire"
    assert matches_filters(url, "satilik", "konut", "daire", {"daire", "villa"})
    assert not matches_filters(url, "satilik", "konut", "villa", {"daire", "villa"})
    numeric = "https://www.hepsiemlak.com/istanbul-satilik/119379-758"
    assert matches_filters(numeric, "satilik", "konut", None, {"daire"})


def test_hepsiemlak_listings_and_pagination():
    listings = extract_listings_from_html(
        HEPSIEMLAK_FIXTURE,
        page_url="https://www.hepsiemlak.com/istanbul-satilik",
        category="konut",
        scraping_method="test",
    )
    assert len(listings) == 1
    item = listings[0]
    assert item["baslik"] == "3+1 Daire Kadikoy"
    assert item["fiyat"] == "4.250.000 TL"
    assert item["il"] == "Istanbul"
    assert item["ilce"] == "Kadikoy"
    assert item["ilan_linki"].endswith("/istanbul-satilik/daire/123")
    assert item["oda_sayisi"] == "3+1"
    assert item["metrekare"] == "140"
    assert extract_total_pages(HEPSIEMLAK_FIXTURE) == 1386
