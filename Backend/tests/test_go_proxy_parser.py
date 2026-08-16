import os
import sys
import types

from bs4 import BeautifulSoup

BACKEND = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, BACKEND)

pkg = types.ModuleType("scrapers.hepsiemlak")
pkg.__path__ = [os.path.join(BACKEND, "scrapers", "hepsiemlak")]
pkg.__package__ = "scrapers.hepsiemlak"
sys.modules["scrapers.hepsiemlak"] = pkg
main_mod = types.ModuleType("scrapers.hepsiemlak.main")
main_mod.save_listings_to_db = lambda *args, **kwargs: None
sys.modules["scrapers.hepsiemlak.main"] = main_mod

from scrapers.hepsiemlak.go_proxy_scraper import HepsiemlakGoProxyScraper

FIXTURE = """
<html><body>
<article class="listingCard__box">
  <a class="card-link" href="/ilan/123">
    <h3 class="listingCard__title">3+1 Daire Kadikoy</h3>
  </a>
  <p class="listingCard__price">4.250.000 TL</p>
  <span class="list-view-location"><address>Istanbul / Kadikoy / Moda</address></span>
  <time class="listingCard__date">Bugun</time>
  <p class="listingCard__owner-firm">Demo Emlak</p>
</article>
</body></html>
"""


def test_extract_listings_from_fixture_html():
    scraper = HepsiemlakGoProxyScraper(proxy_url="http://127.0.0.1:9")
    soup = BeautifulSoup(FIXTURE, "html.parser")
    listings = scraper.extract_listings_from_page(
        soup, page_url="https://www.hepsiemlak.com/istanbul-satilik"
    )
    assert len(listings) == 1
    item = listings[0]
    assert item["baslik"] == "3+1 Daire Kadikoy"
    assert item["fiyat"] == "4.250.000 TL"
    assert item["il"] == "Istanbul"
    assert item["ilce"] == "Kadikoy"
    assert item["ilan_linki"].endswith("/ilan/123")


def test_get_total_pages_from_pagination():
    scraper = HepsiemlakGoProxyScraper(proxy_url="http://127.0.0.1:9")
    html = """
    <ul class="he-pagination__links">
      <a href="?page=1">1</a>
      <a href="?page=4">4</a>
    </ul>
    """
    assert scraper.get_total_pages(BeautifulSoup(html, "html.parser")) == 4
