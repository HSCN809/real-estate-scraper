from scrapers.emlakjet.filters import extract_primary_slug_from_url, matches_filters
from scrapers.emlakjet.listings import extract_listings_from_html, extract_total_pages
from scrapers.emlakjet.urls import (
    build_city_url,
    build_page_url,
    extract_location_name,
    page_number_from_url,
    parse_location_options,
    should_scrape_city_level,
    slugify_location,
)
from utils.logger import should_forward_ui_log

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
    cities = parse_location_options(
        """
        <a href="/satilik-konut/adana">Adana</a>
        <a href="/satilik-konut/bayburt"></a>
        """,
        "https://www.emlakjet.com/satilik-konut",
    )
    names = {item["name"].casefold() for item in cities}
    assert "adana" in names
    assert "bayburt" in names

    districts = parse_location_options(
        """
        <a href="/satilik-daire/istanbul-kadikoy">Kadıköy</a>
        <a href="/satilik-daire/istanbul-bagcilar-100-yil-mahallesi">Bağcılar 100. Yıl Mahallesi</a>
        <a href="/satilik-daire/istanbul-fatih">İstanbul Fatih</a>
        <a href="/satilik-daire/istanbul-besiktas-bebek-mahallesi">Beşiktaş Bebek</a>
        """,
        "https://www.emlakjet.com/satilik-daire/istanbul",
        "İlçeler",
    )
    district_names = {item["name"] for item in districts}
    assert "Kadıköy" in district_names
    assert "Fatih" in district_names
    assert not any("mahalle" in name.casefold() for name in district_names)
    assert "Beşiktaş Bebek" not in district_names


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


def test_emlakjet_keeps_ilan_detail_urls_with_subtype():
    url = "https://www.emlakjet.com/ilan/satilik-daire-istanbul-kadikoy-123"
    assert matches_filters(
        url,
        "satilik",
        "konut",
        "daire",
        {"satilik-daire"},
        {"satilik-isyeri"},
    )


def test_emlakjet_stays_at_city_when_page_limit_set():
    assert should_scrape_city_level(1, 22694, has_district_filter=False) is True
    assert should_scrape_city_level(5, 22694, has_district_filter=False) is False
    assert should_scrape_city_level(None, 22694, has_district_filter=False) is False
    assert should_scrape_city_level(None, 800, has_district_filter=False) is True
    assert should_scrape_city_level(5, 22694, has_district_filter=True) is False


def test_ui_log_does_not_treat_thirty_listings_as_zero():
    assert should_forward_ui_log("Şırnak → 0 ilan, il atlanıyor.", "info") is True
    assert should_forward_ui_log("Sayfa 1: 30 ilan çıkarıldı", "info") is False
    assert should_forward_ui_log("Bağcılar → 20 ilan, ilçe seviyesinden taranıyor.", "info") is True


def test_emlakjet_keeps_seo_ilan_urls():
    url = "https://www.emlakjet.com/ilan/cumhuriyet-caddesinde-icerisi-yenilenmis-dubleks-17854427"
    assert extract_primary_slug_from_url(url) == "ilan"
    assert matches_filters(
        url,
        "satilik",
        "konut",
        None,
        {"satilik-daire", "satilik-villa"},
        {"satilik-isyeri"},
    )


def test_emlakjet_reads_live_ilan_href():
    html = """
    <article data-listing-id="19731432" class="listing-row-card-shell">
      <a data-listing-image href="/ilan/safak-residence-da-arakat-kapali-mutfak-21-daire-19731432"></a>
      <h3 data-listing-title>
        <a class="title" href="/ilan/safak-residence-da-arakat-kapali-mutfak-21-daire-19731432">Şafak Residence 2+1</a>
      </h3>
      <p class="text-xs">İstanbul, Esenyurt</p>
      <p class="text-xs">Daire | 2+1 | 3. Kat | 95 m²</p>
      <span class="shrink-0 whitespace-nowrap">5.100.000 TL</span>
    </article>
    """
    listings = extract_listings_from_html(
        html,
        page_url="https://www.emlakjet.com/satilik-daire/istanbul",
        category="konut",
    )
    assert len(listings) == 1
    assert listings[0]["ilan_url"].endswith(
        "/ilan/safak-residence-da-arakat-kapali-mutfak-21-daire-19731432"
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
