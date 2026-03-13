#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HepsiEmlak icin Selenium ve Scrapling modlari karsilastirmasi."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Proje root'u ekle
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.logger import get_logger

logger = get_logger(__name__)

MAX_PAGES = 6
WAIT_BETWEEN_TESTS_SECONDS = 5
TARGET_CITY = "İstanbul"
TARGET_LISTING_TYPE = "kiralik"
TARGET_CATEGORY = "konut"
ENABLE_STEALTH_SESSION_BENCHMARK = False


def _build_page_url(base_url: str, page_num: int) -> str:
    """Sayfa numarasina gore URL uret."""
    if page_num <= 1:
        return base_url

    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_num)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _get_page_number(url: str) -> int:
    """URL'den page query param degerini cikar."""
    try:
        parsed = urlparse(url)
        page_values = parse_qs(parsed.query).get("page")
        if page_values and page_values[0].isdigit():
            return int(page_values[0])
    except Exception:
        pass
    return 1


def _count_listing_elements(response, container_selector: str) -> int:
    """Response uzerinden listing sayisini bul."""
    try:
        return len(response.css(container_selector))
    except Exception:
        return 0


def _flatten_selenium_results(raw_result) -> list:
    """Selenium sonucunu sehir/ilce agacindan duz listeye cevir."""
    rows = []
    if not isinstance(raw_result, dict):
        return rows

    for city, city_data in raw_result.items():
        if isinstance(city_data, list):
            for item in city_data:
                if isinstance(item, dict):
                    row = dict(item)
                    row.setdefault("city_key", city)
                    rows.append(row)
        elif isinstance(city_data, dict):
            for district, district_listings in city_data.items():
                if not isinstance(district_listings, list):
                    continue
                for item in district_listings:
                    if isinstance(item, dict):
                        row = dict(item)
                        row.setdefault("city_key", city)
                        row.setdefault("district_key", district)
                        rows.append(row)

    return rows


def _build_method_detail_rows(method_result: dict) -> list:
    """Metot sonucundan Excel'e yazilabilir detay satirlari uret."""
    method = method_result.get("method", "")
    payload = method_result.get("result")

    if method == "selenium":
        return _flatten_selenium_results(payload)

    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("listings"), list):
        return [row for row in payload["listings"] if isinstance(row, dict)]

    if method == "scrapling_dynamic_session":
        page_details = payload.get("page_details", [])
        return [row for row in page_details if isinstance(row, dict)]

    if method.startswith("scrapling_spider_"):
        page_counts = payload.get("page_listing_counts", {})
        rows = []
        if isinstance(page_counts, dict):
            for page_str, count in page_counts.items():
                try:
                    page_num = int(page_str)
                except Exception:
                    page_num = page_str
                rows.append(
                    {
                        "page": page_num,
                        "listings": count,
                        "missing": page_num in set(payload.get("missing_pages", [])),
                    }
                )
        return rows

    return []


def _export_excel_reports(results: list, output_dir: Path) -> None:
    """Benchmark sonuclarini lokal Excel dosyalarina yaz."""
    try:
        import pandas as pd
    except Exception as e:
        print(f"\n⚠️ Excel export atlandi (pandas import hatasi): {e}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    details_dir = output_dir / "method_details"
    details_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for result in results:
        summary_rows.append(
            {
                "method": result.get("method"),
                "duration_seconds": result.get("duration", 0),
                "listings": result.get("listings", 0),
                "max_pages": result.get("max_pages", 0),
                "has_error": "error" in result,
                "error": result.get("error", ""),
            }
        )

    summary_path = output_dir / "simple_comparison_summary.xlsx"
    pd.DataFrame(summary_rows).to_excel(summary_path, index=False)
    print(f"📁 Excel summary kaydedildi: {summary_path}")

    for result in results:
        method = result.get("method", "unknown_method")
        detail_rows = _build_method_detail_rows(result)

        if detail_rows:
            detail_df = pd.DataFrame(detail_rows)
        else:
            detail_df = pd.DataFrame(
                [
                    {
                        "method": method,
                        "note": "Detay veri yok, sadece ozet metrik mevcut.",
                        "duration_seconds": result.get("duration", 0),
                        "listings": result.get("listings", 0),
                        "error": result.get("error", ""),
                    }
                ]
            )

        detail_path = details_dir / f"{method}.xlsx"
        detail_df.to_excel(detail_path, index=False)
        print(f"📁 Excel detay kaydedildi: {detail_path}")


def run_selenium_test(max_pages: int = MAX_PAGES):
    """Selenium tabanli scraper'i calistir."""
    print(f"\n🔵 Selenium testi basliyor... (max_pages={max_pages})\n")

    try:
        from scrapers.hepsiemlak import HepsiemlakScraper
        from core.driver_manager import DriverManager

        driver_manager = DriverManager()
        driver = driver_manager.start()

        try:
            scraper = HepsiemlakScraper(
                driver=driver,
                listing_type=TARGET_LISTING_TYPE,
                category=TARGET_CATEGORY,
                selected_cities=[TARGET_CITY],
                selected_districts={},
            )

            start_time = time.time()
            result = scraper.start_scraping_api(max_pages=max_pages)
            end_time = time.time()
        finally:
            driver_manager.stop()

        duration = end_time - start_time

        total_listings = 0
        if isinstance(result, dict):
            for city_data in result.values():
                if isinstance(city_data, list):
                    total_listings += len(city_data)
                elif isinstance(city_data, dict):
                    for district_listings in city_data.values():
                        total_listings += len(district_listings)

        print(f"\n✅ Selenium tamamlandi: {duration:.2f}s, {total_listings} ilan")

        return {
            "method": "selenium",
            "duration": duration,
            "listings": total_listings,
            "max_pages": max_pages,
            "result": result,
        }

    except Exception as e:
        print(f"❌ Selenium testi hatasi: {e}")
        import traceback

        traceback.print_exc()
        return {
            "method": "selenium",
            "duration": 0,
            "listings": 0,
            "max_pages": max_pages,
            "error": str(e),
        }


def run_scrapling_session_test(use_stealth: bool, max_pages: int = MAX_PAGES):
    """Scrapling tabanli mevcut scraper'i session moduna gore calistir."""
    mode_name = "stealth_session" if use_stealth else "fetcher_session"
    print(f"\n🟢 Scrapling ({mode_name}) testi basliyor... (max_pages={max_pages})")

    try:
        from scrapling_scraper import HepsiemlakScraplingScraper

        scraper = HepsiemlakScraplingScraper(
            listing_type=TARGET_LISTING_TYPE,
            category=TARGET_CATEGORY,
            selected_cities=[TARGET_CITY],
            selected_districts={},
            use_stealth=use_stealth,
            headless=True,
        )

        start_time = time.time()
        result = scraper.start_scraping(max_pages_per_city=max_pages, max_pages_per_district=max_pages)
        end_time = time.time()

        duration = end_time - start_time
        total_listings = len(result.get("listings", []))

        print(f"\n✅ Scrapling ({mode_name}) tamamlandi: {duration:.2f}s, {total_listings} ilan")

        return {
            "method": f"scrapling_{mode_name}",
            "duration": duration,
            "listings": total_listings,
            "max_pages": max_pages,
            "use_stealth": use_stealth,
            "result": result,
        }

    except Exception as e:
        print(f"❌ Scrapling ({mode_name}) testi hatasi: {e}")
        import traceback

        traceback.print_exc()
        return {
            "method": f"scrapling_{mode_name}",
            "duration": 0,
            "listings": 0,
            "max_pages": max_pages,
            "use_stealth": use_stealth,
            "error": str(e),
        }


def run_scrapling_dynamic_session_test(max_pages: int = MAX_PAGES):
    """Scrapling DynamicSession ile benchmark calistir."""
    print(f"\n🟨 Scrapling (dynamic_session) testi basliyor... (max_pages={max_pages})")

    try:
        from scrapling.fetchers import DynamicSession
        from scrapling_scraper import HepsiemlakScraplingScraper

        helper = HepsiemlakScraplingScraper(
            listing_type=TARGET_LISTING_TYPE,
            category=TARGET_CATEGORY,
            selected_cities=[TARGET_CITY],
            selected_districts={},
            use_stealth=False,
            headless=True,
        )

        city_url = helper._get_city_url(TARGET_CITY)
        listing_container = helper.common_selectors.get(
            "listing_container", "li.listing-item:not(.listing-item--promo)"
        )
        listing_results = helper.common_selectors.get("listing_results")

        total_listings = 0
        page_details = []
        all_listings = []

        start_time = time.time()
        with DynamicSession(
            headless=True,
            disable_resources=True,
            timeout=30000,
            network_idle=False,
        ) as session:
            for page_num in range(1, max_pages + 1):
                page_url = _build_page_url(city_url, page_num)
                fetch_kwargs = {"timeout": 30000}
                if listing_results:
                    fetch_kwargs["wait_selector"] = listing_results

                response = session.fetch(page_url, **fetch_kwargs)
                page_count = _count_listing_elements(response, listing_container)
                page_listings = helper.extract_listings_from_page(
                    response,
                    city=TARGET_CITY,
                    page_url=getattr(response, "url", page_url),
                )
                all_listings.extend(page_listings)
                total_listings = len(all_listings)

                page_details.append(
                    {
                        "page": page_num,
                        "detected_listings": page_count,
                        "extracted_listings": len(page_listings),
                        "url": page_url,
                    }
                )

        end_time = time.time()
        duration = end_time - start_time

        print(f"\n✅ Scrapling (dynamic_session) tamamlandi: {duration:.2f}s, {total_listings} ilan")

        return {
            "method": "scrapling_dynamic_session",
            "duration": duration,
            "listings": total_listings,
            "max_pages": max_pages,
            "result": {
                "city_url": city_url,
                "page_details": page_details,
                "listings": all_listings,
            },
        }

    except Exception as e:
        print(f"❌ Scrapling (dynamic_session) testi hatasi: {e}")
        import traceback

        traceback.print_exc()
        return {
            "method": "scrapling_dynamic_session",
            "duration": 0,
            "listings": 0,
            "max_pages": max_pages,
            "error": str(e),
        }


def run_scrapling_spider_test(session_mode: str, max_pages: int = MAX_PAGES):
    """Scrapling Spider API ile benchmark calistir (fetcher/async_dynamic/async_stealth)."""
    session_cfg = {
        "fetcher": {
            "method": "scrapling_spider_fetcher_session",
            "label": "🟪 Scrapling (spider_fetcher_session)",
            "concurrent_requests": 3,
            "download_delay": 0.0,
            "timeout_ms": 30000,
            "retries": 3,
            "retry_delay": 1,
            "max_blocked_retries": 3,
        },
        "dynamic": {
            "method": "scrapling_spider_dynamic_session",
            "label": "🟧 Scrapling (spider_dynamic_session)",
            "concurrent_requests": 2,
            "download_delay": 0.0,
            "timeout_ms": 45000,
            "retries": 4,
            "retry_delay": 2,
            "max_blocked_retries": 4,
        },
        "stealth": {
            "method": "scrapling_spider_stealth_session",
            "label": "🟥 Scrapling (spider_stealth_session)",
            "concurrent_requests": 1,
            "download_delay": 0.4,
            "timeout_ms": 60000,
            "retries": 5,
            "retry_delay": 2,
            "max_blocked_retries": 5,
        },
    }

    if session_mode not in session_cfg:
        raise ValueError(f"Unsupported spider session mode: {session_mode}")

    method_name = session_cfg[session_mode]["method"]
    label = session_cfg[session_mode]["label"]
    mode_settings = session_cfg[session_mode]
    print(f"\n{label} testi basliyor... (max_pages={max_pages})")

    try:
        from scrapling.fetchers import AsyncDynamicSession, AsyncStealthySession, FetcherSession
        from scrapling.spiders import Response, Spider
        from scrapling_scraper import HepsiemlakScraplingScraper

        # Keep spider output concise but preserve warnings/errors.
        logging.getLogger("scrapling").setLevel(logging.WARNING)
        logging.getLogger("scrapling.spiders").setLevel(logging.WARNING)

        helper = HepsiemlakScraplingScraper(
            listing_type=TARGET_LISTING_TYPE,
            category=TARGET_CATEGORY,
            selected_cities=[TARGET_CITY],
            selected_districts={},
            use_stealth=False,
            headless=True,
        )

        city_url = helper._get_city_url(TARGET_CITY)
        listing_container = helper.common_selectors.get(
            "listing_container", "li.listing-item:not(.listing-item--promo)"
        )
        link_selector = helper.common_selectors.get("link", "a.card-link")
        listing_results = helper.common_selectors.get("listing_results")
        spider_errors = []
        visited_pages = set()
        page_listing_counts = {}

        class HepsiemlakSpiderBenchmark(Spider):
            name = f"hepsiemlak_spider_benchmark_{session_mode}"
            start_urls = [city_url]
            allowed_domains = {"hepsiemlak.com"}
            concurrent_requests = mode_settings["concurrent_requests"]
            download_delay = mode_settings["download_delay"]
            max_blocked_retries = mode_settings["max_blocked_retries"]
            logging_level = logging.WARNING

            def configure_sessions(self, manager):
                if session_mode == "fetcher":
                    manager.add(
                        "default",
                        FetcherSession(
                            stealthy_headers=True,
                            follow_redirects=True,
                            timeout=mode_settings["timeout_ms"] // 1000,
                            retries=mode_settings["retries"],
                            retry_delay=mode_settings["retry_delay"],
                        ),
                        default=True,
                    )
                elif session_mode == "dynamic":
                    manager.add(
                        "default",
                        AsyncDynamicSession(
                            headless=True,
                            disable_resources=True,
                            timeout=mode_settings["timeout_ms"],
                            retries=mode_settings["retries"],
                            retry_delay=mode_settings["retry_delay"],
                            network_idle=False,
                        ),
                        default=True,
                    )
                else:
                    manager.add(
                        "default",
                        AsyncStealthySession(
                            headless=True,
                            disable_resources=True,
                            timeout=mode_settings["timeout_ms"],
                            retries=mode_settings["retries"],
                            retry_delay=mode_settings["retry_delay"],
                            network_idle=False,
                        ),
                        default=True,
                    )

            async def on_error(self, request, error):
                spider_errors.append(
                    {
                        "url": getattr(request, "url", ""),
                        "sid": getattr(request, "sid", ""),
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
                logger.warning(f"{label} request error: {request.url} -> {type(error).__name__}: {error}")

            async def parse(self, response: Response):
                current_page = _get_page_number(response.url)
                visited_pages.add(current_page)

                listings = response.css(listing_container)
                page_listing_counts[current_page] = len(listings)
                for listing in listings:
                    href = ""
                    try:
                        links = listing.css(link_selector)
                        if links:
                            href = str(links[0].attrib.get("href", "")).strip()
                    except Exception:
                        href = ""
                    data = {}
                    try:
                        data = helper._extract_from_scrapling_element(listing, page_url=response.url)
                    except Exception:
                        data = {}

                    if not isinstance(data, dict):
                        data = {}
                    if not data.get("ilan_linki"):
                        data["ilan_linki"] = href
                    if not data.get("il") or data.get("il") == "Belirtilmemiş":
                        data["il"] = TARGET_CITY
                    data["page"] = current_page
                    data["scraping_method"] = "scrapling_spider"
                    yield data

                if current_page < max_pages:
                    next_url = _build_page_url(city_url, current_page + 1)
                    follow_kwargs = {"callback": self.parse}
                    # wait_selector is browser-session specific; FetcherSession does not accept it.
                    if session_mode != "fetcher" and listing_results:
                        follow_kwargs["wait_selector"] = listing_results
                    yield response.follow(next_url, **follow_kwargs)

        start_time = time.time()
        crawl_result = HepsiemlakSpiderBenchmark().start()
        end_time = time.time()

        method_items = [item for item in crawl_result.items if isinstance(item, dict)]

        duration = end_time - start_time
        total_listings = len(method_items)
        visited_pages_sorted = sorted(visited_pages)
        missing_pages = [page for page in range(1, max_pages + 1) if page not in visited_pages]

        print(f"\n✅ {label} tamamlandi: {duration:.2f}s, {total_listings} ilan")
        print(f"   📄 Ziyaret edilen sayfalar: {visited_pages_sorted}")
        if missing_pages:
            print(f"   ⚠️ Eksik sayfalar: {missing_pages}")
        if spider_errors:
            print(f"   ⚠️ Toplam request hatasi: {len(spider_errors)}")
        if page_listing_counts:
            ordered_counts = {p: page_listing_counts[p] for p in sorted(page_listing_counts.keys())}
            print(f"   📊 Sayfa bazli ilan: {ordered_counts}")

        return {
            "method": method_name,
            "duration": duration,
            "listings": total_listings,
            "max_pages": max_pages,
            "result": {
                "requests_count": crawl_result.stats.requests_count,
                "items_scraped": crawl_result.stats.items_scraped,
                "elapsed_seconds": crawl_result.stats.elapsed_seconds,
                "requests_per_second": crawl_result.stats.requests_per_second,
                "completed": crawl_result.completed,
                "listings": method_items,
                "visited_pages": visited_pages_sorted,
                "missing_pages": missing_pages,
                "page_listing_counts": {str(k): page_listing_counts[k] for k in sorted(page_listing_counts.keys())},
                "request_errors_count": len(spider_errors),
                "request_errors": spider_errors[:20],
            },
        }

    except Exception as e:
        print(f"❌ {label} testi hatasi: {e}")
        import traceback

        traceback.print_exc()
        return {
            "method": method_name,
            "duration": 0,
            "listings": 0,
            "max_pages": max_pages,
            "error": str(e),
        }


def compare_results(results):
    """Tum yontem sonuclarini karsilastir."""
    print("\n" + "=" * 70)
    print("KARSILASTIRMA SONUCLARI")
    print("=" * 70)

    labels = {
        "selenium": "🔵 Selenium",
        "scrapling_stealth_session": "🟢 Scrapling (StealthSession)",
        "scrapling_fetcher_session": "🟩 Scrapling (FetcherSession)",
        "scrapling_dynamic_session": "🟨 Scrapling (DynamicSession)",
        "scrapling_spider_fetcher_session": "🟪 Scrapling (Spider+FetcherSession)",
        "scrapling_spider_dynamic_session": "🟧 Scrapling (Spider+AsyncDynamicSession)",
        "scrapling_spider_stealth_session": "🟥 Scrapling (Spider+AsyncStealthySession)",
    }

    for result in results:
        label = labels.get(result["method"], result["method"])
        print(f"\n{label}:")
        print(f"   Sure: {result['duration']:.2f} saniye")
        print(f"   Ilan: {result['listings']}")

    successful_results = [r for r in results if r["duration"] > 0]

    print("\n⚡ HIZ KARSILASTIRMASI:")
    winner_method = None
    ranking = []
    if successful_results:
        ranked = sorted(successful_results, key=lambda r: r["duration"])
        ranking = [r["method"] for r in ranked]
        winner_method = ranked[0]["method"]
        print(f"   ⭐ En hizli: {labels.get(winner_method, winner_method)} ({ranked[0]['duration']:.2f}s)")

        selenium_result = next((r for r in successful_results if r["method"] == "selenium"), None)
        if selenium_result and selenium_result["duration"] > 0:
            for result in successful_results:
                if result["method"] == "selenium":
                    continue
                ratio = result["duration"] / selenium_result["duration"]
                method_label = labels.get(result["method"], result["method"])
                if ratio >= 1:
                    print(f"   {method_label}, Selenium'dan {ratio:.2f}x daha yavas")
                else:
                    print(f"   {method_label}, Selenium'dan {1/ratio:.2f}x daha hizli")
    else:
        print("   Basarili sure olusmadi, hiz karsilastirmasi yapilamadi.")

    print("\n📊 KAYNAK KULLANIMI:")
    print("   Selenium: Tarayici tabanli, parse islemi mature")
    print("   StealthSession: En yuksek anti-bot, genelde en yavas")
    print("   FetcherSession: HTTP tabanli, genelde en hizli Scrapling modu")
    print("   DynamicSession: Browser tabanli orta seviye gizlilik")
    print("   Spider+FetcherSession: Crawl framework + HTTP session")
    print("   Spider+AsyncDynamicSession: Crawl framework + async dynamic browser session")
    print("   Spider+AsyncStealthySession: Crawl framework + async stealth browser session")

    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "max_pages": MAX_PAGES,
            "city": TARGET_CITY,
            "category": TARGET_CATEGORY,
            "listing_type": TARGET_LISTING_TYPE,
        },
        "methods": {r["method"]: r for r in results},
        "comparison": {
            "winner": winner_method,
            "ranking_by_duration": ranking,
        },
    }

    output_dir = Path("Outputs/Comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "simple_comparison_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Sonuclar kaydedildi: {output_path}")
    _export_excel_reports(results, output_dir)
    print("\n✅ Karsilastirma tamamlandi!")


def main():
    """Ana fonksiyon."""
    print("=" * 70)
    print("HepsiEmlak Scraping Karsilastirmasi: Selenium vs Scrapling")
    print("=" * 70)
    print(
        f"\nTest konfigurasyonu: max_pages={MAX_PAGES}, sehir={TARGET_CITY}, kategori={TARGET_CATEGORY}, "
        f"ilan_tipi={TARGET_LISTING_TYPE}"
    )

    results = []

    results.append(run_selenium_test(max_pages=MAX_PAGES))

    print(f"\n⏳ {WAIT_BETWEEN_TESTS_SECONDS} saniye bekleniyor...")
    time.sleep(WAIT_BETWEEN_TESTS_SECONDS)

    # Geçici olarak kapalı: StealthSession benchmark'ı.
    if ENABLE_STEALTH_SESSION_BENCHMARK:
        results.append(run_scrapling_session_test(use_stealth=True, max_pages=MAX_PAGES))
        print(f"\n⏳ {WAIT_BETWEEN_TESTS_SECONDS} saniye bekleniyor...")
        time.sleep(WAIT_BETWEEN_TESTS_SECONDS)
    else:
        print("\n⏭️ Scrapling (StealthSession) testi geçici olarak atlandi.")

    results.append(run_scrapling_session_test(use_stealth=False, max_pages=MAX_PAGES))

    print(f"\n⏳ {WAIT_BETWEEN_TESTS_SECONDS} saniye bekleniyor...")
    time.sleep(WAIT_BETWEEN_TESTS_SECONDS)

    results.append(run_scrapling_dynamic_session_test(max_pages=MAX_PAGES))

    print(f"\n⏳ {WAIT_BETWEEN_TESTS_SECONDS} saniye bekleniyor...")
    time.sleep(WAIT_BETWEEN_TESTS_SECONDS)

    results.append(run_scrapling_spider_test(session_mode="fetcher", max_pages=MAX_PAGES))

    print(f"\n⏳ {WAIT_BETWEEN_TESTS_SECONDS} saniye bekleniyor...")
    time.sleep(WAIT_BETWEEN_TESTS_SECONDS)

    results.append(run_scrapling_spider_test(session_mode="dynamic", max_pages=MAX_PAGES))

    print(f"\n⏳ {WAIT_BETWEEN_TESTS_SECONDS} saniye bekleniyor...")
    time.sleep(WAIT_BETWEEN_TESTS_SECONDS)

    results.append(run_scrapling_spider_test(session_mode="stealth", max_pages=MAX_PAGES))

    compare_results(results)


if __name__ == "__main__":
    main()
