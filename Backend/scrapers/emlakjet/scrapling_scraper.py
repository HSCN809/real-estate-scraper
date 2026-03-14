# -*- coding: utf-8 -*-
"""EmlakJet Scrapling tabanli scraper."""

import os
import random
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from scrapling.fetchers import DynamicSession, FetcherSession, StealthySession
from scrapling.parser import Selector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.config import get_emlakjet_config
from core.selectors import get_common_selectors, get_selectors
from scrapers.common.proxy_fetch import ProxyFetchClient
from utils.data_exporter import DataExporter
from utils.logger import TaskLogLayout, get_logger

from .main import EmlakJetScraper
from ..hepsiemlak.main import save_listings_to_db

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

SESSION_METHOD_ALIASES = {
    "scrapling_stealth_session": "scrapling_stealth_session",
    "scrapling_fetcher_session": "scrapling_fetcher_session",
    "scrapling_dynamic_session": "scrapling_dynamic_session",
    "scrapling_spider_fetcher_session": "scrapling_fetcher_session",
    "scrapling_spider_dynamic_session": "scrapling_dynamic_session",
    "scrapling_spider_stealth_session": "scrapling_stealth_session",
}


class EmlakJetScraplingScraper:
    """EmlakJet platformu icin Scrapling tabanli scraper."""

    PAGINATION_LIMIT = 1500

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
        proxy_enabled: bool = False,
        proxy_url: Optional[str] = None,
    ):
        base_config = get_emlakjet_config()
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
        self.proxy_enabled = proxy_enabled
        self.proxy_fetcher = ProxyFetchClient(
            enabled=proxy_enabled,
            proxy_url=proxy_url,
            max_retries=6,
            initial_delay=2.0,
        )

        self.selectors = get_selectors("emlakjet", category)
        self.common_selectors = get_common_selectors("emlakjet")
        parser_class = EmlakJetScraper.CATEGORY_PARSERS.get(category, EmlakJetScraper.CATEGORY_PARSERS["konut"])
        self.parser = parser_class()

        self.session_context = None
        self.session = None
        self._stop_checker = None
        self._max_listings = 0

        self.db = None
        self.scrape_session_id = None
        self.all_listings: List[Dict[str, Any]] = []
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
            output_dir="Outputs/EmlakJet Output/Scrapling",
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
            parts = self.subtype_path.strip("/").split("-")
            if len(parts) >= 2:
                return parts[-1].replace("-", "_")
        return None

    def _effective_session_method(self) -> str:
        return SESSION_METHOD_ALIASES[self.scraping_method]

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text or "")
        ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        replacements = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"})
        return ascii_only.translate(replacements).casefold().strip()

    @staticmethod
    def _build_page_url(base_url: str, page_num: int) -> str:
        if page_num <= 1:
            return base_url
        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        query["sayfa"] = [str(page_num)]
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

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

    def _is_listing_limit_reached(self) -> bool:
        return self._max_listings > 0 and len(self.all_listings) >= self._max_listings

    def _create_session(self):
        if self.proxy_enabled:
            task_log.line(
                f"Proxy mode active ({self.proxy_fetcher.proxy_url}); "
                "Scrapling network sessions are bypassed.",
            )
            self.session_context = None
            self.session = None
            return None

        effective_method = self._effective_session_method()
        wait_selector = self.common_selectors.get("listing_container")
        task_log.line(f"Creating Scrapling session via {self.scraping_method} (effective={effective_method}, headless={self.headless})")

        if effective_method == "scrapling_stealth_session":
            self.session_context = StealthySession(
                headless=self.headless,
                solve_cloudflare=False,
                google_search=False,
                timeout=self.request_timeout_ms,
                network_idle=True,
                wait_selector=wait_selector,
            )
        elif effective_method == "scrapling_dynamic_session":
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
            if self.proxy_enabled:
                start_time = time.time()
                selector = self.proxy_fetcher.fetch_selector(url, task_log=task_log)
                if not selector:
                    self.metrics["failed_requests"] += 1
                    return None
                self.metrics["successful_requests"] += 1
                task_log.line(
                    f"Fetched {url} in {time.time() - start_time:.2f}s via go_proxy_client "
                    f"(method={self.scraping_method})"
                )
                return selector

            if self.session is None:
                raise RuntimeError("Session is not initialized")

            effective_method = self._effective_session_method()
            start_time = time.time()
            if effective_method == "scrapling_fetcher_session":
                response = self.session.get(url)
            else:
                fetch_kwargs: Dict[str, Any] = {"timeout": self.request_timeout_ms}
                if effective_method == "scrapling_stealth_session":
                    fetch_kwargs["network_idle"] = True
                wait_selector = self.common_selectors.get("listing_container")
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

    def _extract_text(self, element: Selector, css_selector: str, default: str = "") -> str:
        try:
            elements = element.css(css_selector) if css_selector else []
            value = str(elements[0].text).strip() if elements else ""
            return value or default
        except Exception:
            return default

    def _extract_attribute(self, element: Selector, css_selector: str, attribute: str, default: str = "") -> str:
        try:
            elements = element.css(css_selector) if css_selector else []
            value = str(elements[0].attrib.get(attribute, "")).strip() if elements else ""
            return value or default
        except Exception:
            return default

    def _extract_common_data(self, element: Selector, page_url: str = "") -> Dict[str, Any]:
        title = self._extract_text(element, self.common_selectors.get("title", "h3.styles_title__aKEGQ"))
        location = self._extract_text(element, self.common_selectors.get("location", "span.styles_location__OwJiQ"))
        price = self._extract_text(element, self.common_selectors.get("price", "span.styles_price__F3pMQ"))
        quick_info = self._extract_text(element, self.common_selectors.get("quick_info", "div.styles_quickinfoWrapper__Vsnk5"))
        image_url = self._extract_attribute(element, self.common_selectors.get("image", "img.styles_imageClass___SLvt"), "src")
        listing_url = str(element.attrib.get("href", "")).strip()
        if listing_url and page_url:
            listing_url = urljoin(page_url, listing_url)

        badges = []
        for badge in element.css(self.common_selectors.get("badge_wrapper", "div.styles_badgewrapper__pS0rt")):
            badge_text = str(badge.text).strip()
            if badge_text:
                badges.append(self._normalize_text(badge_text))

        return {
            "baslik": title,
            "lokasyon": location,
            "fiyat": price,
            "ilan_url": listing_url,
            "resim_url": image_url,
            "one_cikan": any("one cikan" in badge for badge in badges),
            "yeni": any(badge == "yeni" or badge.startswith("yeni ") for badge in badges),
            "_quick_info": quick_info,
        }

    def extract_listings_from_page(
        self,
        selector: Selector,
        page_url: str = "",
        city: Optional[str] = None,
        district: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        try:
            listing_selector = self.common_selectors.get("listing_container", "a.styles_wrapper__587DT")
            for element in selector.css(listing_selector):
                data = self._extract_common_data(element, page_url=page_url or getattr(selector, "url", ""))
                if not all([data.get("baslik"), data.get("lokasyon"), data.get("fiyat")]):
                    continue
                quick_info = data.pop("_quick_info", "")
                data.update(self.parser.parse_category_details(quick_info, data.get("baslik", "")))
                data["tarih"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["scraping_method"] = self.scraping_method
                if city:
                    data["il"] = city
                if district:
                    data["ilce"] = district
                if neighborhood:
                    data["mahalle"] = neighborhood
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
            platform="emlakjet",
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

    def _report_page_persist_result(self, page_num: int, extracted_count: int, new_count: int, updated_count: int, unchanged_count: int, location_name: str) -> None:
        task_log.line(f"   ✅ Sayfa {page_num}: {extracted_count} ilan cikarildi")
        task_log.line(f"   💾 Sayfa {page_num}: {new_count} yeni, {updated_count} guncellendi, {unchanged_count} degismedi")

    def _log_location_start(self, location_name: str, location_url: str) -> None:
        task_log.section(
            f"📍 Taraniyor: {location_name}",
            f"🌐 {location_url}",
            f"🕸️ Yontem: {self.scraping_method}",
        )

    def _log_location_plan(self, location_name: str, pages_to_scrape: int) -> None:
        task_log.line(f"{location_name}: scraping {pages_to_scrape} pages via {self.scraping_method}")
        task_log.line(f"📄 {pages_to_scrape} sayfa taranacak")

    def get_total_pages(self, selector: Selector) -> int:
        try:
            page_numbers: List[int] = []
            for link in selector.css("a[href*='sayfa='], ul.styles_list__zqOeW li a"):
                text = str(link.text).strip()
                if text.isdigit():
                    page_numbers.append(int(text))
                href = str(link.attrib.get("href", "")).strip()
                page_value = parse_qs(urlparse(href).query).get("sayfa")
                if page_value and page_value[0].isdigit():
                    page_numbers.append(int(page_value[0]))

            active_page = self._extract_text(selector, self.common_selectors.get("active_page", "span.styles_selected__hilA_"))
            if active_page.isdigit():
                page_numbers.append(int(active_page))
            return max(page_numbers) if page_numbers else 1
        except Exception as exc:
            task_log.line(f"Error detecting pagination: {exc}", level="warning")
            return 1

    def _parse_listing_count(self, selector: Selector) -> int:
        try:
            for element in selector.css("span.styles_adsCount__A1YW5, span.styles_title__e_y3h"):
                if "bulunamadi" in self._normalize_text(str(element.text)):
                    return 0
            for css_selector in [
                "span.styles_adsCount__A1YW5 strong.styles_strong__cw1jn",
                "strong.styles_strong__cw1jn",
            ]:
                text = self._extract_text(selector, css_selector)
                digits = re.sub(r"[^\d]", "", text)
                if digits.isdigit():
                    return int(digits)
            return 0
        except Exception:
            return 0

    def get_listing_count(self, url: str) -> int:
        selector = self.fetch_page(url)
        return self._parse_listing_count(selector) if selector else 0

    def _clean_location_name(self, text: str) -> str:
        compact = " ".join(str(text).split())
        compact = re.sub(r"\s+\(?[\d\.\,]+\)?$", "", compact).strip()
        compact = re.sub(r"\s+\d[\d\.\,]*\s+ilan.*$", "", compact, flags=re.IGNORECASE).strip()
        return compact

    def get_location_options(self, location_type: str, current_url: str) -> Tuple[List[Dict[str, str]], int]:
        task_log.line(f"Getting {location_type} options via {self.scraping_method}")
        selector = self.fetch_page(current_url)
        if not selector:
            return [], 0

        listing_count = self._parse_listing_count(selector)
        location_options: List[Dict[str, str]] = []
        seen_names = set()

        for link in selector.css(self.common_selectors.get("location_links", "section.styles_section__xzOd3 a.styles_link__7WOOd")):
            location_name = self._clean_location_name(str(link.text).strip())
            location_url = str(link.attrib.get("href", "")).strip()
            if location_url:
                location_url = urljoin(current_url, location_url)
            if not location_name or not location_url:
                continue
            normalized = self._normalize_text(location_name)
            if normalized in seen_names:
                continue
            seen_names.add(normalized)
            location_options.append({"name": location_name, "url": location_url})

        return location_options, listing_count

    def _match_requested_locations(self, options: List[Dict[str, str]], requested: List[str]) -> List[Dict[str, str]]:
        requested_set = {self._normalize_text(name) for name in requested}
        return [option for option in options if self._normalize_text(option["name"]) in requested_set]

    def _trim_page_listings(self, page_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self._max_listings <= 0:
            return page_listings
        remaining = self._max_listings - len(self.all_listings)
        if remaining <= 0:
            return []
        return page_listings[:remaining]

    def _resolve_page_limit(self, detected_total_pages: Optional[int], requested_max_pages: Optional[int]) -> int:
        total_pages = max(1, detected_total_pages or 1)
        if requested_max_pages is None or requested_max_pages <= 0:
            return total_pages
        return min(requested_max_pages, total_pages)

    def _scrape_location(
        self,
        location_name: str,
        location_url: str,
        max_pages: Optional[int],
        city: Optional[str] = None,
        district: Optional[str] = None,
        neighborhood: Optional[str] = None,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        self._log_location_start(location_name, location_url)

        first_page = self.fetch_page(location_url)
        if not first_page:
            task_log.line(f"⚠️ Ilk sayfa alinamadi: {location_name}", level="warning")
            return listings

        pages_to_scrape = self._resolve_page_limit(self.get_total_pages(first_page), max_pages)
        self._log_location_plan(location_name, pages_to_scrape)

        for page_num in range(1, pages_to_scrape + 1):
            if self._raise_if_stop_requested(progress_callback, f"{location_name}: durdurma istegi alindi."):
                break
            if self._is_listing_limit_reached():
                task_log.line(f"🎯 Ilan limitine ulasildi: {len(self.all_listings)} / {self._max_listings}")
                break

            current_url = self._build_page_url(location_url, page_num)
            task_log.line(f"🔍 [{page_num}/{pages_to_scrape}] {location_name} - Sayfa {page_num} taraniyor...")
            selector = first_page if page_num == 1 else self.fetch_page(current_url)
            if not selector:
                task_log.line(f"   ⚠️ Sayfa {page_num} alinamadi, atlaniyor", level="warning")
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
                page_url=getattr(selector, "url", current_url),
                city=city,
                district=district,
                neighborhood=neighborhood,
            )
            page_listings = self._trim_page_listings(page_listings)
            self.all_listings.extend(page_listings)
            listings.extend(page_listings)
            new_count, updated_count, unchanged_count = self._persist_listings(page_listings)
            self._report_page_persist_result(page_num, len(page_listings), new_count, updated_count, unchanged_count, location_name)
            self.metrics["total_pages"] += 1

            if self._is_listing_limit_reached():
                task_log.line(f"🎯 Ilan limitine ulasildi: {len(self.all_listings)} / {self._max_listings}")
                break

            if page_num < pages_to_scrape:
                time.sleep(random.uniform(1, 3))

        if listings:
            task_log.line(f"✅ {location_name} tamamlandi - {len(listings)} ilan islendi")
        else:
            task_log.line(f"⚠️ {location_name} icin ilan bulunamadi", level="warning")
        return listings

    def _scrape_target(
        self,
        target: Dict[str, str],
        max_pages: Optional[int],
        city: Optional[str] = None,
        district: Optional[str] = None,
        neighborhood: Optional[str] = None,
        progress_callback=None,
    ) -> Tuple[bool, int]:
        before_new = self.total_new_listings
        listings = self._scrape_location(
            location_name=target["label"],
            location_url=target["url"],
            max_pages=max_pages,
            city=city,
            district=district,
            neighborhood=neighborhood,
            progress_callback=progress_callback,
        )
        return len(listings) == 0, self.total_new_listings - before_new

    def _make_progress_callback(self, progress_callback, current_idx: int, total_count: int, name: str):
        def callback(msg, current=0, total=0, progress=0):
            overall = int(((current_idx - 1 + (progress or 0) / 100) / max(1, total_count)) * 100)
            if progress_callback:
                progress_callback(f"[{current_idx}/{total_count}] {name}: {msg}", current=current, total=total, progress=overall)
        return callback

    def start_scraping_api(
        self,
        cities: Optional[List[str]] = None,
        districts: Optional[Dict[str, List[str]]] = None,
        max_listings: int = 0,
        max_pages: Optional[int] = None,
        progress_callback=None,
        stop_checker=None,
    ):
        self.selected_cities = cities or self.selected_cities
        self.selected_districts = districts or self.selected_districts
        self._stop_checker = stop_checker
        self._max_listings = max_listings or 0
        self.all_listings = []
        self.total_scraped_count = 0
        self.new_listings_count = 0
        self.duplicate_count = 0
        self.total_new_listings = 0
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

        task_log.line(f"🚀 API: EmlakJet {self.listing_type.capitalize()} {self.category.capitalize()} Scrapling Scraper baslatiliyor")
        task_log.line(f"🕸️ Yontem: {self.scraping_method}")

        if not self.selected_cities:
            task_log.line("API taramasi icin sehir belirtilmedi", level="error")
            return {}

        self._create_session()
        scrape_stats: Dict[str, Dict[str, int]] = {}
        page_limit = max_pages
        stopped = False

        try:
            task_log.line("Il listesi aliniyor...")
            all_provinces, _ = self.get_location_options("Iller", self.base_url)
            provinces = self._match_requested_locations(all_provinces, self.selected_cities)
            if not provinces:
                task_log.line(f"Sehirler icin eslesen il bulunamadi: {self.selected_cities}", level="error")
                return {}

            for prov_idx, province in enumerate(provinces, 1):
                province_name = province["name"]
                province_callback = self._make_progress_callback(progress_callback, prov_idx, len(provinces), province_name)

                if self._raise_if_stop_requested(province_callback, f"{province_name}: durdurma istegi alindi."):
                    stopped = True
                    break
                if self._is_listing_limit_reached():
                    stopped = True
                    break

                province_count = self.get_listing_count(province["url"])
                task_log.section(f"🏙️ IL {prov_idx}/{len(provinces)}: {province_name} (Toplam Ilan: {province_count})")

                if province_count == 0:
                    task_log.line(f"⏭️ {province_name} -> 0 ilan, il atlaniyor.")
                    continue

                if province_count <= self.PAGINATION_LIMIT:
                    target = {"url": province["url"], "label": province_name, "type": "il"}
                    should_skip, new_count = self._scrape_target(target, page_limit, city=province_name, progress_callback=province_callback)
                    if not should_skip:
                        scrape_stats[province_name] = {"(il seviyesi)": new_count}
                    continue

                district_list, _ = self.get_location_options("Ilceler", province["url"])
                if not district_list:
                    task_log.line(f"⏭️ {province_name} icin ilce bulunamadi, atlaniyor.")
                    continue

                requested_districts = None
                for city_name, district_names in self.selected_districts.items():
                    if self._normalize_text(city_name) == self._normalize_text(province_name):
                        requested_districts = district_names
                        break

                if requested_districts:
                    district_list = self._match_requested_locations(district_list, requested_districts)
                    if not district_list:
                        task_log.line(f"⏭️ {province_name} icin eslesen ilce bulunamadi.")
                        continue

                for district_item in district_list:
                    district_name = district_item["name"]
                    if self._raise_if_stop_requested(province_callback, f"{district_name}: durdurma istegi alindi."):
                        stopped = True
                        break
                    if self._is_listing_limit_reached():
                        stopped = True
                        break

                    district_count = self.get_listing_count(district_item["url"])
                    if district_count == 0:
                        continue

                    if district_count <= self.PAGINATION_LIMIT:
                        target = {"url": district_item["url"], "label": f"{province_name} / {district_name}", "type": "ilce"}
                        should_skip, new_count = self._scrape_target(
                            target,
                            page_limit,
                            city=province_name,
                            district=district_name,
                            progress_callback=province_callback,
                        )
                        if not should_skip:
                            scrape_stats.setdefault(province_name, {})[district_name] = new_count
                        continue

                    neighborhoods, _ = self.get_location_options("Mahalleler", district_item["url"])
                    if not neighborhoods:
                        target = {"url": district_item["url"], "label": f"{province_name} / {district_name}", "type": "ilce"}
                        should_skip, new_count = self._scrape_target(
                            target,
                            page_limit,
                            city=province_name,
                            district=district_name,
                            progress_callback=province_callback,
                        )
                        if not should_skip:
                            scrape_stats.setdefault(province_name, {})[district_name] = new_count
                        continue

                    for neighborhood_item in neighborhoods:
                        neighborhood_name = neighborhood_item["name"]
                        if self._raise_if_stop_requested(province_callback, f"{neighborhood_name}: durdurma istegi alindi."):
                            stopped = True
                            break
                        if self._is_listing_limit_reached():
                            stopped = True
                            break

                        target = {
                            "url": neighborhood_item["url"],
                            "label": f"{province_name} / {district_name} / {neighborhood_name}",
                            "type": "mahalle",
                        }
                        should_skip, new_count = self._scrape_target(
                            target,
                            page_limit,
                            city=province_name,
                            district=district_name,
                            neighborhood=neighborhood_name,
                            progress_callback=province_callback,
                        )
                        if not should_skip and new_count > 0:
                            scrape_stats.setdefault(province_name, {})
                            scrape_stats[province_name][district_name] = scrape_stats[province_name].get(district_name, 0) + new_count

                    if stopped:
                        break

                if stopped:
                    break

            self.metrics["end_time"] = time.time()
            self.metrics["total_duration"] = self.metrics["end_time"] - self.metrics["start_time"]
            self.metrics["total_listings"] = len(self.all_listings)

            task_log.divider()
            if stopped and self._is_stop_requested():
                task_log.line("⚠️ ERKEN DURDURULDU", level="warning")
            elif self.all_listings:
                task_log.line("✅ TARAMA BASARIYLA TAMAMLANDI")
            else:
                task_log.line("❌ HIC ILAN BULUNAMADI", level="warning")
            task_log.divider()
            return scrape_stats
        finally:
            self._close_session()
