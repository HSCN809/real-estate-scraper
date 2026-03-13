# -*- coding: utf-8 -*-
"""HepsiEmlak Scrapling tabanli scraper."""

import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from scrapling.fetchers import (
    AsyncDynamicSession,
    AsyncStealthySession,
    DynamicSession,
    FetcherSession,
    StealthySession,
)
from scrapling.parser import Selector
from scrapling.spiders import Response, Spider

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.config import get_hepsiemlak_config
from core.selectors import get_common_selectors, get_selectors
from utils.data_exporter import DataExporter
from utils.logger import TaskLogLayout, get_logger

from .main import save_listings_to_db

logger = get_logger(__name__)
task_log = TaskLogLayout(logger)

SUPPORTED_SCRAPLING_METHODS = (
    "scrapling_stealth_session",
    "scrapling_fetcher_session",
    "scrapling_dynamic_session",
    "scrapling_spider_fetcher_session",
    "scrapling_spider_dynamic_session",
    "scrapling_spider_stealth_session",
)

SESSION_METHODS = {
    "scrapling_stealth_session",
    "scrapling_fetcher_session",
    "scrapling_dynamic_session",
}

SPIDER_METHOD_TO_SESSION = {
    "scrapling_spider_fetcher_session": "fetcher",
    "scrapling_spider_dynamic_session": "dynamic",
    "scrapling_spider_stealth_session": "stealth",
}

SPIDER_SESSION_CONFIG = {
    "fetcher": {"concurrent_requests": 3, "download_delay": 0.0, "timeout_ms": 30000, "retries": 3, "retry_delay": 1, "max_blocked_retries": 3},
    "dynamic": {"concurrent_requests": 2, "download_delay": 0.0, "timeout_ms": 45000, "retries": 4, "retry_delay": 2, "max_blocked_retries": 4},
    "stealth": {"concurrent_requests": 1, "download_delay": 0.4, "timeout_ms": 60000, "retries": 5, "retry_delay": 2, "max_blocked_retries": 5},
}


class HepsiemlakScraplingScraper:
    """HepsiEmlak platformu icin Scrapling tabanli scraper."""

    def __init__(
        self,
        listing_type: str = "satilik",
        category: str = "konut",
        subtype_path: Optional[str] = None,
        selected_cities: Optional[List[str]] = None,
        selected_districts: Optional[Dict[str, List[str]]] = None,
        use_stealth: bool = True,
        headless: bool = True,
        scraping_method: Optional[str] = None,
    ):
        base_config = get_hepsiemlak_config()
        category_path = subtype_path or base_config.categories.get(listing_type, {}).get(category, "")

        self.base_config = base_config
        self.base_url = base_config.base_url + category_path
        self.listing_type = listing_type
        self.category = category
        self.subtype_path = subtype_path
        self.selected_cities = selected_cities or []
        self.selected_districts = selected_districts or {}
        self.headless = headless
        self.request_timeout_ms = 45000
        self.scraping_method = self._resolve_scraping_method(scraping_method, use_stealth)

        self.selectors = get_selectors("hepsiemlak", category)
        self.common_selectors = get_common_selectors("hepsiemlak")

        self.session_context = None
        self.session = None
        self._stop_checker = None

        self.db = None
        self.scrape_session_id = None
        self.total_scraped_count = 0
        self.new_listings_count = 0
        self.duplicate_count = 0
        self.total_new_listings = 0
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_pages": 0,
            "total_listings": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration": 0,
        }

        self.exporter = DataExporter(
            output_dir="Outputs/HepsiEmlak Output/Scrapling",
            listing_type=listing_type,
            category=category,
            subtype=self.subtype_name,
        )

    @staticmethod
    def _resolve_scraping_method(scraping_method: Optional[str], use_stealth: bool) -> str:
        if scraping_method is None:
            return "scrapling_stealth_session" if use_stealth else "scrapling_fetcher_session"
        if scraping_method not in SUPPORTED_SCRAPLING_METHODS:
            raise ValueError(f"Unsupported scraping_method: {scraping_method}")
        return scraping_method

    @property
    def subtype_name(self) -> Optional[str]:
        if self.subtype_path:
            parts = self.subtype_path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[-1].replace("-", "_")
        return None

    def get_file_prefix(self) -> str:
        parts = ["hepsiemlak", self.listing_type, self.category]
        if self.subtype_name:
            parts.append(self.subtype_name)
        parts.append(self.scraping_method)
        return "_".join(parts)

    def _normalize_text(self, text: str) -> str:
        import unicodedata

        text = unicodedata.normalize("NFC", text)
        for tr_char, en_char in {"I": "i", "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c", "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}.items():
            text = text.replace(tr_char, en_char)
        return text.lower().replace(" ", "-")

    def _get_category_or_subtype_slug(self) -> str:
        if self.subtype_path:
            parts = self.subtype_path.strip("/").split("/")
            return parts[-1] if len(parts) >= 2 else ""
        category_path = self.base_config.categories.get(self.listing_type, {}).get(self.category, "")
        parts = category_path.strip("/").split("/") if category_path else []
        return parts[-1] if len(parts) >= 2 else ""

    def _build_location_url(self, location_slug: str) -> str:
        suffix = self._get_category_or_subtype_slug()
        base_location_url = f"https://www.hepsiemlak.com/{location_slug}-{self.listing_type}"
        return f"{base_location_url}/{suffix}" if suffix else base_location_url

    def _get_city_url(self, city: str) -> str:
        return self._build_location_url(self._normalize_text(city))

    def _get_district_url(self, district: str) -> str:
        return self._build_location_url(self._normalize_text(district))

    @staticmethod
    def _build_page_url(base_url: str, page_num: int) -> str:
        if page_num <= 1:
            return base_url
        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page_num)]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    @staticmethod
    def _get_page_number(url: str) -> int:
        try:
            page_values = parse_qs(urlparse(url).query).get("page")
            if page_values and page_values[0].isdigit():
                return int(page_values[0])
        except Exception:
            pass
        return 1

    def _is_stop_requested(self) -> bool:
        if self._stop_checker and self._stop_checker():
            return True
        try:
            from api.status import task_status

            return task_status.is_stop_requested()
        except Exception:
            return False

    def _raise_if_stop_requested(self, progress_callback=None, message: str = "Durdurma istegi alindi.") -> bool:
        if not self._is_stop_requested():
            return False
        task_log.line(f"⚠️ {message}", level="warning")
        if progress_callback:
            progress_callback(message, progress=0)
        return True

    def _create_session(self):
        if self.scraping_method not in SESSION_METHODS:
            return None

        listing_results = self.common_selectors.get("listing_results")
        task_log.line(f"Creating Scrapling session via {self.scraping_method} (headless={self.headless})")
        if self.scraping_method == "scrapling_stealth_session":
            self.session_context = StealthySession(
                headless=self.headless,
                solve_cloudflare=False,
                google_search=False,
                timeout=self.request_timeout_ms,
                network_idle=True,
                wait_selector=listing_results,
            )
        elif self.scraping_method == "scrapling_dynamic_session":
            self.session_context = DynamicSession(
                headless=self.headless,
                disable_resources=True,
                timeout=self.request_timeout_ms,
                network_idle=False,
            )
        else:
            self.session_context = FetcherSession(
                stealthy_headers=True,
                follow_redirects=True,
                timeout=30,
                retries=3,
                retry_delay=1,
            )

        self.session = self.session_context.__enter__() if hasattr(self.session_context, "__enter__") else self.session_context
        task_log.line(f"Scrapling session ready via {self.scraping_method}")
        return self.session

    def _close_session(self):
        if self.session_context and hasattr(self.session_context, "__exit__"):
            self.session_context.__exit__(None, None, None)
        elif self.session and hasattr(self.session, "__exit__"):
            self.session.__exit__(None, None, None)
        self.session_context = None
        self.session = None

    def fetch_page(self, url: str) -> Optional[Selector]:
        try:
            if self.session is None:
                raise RuntimeError("Session is not initialized")

            start_time = time.time()
            if self.scraping_method == "scrapling_fetcher_session":
                response = self.session.get(url)
            else:
                fetch_kwargs: Dict[str, Any] = {"timeout": self.request_timeout_ms}
                if self.scraping_method == "scrapling_stealth_session":
                    fetch_kwargs["network_idle"] = True
                wait_selector = self.common_selectors.get("listing_results")
                if wait_selector:
                    fetch_kwargs["wait_selector"] = wait_selector
                response = self.session.fetch(url, **fetch_kwargs)

            if not response:
                self.metrics["failed_requests"] += 1
                return None

            status = getattr(response, "status", 200)
            body = getattr(response, "body", b"")
            if (isinstance(status, int) and status >= 400) or not body or len(body) <= 100:
                self.metrics["failed_requests"] += 1
                return None

            self.metrics["successful_requests"] += 1
            task_log.line(f"Fetched {url} in {time.time() - start_time:.2f}s via {self.scraping_method}")
            return response
        except Exception as exc:
            self.metrics["failed_requests"] += 1
            task_log.line(f"Error fetching {url}: {exc}", level="error")
            return None

    def get_total_pages(self, selector: Selector) -> int:
        try:
            count_elements = selector.css("span.applied-filters__count")
            if count_elements:
                count_text_clean = str(count_elements[0].text).strip().replace(".", "")
                match = re.search(r"(\d+)", count_text_clean)
                if match and int(match.group(1)) <= 24:
                    return 1
            pagination_links = selector.css("ul.he-pagination__links a, ul.he-pagination a")
            max_page = 1
            for link in pagination_links:
                text = str(link.text).strip()
                if text.isdigit():
                    max_page = max(max_page, int(text))
            return max_page
        except Exception as exc:
            task_log.line(f"Error detecting pagination: {exc}", level="warning")
            return 1

    def _extract_text(self, element: Selector, css_selector: str, default: str = "Belirtilmemis") -> str:
        try:
            elements = element.css(css_selector) if css_selector else []
            value = str(elements[0].text).strip() if elements else ""
            return value or default
        except Exception:
            return default

    def _extract_attribute(self, element: Selector, css_selector: str, attribute: str, default: str = "Belirtilmemis") -> str:
        try:
            elements = element.css(css_selector) if css_selector else []
            value = str(elements[0].attrib.get(attribute, "")).strip() if elements else ""
            return value or default
        except Exception:
            return default

    def _extract_common_data(self, element: Selector, page_url: str = "") -> Dict[str, Any]:
        listing_link = self._extract_attribute(element, self.common_selectors.get("link", "a.card-link"), "href")
        if listing_link != "Belirtilmemis" and page_url:
            listing_link = urljoin(page_url, listing_link)
        location_text = ""
        for loc_selector in ["span.list-view-location address", "span.list-view-location", ".list-view-location address", ".list-view-location", "address"]:
            location_text = self._extract_text(element, loc_selector, default="")
            if location_text and "/" in location_text:
                break
        location_parts = [part.strip() for part in location_text.split("/") if part.strip()]
        return {
            "fiyat": self._extract_text(element, self.common_selectors.get("price", "span.list-view-price")),
            "baslik": self._extract_text(element, self.common_selectors.get("title", "h3")),
            "il": location_parts[0] if len(location_parts) > 0 else "Belirtilmemis",
            "ilce": location_parts[1] if len(location_parts) > 1 else "Belirtilmemis",
            "mahalle": location_parts[2] if len(location_parts) > 2 else "Belirtilmemis",
            "ilan_linki": listing_link,
            "ilan_tarihi": self._extract_text(element, self.common_selectors.get("date", "span.list-view-date")),
            "emlak_ofisi": self._extract_text(element, self.common_selectors.get("firm", "p.listing-card--owner-info__firm-name")),
        }

    def _extract_category_specific_data(self, element: Selector) -> Dict[str, Any]:
        if self.category == "konut":
            return {"oda_sayisi": self._extract_text(element, self.selectors.get("room_count", "span.houseRoomCount")), "metrekare": self._extract_text(element, self.selectors.get("size", "span.list-view-size")), "bina_yasi": self._extract_text(element, self.selectors.get("building_age", "span.buildingAge")), "kat": self._extract_text(element, self.selectors.get("floor", "span.floortype"))}
        if self.category == "arsa":
            data = {"arsa_metrekare": "Belirtilmemis", "metrekare_fiyat": "Belirtilmemis"}
            for size_element in element.css(self.selectors.get("size", "span.celly.squareMeter.list-view-size")):
                size_text = str(size_element.text).strip()
                normalized = size_text.lower().replace(" ", "")
                if ("tl/m²" in normalized or "tl/m2" in normalized) and data["metrekare_fiyat"] == "Belirtilmemis":
                    data["metrekare_fiyat"] = size_text
                elif ("m²" in normalized or "m2" in normalized) and data["arsa_metrekare"] == "Belirtilmemis":
                    data["arsa_metrekare"] = size_text
            return data
        if self.category == "isyeri":
            return {"metrekare": self._extract_text(element, self.selectors.get("size", "span.celly.squareMeter.list-view-size"))}
        if self.category == "devremulk":
            return {"oda_sayisi": self._extract_text(element, self.selectors.get("room_count", "span.houseRoomCount")), "metrekare": self._extract_text(element, self.selectors.get("size", "span.celly.squareMeter.list-view-size")), "bina_yasi": self._extract_text(element, self.selectors.get("building_age", "span.buildingAge")), "kat": self._extract_text(element, self.selectors.get("floor", "span.floortype"))}
        if self.category == "turistik_isletme":
            return {"oda_sayisi": self._extract_text(element, self.selectors.get("room_count", "span.workRoomCount")), "otel_tipi": self._extract_text(element, self.selectors.get("star_count", "span.startCount"))}
        return {}

    def _extract_from_scrapling_element(self, element: Selector, page_url: str = "") -> Dict[str, Any]:
        data = self._extract_common_data(element, page_url=page_url)
        data.update(self._extract_category_specific_data(element))
        return data

    def extract_listings_from_page(self, selector: Selector, city: Optional[str] = None, district: Optional[str] = None, page_url: str = "") -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        try:
            listing_elements = selector.css(self.common_selectors.get("listing_container", "li.listing-item:not(.listing-item--promo)"))
            source_url = page_url or getattr(selector, "url", "")
            for element in listing_elements:
                data = self._extract_from_scrapling_element(element, page_url=source_url)
                if not data:
                    continue
                if city and (not data.get("il") or data.get("il") == "Belirtilmemis"):
                    data["il"] = city
                if district and (not data.get("ilce") or data.get("ilce") == "Belirtilmemis"):
                    data["ilce"] = district
                data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["scraping_method"] = self.scraping_method
                listings.append(data)
        except Exception as exc:
            task_log.line(f"Error extracting listings from page: {exc}", level="error")
        return listings

    def _persist_listings(self, listings: List[Dict[str, Any]]) -> Tuple[int, int, int]:
        if not listings:
            return 0, 0, 0
        self.total_scraped_count += len(listings)
        if not self.db:
            return len(listings), 0, 0
        new_count, updated_count, unchanged_count = save_listings_to_db(
            self.db,
            listings,
            platform="hepsiemlak",
            kategori=self.category,
            ilan_tipi=self.listing_type,
            alt_kategori=self.subtype_name,
            scrape_session_id=self.scrape_session_id,
            log_db_save=False,
        )
        self.new_listings_count += new_count
        self.duplicate_count += unchanged_count
        self.total_new_listings += new_count
        return new_count, updated_count, unchanged_count

    def _report_page_persist_result(
        self,
        page_num: int,
        extracted_count: int,
        new_count: int,
        updated_count: int,
        unchanged_count: int,
        location_name: str,
    ) -> None:
        task_log.line(f"   ✅ Sayfa {page_num}: {extracted_count} ilan çıkarıldı")
        task_log.line(f"   💾 Sayfa {page_num}: {new_count} yeni, {updated_count} güncellendi, {unchanged_count} değişmedi")

    def _log_location_start(self, location_name: str, location_url: str) -> None:
        task_log.section(
            f"📍 Taranıyor: {location_name}",
            f"🌐 {location_url}",
            f"🕸️ Yöntem: {self.scraping_method}",
        )

    def _log_location_plan(self, location_name: str, pages_to_scrape: int) -> None:
        task_log.line(f"{location_name}: scraping {pages_to_scrape} pages via {self.scraping_method}")
        task_log.line(f"📄 {pages_to_scrape} sayfa taranacak")

    def _make_city_progress_callback(self, progress_callback, current_city_idx: int, num_cities: int, city_name: str):
        def city_progress_callback(msg, current=None, total=None, progress=None):
            city_local_progress = progress if progress is not None else 0
            overall = int(((current_city_idx - 1 + city_local_progress / 100) / num_cities) * 100)
            if progress_callback:
                progress_callback(
                    f"[{current_city_idx}/{num_cities}] {city_name}: {msg}",
                    current=current,
                    total=total,
                    progress=overall,
                )
            else:
                try:
                    from api.status import task_status

                    task_status.update(
                        message=f"[{current_city_idx}/{num_cities}] {city_name}: {msg}",
                        progress=overall,
                        current=current,
                        total=total,
                    )
                except Exception:
                    pass

        return city_progress_callback

    def _resolve_page_limit(self, detected_total_pages: Optional[int], requested_max_pages: Optional[int]) -> int:
        total_pages = max(1, detected_total_pages or 1)
        if requested_max_pages is None or requested_max_pages <= 0:
            return total_pages
        return min(requested_max_pages, total_pages)

    def _fetch_spider_seed_page(self, url: str, session_mode: str) -> Optional[Selector]:
        mode_settings = SPIDER_SESSION_CONFIG[session_mode]
        listing_results = self.common_selectors.get("listing_results")

        try:
            if session_mode == "fetcher":
                with FetcherSession(
                    stealthy_headers=True,
                    follow_redirects=True,
                    timeout=mode_settings["timeout_ms"] // 1000,
                    retries=mode_settings["retries"],
                    retry_delay=mode_settings["retry_delay"],
                ) as session:
                    response = session.get(url)
            elif session_mode == "dynamic":
                with DynamicSession(
                    headless=self.headless,
                    disable_resources=True,
                    timeout=mode_settings["timeout_ms"],
                    retries=mode_settings["retries"],
                    retry_delay=mode_settings["retry_delay"],
                    network_idle=False,
                ) as session:
                    fetch_kwargs: Dict[str, Any] = {"timeout": mode_settings["timeout_ms"]}
                    if listing_results:
                        fetch_kwargs["wait_selector"] = listing_results
                    response = session.fetch(url, **fetch_kwargs)
            else:
                with StealthySession(
                    headless=self.headless,
                    solve_cloudflare=False,
                    google_search=False,
                    timeout=mode_settings["timeout_ms"],
                    network_idle=True,
                    disable_resources=True,
                ) as session:
                    fetch_kwargs: Dict[str, Any] = {"timeout": mode_settings["timeout_ms"]}
                    if listing_results:
                        fetch_kwargs["wait_selector"] = listing_results
                    response = session.fetch(url, **fetch_kwargs)

            if not response:
                return None

            status = getattr(response, "status", 200)
            body = getattr(response, "body", b"")
            if (isinstance(status, int) and status >= 400) or not body or len(body) <= 100:
                return None
            return response
        except Exception as exc:
            task_log.line(f"Could not detect pagination seed for {url}: {exc}", level="warning")
            return None

    def _scrape_location_with_session(
        self,
        location_name: str,
        location_url: str,
        max_pages: Optional[int],
        city: Optional[str] = None,
        district: Optional[str] = None,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        self._log_location_start(location_name, location_url)
        first_page = self.fetch_page(location_url)
        if not first_page:
            task_log.line(f"⚠️ İlk sayfa alınamadı: {location_name}", level="warning")
            return listings

        pages_to_scrape = self._resolve_page_limit(self.get_total_pages(first_page), max_pages)
        self._log_location_plan(location_name, pages_to_scrape)

        for page_num in range(1, pages_to_scrape + 1):
            if self._raise_if_stop_requested(progress_callback, f"{location_name}: durdurma istegi alindi."):
                break

            current_url = self._build_page_url(location_url, page_num)
            task_log.line(f"🔍 [{page_num}/{pages_to_scrape}] {location_name} - Sayfa {page_num} taranıyor...")
            selector = first_page if page_num == 1 else self.fetch_page(current_url)
            if not selector:
                task_log.line(f"   ⚠️ Sayfa {page_num} alınamadı, atlanıyor", level="warning")
                continue

            if progress_callback:
                progress_callback(
                    f"{location_name} - Sayfa {page_num}/{pages_to_scrape}",
                    current=page_num,
                    total=pages_to_scrape,
                    progress=int((page_num / max(1, pages_to_scrape)) * 100),
                )

            page_listings = self.extract_listings_from_page(
                selector,
                city=city,
                district=district,
                page_url=getattr(selector, "url", current_url),
            )
            listings.extend(page_listings)
            new_count, updated_count, unchanged_count = self._persist_listings(page_listings)
            self._report_page_persist_result(
                page_num=page_num,
                extracted_count=len(page_listings),
                new_count=new_count,
                updated_count=updated_count,
                unchanged_count=unchanged_count,
                location_name=location_name,
            )
            self.metrics["total_pages"] += 1

            if page_num < pages_to_scrape:
                time.sleep(random.uniform(1, 3))

        task_log.line(f"✅ {location_name} tamamlandı - {len(listings)} ilan işlendi")
        return listings

    def _scrape_location_with_spider(
        self,
        location_name: str,
        location_url: str,
        max_pages: Optional[int],
        city: Optional[str] = None,
        district: Optional[str] = None,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        session_mode = SPIDER_METHOD_TO_SESSION[self.scraping_method]
        mode_settings = SPIDER_SESSION_CONFIG[session_mode]
        listing_results = self.common_selectors.get("listing_results")
        spider_errors: List[Dict[str, str]] = []
        visited_pages: set[int] = set()
        processed_pages: set[int] = set()
        collected_items: List[Dict[str, Any]] = []
        outer = self

        self._log_location_start(location_name, location_url)
        seed_page = self._fetch_spider_seed_page(location_url, session_mode)
        pages_to_scrape = self._resolve_page_limit(
            self.get_total_pages(seed_page) if seed_page else None,
            max_pages,
        )
        self._log_location_plan(location_name, pages_to_scrape)

        logging.getLogger("scrapling").setLevel(logging.ERROR)
        logging.getLogger("scrapling.spiders").setLevel(logging.ERROR)

        class HepsiemlakSpider(Spider):
            name = f"hepsiemlak_{session_mode}_{outer._normalize_text(location_name)}"
            start_urls = [location_url]
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
                            headless=outer.headless,
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
                            headless=outer.headless,
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
                task_log.line(f"{outer.scraping_method} request error: {request.url} -> {type(error).__name__}: {error}", level="warning")

            async def parse(self, response: Response):
                current_page = outer._get_page_number(response.url)
                visited_pages.add(current_page)

                if outer._raise_if_stop_requested(progress_callback, f"{location_name}: durdurma istegi alindi."):
                    return
                if current_page in processed_pages:
                    return

                task_log.line(f"🔍 [{current_page}/{pages_to_scrape}] {location_name} - Sayfa {current_page} taranıyor...")
                if progress_callback:
                    progress_callback(
                        f"{location_name} - Sayfa {current_page}/{pages_to_scrape}",
                        current=current_page,
                        total=pages_to_scrape,
                        progress=int((current_page / max(1, pages_to_scrape)) * 100),
                    )

                page_listings = outer.extract_listings_from_page(
                    response,
                    city=city,
                    district=district,
                    page_url=response.url,
                )
                for listing in page_listings:
                    listing["page"] = current_page
                    listing["scraping_method"] = outer.scraping_method

                new_count, updated_count, unchanged_count = outer._persist_listings(page_listings)
                outer._report_page_persist_result(
                    page_num=current_page,
                    extracted_count=len(page_listings),
                    new_count=new_count,
                    updated_count=updated_count,
                    unchanged_count=unchanged_count,
                    location_name=location_name,
                )
                processed_pages.add(current_page)
                collected_items.extend(page_listings)

                if current_page < pages_to_scrape and not outer._is_stop_requested():
                    next_url = outer._build_page_url(location_url, current_page + 1)
                    follow_kwargs = {"callback": self.parse}
                    if session_mode != "fetcher" and listing_results:
                        follow_kwargs["wait_selector"] = listing_results
                    yield response.follow(next_url, **follow_kwargs)

        HepsiemlakSpider().start()
        method_items = list(collected_items)
        method_items.sort(key=lambda item: (item.get("page", 1), item.get("ilan_linki", "")))
        self.metrics["total_pages"] += len(visited_pages)
        self.metrics["successful_requests"] += len(visited_pages)
        self.metrics["failed_requests"] += len(spider_errors)

        if not method_items:
            task_log.line(f"⚠️ {location_name} için ilan bulunamadı", level="warning")
        else:
            task_log.line(f"✅ {location_name} tamamlandı - {len(method_items)} ilan işlendi")
        return method_items

    def _scrape_location(
        self,
        location_name: str,
        location_url: str,
        max_pages: Optional[int],
        city: Optional[str] = None,
        district: Optional[str] = None,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        if self.scraping_method in SESSION_METHODS:
            return self._scrape_location_with_session(
                location_name=location_name,
                location_url=location_url,
                max_pages=max_pages,
                city=city,
                district=district,
                progress_callback=progress_callback,
            )
        return self._scrape_location_with_spider(
            location_name=location_name,
            location_url=location_url,
            max_pages=max_pages,
            city=city,
            district=district,
            progress_callback=progress_callback,
        )

    def _export_results(self, all_listings: List[Dict[str, Any]]):
        if not all_listings:
            return

        listings_by_city: Dict[str, List[Dict[str, Any]]] = {}
        for listing in all_listings:
            city_name = str(listing.get("il") or "Belirtilmemis").strip() or "Belirtilmemis"
            listings_by_city.setdefault(city_name, []).append(listing)

        prefix = self.get_file_prefix()
        self.exporter.save_by_city(
            listings_by_city,
            prefix=prefix,
            format="excel",
            city_district_map=self.selected_districts if self.selected_districts else None,
        )

        try:
            import pandas as pd

            csv_path = os.path.join(self.exporter.output_dir, f"{prefix}.csv")
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            pd.DataFrame(all_listings).to_csv(csv_path, index=False, encoding="utf-8-sig")
            task_log.line(f"Saved {len(all_listings)} listings to {csv_path}")
        except Exception as exc:
            task_log.line(f"Could not export CSV for {self.scraping_method}: {exc}", level="warning")

    def _run_scraping(self, max_pages: Optional[int], progress_callback=None, stop_checker=None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        self._stop_checker = stop_checker
        task_log.line(
            f"Starting _run_scraping with method={self.scraping_method}, "
            f"cities={self.selected_cities}, max_pages={max_pages}"
        )
        self.metrics.update(
            {
                "start_time": time.time(),
                "end_time": None,
                "total_pages": 0,
                "total_listings": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_duration": 0,
            }
        )
        self.total_scraped_count = 0
        self.new_listings_count = 0
        self.duplicate_count = 0
        self.total_new_listings = 0

        all_results: Dict[str, Any] = {}
        all_listings: List[Dict[str, Any]] = []
        total_cities = len(self.selected_cities)

        if self.scraping_method in SESSION_METHODS:
            task_log.line(f"Initializing session-backed scraping flow for {self.scraping_method}")
            self._create_session()

        try:
            for city_idx, city in enumerate(self.selected_cities, 1):
                city_callback = self._make_city_progress_callback(progress_callback, city_idx, total_cities, city)
                if self._raise_if_stop_requested(city_callback, f"{city}: durdurma istegi alindi."):
                    break

                if self.selected_districts and city in self.selected_districts:
                    district_results: Dict[str, List[Dict[str, Any]]] = {}
                    districts = self.selected_districts[city]
                    for district_idx, district in enumerate(districts, 1):
                        if self._raise_if_stop_requested(city_callback, f"{district}: durdurma istegi alindi."):
                            break
                        district_listings = self._scrape_location(
                            location_name=f"{district} ({district_idx}/{len(districts)})",
                            location_url=self._get_district_url(district),
                            max_pages=max_pages,
                            city=city,
                            district=district,
                            progress_callback=city_callback,
                        )
                        if district_listings:
                            district_results[district] = district_listings
                            all_listings.extend(district_listings)
                        if district_idx < len(districts):
                            time.sleep(random.uniform(1, 3))
                    if district_results:
                        all_results[city] = district_results
                else:
                    city_listings = self._scrape_location(
                        location_name=city,
                        location_url=self._get_city_url(city),
                        max_pages=max_pages,
                        city=city,
                        progress_callback=city_callback,
                    )
                    if city_listings:
                        all_results[city] = city_listings
                        all_listings.extend(city_listings)

                if city_idx < total_cities:
                    time.sleep(random.uniform(2, 4))

            self.metrics["end_time"] = time.time()
            self.metrics["total_duration"] = self.metrics["end_time"] - self.metrics["start_time"]
            self.metrics["total_listings"] = len(all_listings)
            task_log.line("Skipping automatic CSV/Excel export; results remain available in the database.")
            return all_results, all_listings
        finally:
            self._close_session()

    def start_scraping(self, max_pages_per_city: int = 3, max_pages_per_district: int = 2) -> Dict[str, Any]:
        task_log.line(f"Starting Scrapling-based scraping with method={self.scraping_method}")
        results, listings = self._run_scraping(
            max_pages=max(max_pages_per_city, max_pages_per_district),
            progress_callback=None,
            stop_checker=None,
        )
        return {"results": results, "listings": listings, "metrics": self.metrics, "summary": self.get_summary()}

    def start_scraping_api(self, max_pages: Optional[int] = None, progress_callback=None, stop_checker=None):
        task_log.line(
            f"API: HepsiEmlak {self.listing_type.capitalize()} {self.category.capitalize()} Scraper ({self.scraping_method})",
        )
        task_log.line(
            f"start_scraping_api called with method={self.scraping_method}, "
            f"cities={self.selected_cities}, max_pages={max_pages}"
        )
        if not self.selected_cities:
            task_log.line("No cities provided for API scrape", level="error")
            return {}
        results, listings = self._run_scraping(
            max_pages=max_pages,
            progress_callback=progress_callback,
            stop_checker=stop_checker,
        )
        if results:
            task_log.section(
                "SCRAPLING TARAMA TAMAMLANDI",
                f"Yontem: {self.scraping_method}",
                f"Taranan Sehir Sayisi: {len(results)}",
                f"Toplam Ilan Sayisi: {len(listings)}",
            )
        else:
            task_log.section("HIC ILAN BULUNAMADI", level="warning")
        return results

    def get_summary(self) -> Dict[str, Any]:
        total_requests = self.metrics["successful_requests"] + self.metrics["failed_requests"]
        return {
            "scraping_method": self.scraping_method,
            "total_duration_seconds": round(self.metrics["total_duration"], 2),
            "total_listings": self.metrics["total_listings"],
            "total_pages": self.metrics["total_pages"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": round(self.metrics["successful_requests"] / max(1, total_requests) * 100, 2),
            "listings_per_second": round(self.metrics["total_listings"] / max(1, self.metrics["total_duration"]), 2),
            "pages_per_second": round(self.metrics["total_pages"] / max(1, self.metrics["total_duration"]), 2),
        }

    def print_summary(self):
        summary = self.get_summary()
        task_log.section(
            "SCRAPLING SCRAPER - OZET RAPOR",
            f"Yontem: {summary['scraping_method']}",
            f"Toplam Sure: {summary['total_duration_seconds']} saniye",
            f"Toplam Ilan: {summary['total_listings']}",
            f"Toplam Sayfa: {summary['total_pages']}",
            f"Basarili Istek: {summary['successful_requests']}",
            f"Basarisiz Istek: {summary['failed_requests']}",
            f"Basari Orani: {summary['success_rate']}%",
            f"Saniyede Ilan: {summary['listings_per_second']}",
            f"Saniyede Sayfa: {summary['pages_per_second']}",
        )


def test_scrapling_scraper():
    task_log.line("Scrapling Scraper Testi Basliyor...")
    scraper = HepsiemlakScraplingScraper(
        listing_type="kiralik",
        category="konut",
        selected_cities=["Istanbul"],
        selected_districts={"Istanbul": ["Kadikoy"]},
        scraping_method="scrapling_fetcher_session",
        headless=True,
    )
    try:
        result = scraper.start_scraping(max_pages_per_city=2, max_pages_per_district=1)
        scraper.print_summary()
        task_log.line(f"Toplam {len(result['listings'])} ilan bulundu.")
        return result
    except Exception as exc:
        task_log.line(f"Test hatasi: {exc}", level="error")
        return None


if __name__ == "__main__":
    test_scrapling_scraper()
