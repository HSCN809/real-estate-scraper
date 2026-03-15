# -*- coding: utf-8 -*-
"""HepsiEmlak Go Proxy Bypass Scraper - Cloudflare Bypass with uTLS"""

import logging
import os
import random
import re
import time
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.config import get_hepsiemlak_config
from core.selectors import get_common_selectors, get_selectors
from utils.data_exporter import DataExporter
from utils.logger import TaskLogLayout, get_logger
from python_proxy.go_proxy_client import CloudflareBypassClient

from .main import save_listings_to_db

logger = get_logger(__name__)
task_log = TaskLogLayout(logger)


class HepsiemlakGoProxyScraper:
    """HepsiEmlak platformu icin Go Proxy ile Cloudflare bypass eden scraper."""

    def __init__(
        self,
        listing_type: str = "satilik",
        category: str = "konut",
        subtype_path: Optional[str] = None,
        selected_cities: Optional[List[str]] = None,
        selected_districts: Optional[Dict[str, List[str]]] = None,
        proxy_url: Optional[str] = None,
        user_agent: Optional[str] = None,
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

        # Go Proxy Configuration - Auto-detect from environment or use default
        import os
        if proxy_url is None:
            # In Docker, use the service name
            if os.getenv("ENVIRONMENT") == "production" or os.getenv("USE_GO_PROXY", "false").lower() == "true":
                proxy_url = os.getenv("GO_PROXY_URL", "http://invisible-proxy:8080")
            else:
                proxy_url = os.getenv("GO_PROXY_URL", "http://127.0.0.1:8080")

        self.proxy_client = CloudflareBypassClient(
            proxy_url=proxy_url,
            user_agent=user_agent
        )
        self.proxy_url = proxy_url

        # Selectors
        self.selectors = get_selectors("hepsiemlak", category)
        self.common_selectors = get_common_selectors("hepsiemlak")

        # Session state
        self.session_cookies = {}

        # Database and export
        self.db = None
        self.scrape_session_id = None
        self.total_scraped_count = 0
        self.new_listings_count = 0
        self.duplicate_count = 0
        self.total_new_listings = 0

        # Metrics
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_pages": 0,
            "total_listings": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_duration": 0,
            "cloudflare_challenges": 0,
        }

        # Exporter
        self.exporter = DataExporter(
            output_dir="Outputs/HepsiEmlak Output/GoProxy",
            listing_type=listing_type,
            category=category,
            subtype=self.subtype_name,
        )

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
        parts.append("go_proxy")
        return "_".join(parts)

    def _normalize_text(self, text: str) -> str:
        import unicodedata

        text = unicodedata.normalize("NFC", text)
        for tr_char, en_char in {
            "I": "i",
            "\u0130": "i",
            "\u011e": "g",
            "\u00dc": "u",
            "\u015e": "s",
            "\u00d6": "o",
            "\u00c7": "c",
            "\u0131": "i",
            "\u011f": "g",
            "\u00fc": "u",
            "\u015f": "s",
            "\u00f6": "o",
            "\u00e7": "c",
        }.items():
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

    def _fetch_page_with_retry(self, url: str, max_retries: int = 10) -> Optional[BeautifulSoup]:
        """
        Fetch page using Go proxy with intelligent retry logic for Cloudflare challenges
        """
        initial_delay = 4.0

        for attempt in range(max_retries):
            try:
                task_log.debug(f"Fetching {url} via Go Proxy (attempt {attempt + 1}/{max_retries})")

                # Use the proxy client's fetch_with_retry method
                response = self.proxy_client.fetch_with_retry(
                    url=url,
                    max_retries=6,
                    initial_delay=initial_delay
                )

                # Check response
                if response.error:
                    self.metrics["failed_requests"] += 1
                    if response.status in [403, 503]:
                        self.metrics["cloudflare_challenges"] += 1
                    task_log.warning(f"Proxy error: {response.error} (status: {response.status})")

                    # Check if we should retry
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)  # Exponential backoff
                        if response.status in [403, 503]:
                            task_log.info(f"Cloudflare challenge detected, retrying in {delay:.1f}s...")
                        else:
                            task_log.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        task_log.error(f"Failed to fetch {url} after {max_retries} attempts")
                        return None

                if response.status == 200:
                    body = response.body or b""
                    if len(body) < 120:
                        self.metrics["failed_requests"] += 1
                        if attempt < max_retries - 1:
                            delay = initial_delay * (2 ** attempt)
                            task_log.warning(f"Suspiciously short response body ({len(body)} bytes), retrying in {delay:.1f}s...")
                            time.sleep(delay)
                            continue
                        task_log.error(f"Response body is too short after {max_retries} attempts: {url}")
                        return None

                    # Parse HTML
                    soup = BeautifulSoup(body.decode('utf-8', errors='ignore'), 'html.parser')

                    # Check for Cloudflare challenge page
                    if self._is_cloudflare_challenge(soup):
                        self.metrics["cloudflare_challenges"] += 1
                        if attempt < max_retries - 1:
                            delay = initial_delay * (2 ** attempt)
                            task_log.warning(f"Cloudflare challenge detected in response, retrying in {delay:.1f}s...")
                            time.sleep(delay)
                            continue
                        else:
                            task_log.error(f"Failed to bypass Cloudflare after {max_retries} attempts")
                            return None

                    self.metrics["successful_requests"] += 1
                    return soup

                else:
                    self.metrics["failed_requests"] += 1
                    task_log.warning(f"Unexpected status code: {response.status}")

                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        return None

            except Exception as exc:
                self.metrics["failed_requests"] += 1
                task_log.error(f"Error fetching {url}: {exc}")

                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    task_log.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    return None

        return None

    def _is_cloudflare_challenge(self, soup: BeautifulSoup) -> bool:
        """Check if page is an active Cloudflare challenge page (avoid false positives)."""
        strong_indicators = [
            "cf-challenge",
            "challenge-platform",
            "cf-spinner",
            "just a moment",
            "checking your browser",
            "attention required",
            "please enable javascript and cookies",
            "/cdn-cgi/challenge-platform/",
            "cf-browser-verification",
            "cf-turnstile",
        ]

        page_text = soup.get_text(" ", strip=True).lower()
        page_html = str(soup).lower()
        title_text = (soup.title.get_text(strip=True).lower() if soup.title else "")

        if "just a moment" in title_text or "attention required" in title_text:
            return True

        for indicator in strong_indicators:
            if indicator in page_text or indicator in page_html:
                return True

        cf_elements = soup.select(
            "form#challenge-form, "
            "div.challenge-form, "
            "div.cf-browser-verification, "
            "div[id*='cf-challenge'], "
            "script[src*='challenge-platform']"
        )
        return bool(cf_elements)

    def get_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total number of pages from pagination"""
        try:
            # Check if there are very few listings
            count_elements = soup.find_all("span", class_="applied-filters__count")
            if count_elements:
                count_text = count_elements[0].get_text().strip().replace(".", "")
                match = re.search(r"(\d+)", count_text)
                if match and int(match.group(1)) <= 24:
                    return 1

            # Check pagination links
            pagination_links = soup.select("ul.he-pagination__links a, ul.he-pagination a")
            max_page = 1
            for link in pagination_links:
                text = link.get_text().strip()
                if text.isdigit():
                    max_page = max(max_page, int(text))
                    continue

                href = link.get("href", "")
                if href:
                    parsed = urlparse(href)
                    page_values = parse_qs(parsed.query).get("page", [])
                    if page_values and str(page_values[0]).isdigit():
                        max_page = max(max_page, int(page_values[0]))

            return max_page
        except Exception as exc:
            task_log.warning(f"Error detecting pagination: {exc}")
            return 1

    def _extract_text(self, element, css_selector: Any, default: str = "Belirtilmemis") -> str:
        """Extract text from BeautifulSoup element with selector fallback."""
        try:
            if isinstance(css_selector, list):
                selectors = [selector for selector in css_selector if selector]
            else:
                selectors = [css_selector] if css_selector else []

            selected = None
            for selector in selectors:
                selected = element.select_one(selector)
                if selected:
                    break

            value = selected.get_text().strip() if selected else ""
            return value or default
        except Exception:
            return default

    def _extract_attribute(self, element, css_selector: Any, attribute: str, default: str = "Belirtilmemis") -> str:
        """Extract attribute from BeautifulSoup element with selector fallback."""
        try:
            if isinstance(css_selector, list):
                selectors = [selector for selector in css_selector if selector]
            else:
                selectors = [css_selector] if css_selector else []

            selected = None
            for selector in selectors:
                selected = element.select_one(selector)
                if selected:
                    break

            value = selected.get(attribute, "").strip() if selected else ""
            return value or default
        except Exception:
            return default

    def _extract_common_data(self, element, page_url: str = "") -> Dict[str, Any]:
        """Extract common listing data"""
        listing_link = self._extract_attribute(
            element,
            self.common_selectors.get("link", "a.card-link"),
            "href"
        )
        if listing_link and not str(listing_link).lower().startswith("belirtilmem") and page_url:
            listing_link = urljoin(page_url, listing_link)

        # Extract location
        location_text = ""
        loc_selectors = [
            "span.list-view-location address",
            "span.list-view-location",
            ".list-view-location address",
            ".list-view-location",
            "address"
        ]
        for loc_selector in loc_selectors:
            location_text = self._extract_text(element, loc_selector, default="")
            if location_text and "/" in location_text:
                break

        location_parts = [part.strip() for part in location_text.split("/") if part.strip()]

        return {
            "fiyat": self._extract_text(element, self.common_selectors.get("price", "span.list-view-price")),
            "baslik": self._extract_text(
                element,
                [
                    self.common_selectors.get("title", "h3"),
                    "h2",
                    "a.card-link h2",
                    "a.card-link h3",
                    ".listing-card__title",
                ],
            ),
            "il": location_parts[0] if len(location_parts) > 0 else "Belirtilmemis",
            "ilce": location_parts[1] if len(location_parts) > 1 else "Belirtilmemis",
            "mahalle": location_parts[2] if len(location_parts) > 2 else "Belirtilmemis",
            "ilan_linki": listing_link,
            "ilan_tarihi": self._extract_text(element, self.common_selectors.get("date", "span.list-view-date")),
            "emlak_ofisi": self._extract_text(element, self.common_selectors.get("firm", "p.listing-card--owner-info__firm-name")),
        }

    def _extract_category_specific_data(self, element) -> Dict[str, Any]:
        """Extract category-specific data"""
        if self.category == "konut":
            return {
                "oda_sayisi": self._extract_text(element, self.selectors.get("room_count", "span.houseRoomCount")),
                "metrekare": self._extract_text(element, self.selectors.get("size", "span.list-view-size")),
                "bina_yasi": self._extract_text(element, self.selectors.get("building_age", "span.buildingAge")),
                "kat": self._extract_text(element, self.selectors.get("floor", "span.floortype"))
            }

        elif self.category == "arsa":
            data = {"arsa_metrekare": "Belirtilmemis", "metrekare_fiyat": "Belirtilmemis"}
            size_elements = element.select(self.selectors.get("size", "span.celly.squareMeter.list-view-size"))
            for size_element in size_elements:
                size_text = size_element.get_text().strip()
                normalized = size_text.lower().replace(" ", "").replace("²", "2")
                if "tl/m2" in normalized and data["metrekare_fiyat"] == "Belirtilmemis":
                    data["metrekare_fiyat"] = size_text
                elif "m2" in normalized and data["arsa_metrekare"] == "Belirtilmemis":
                    data["arsa_metrekare"] = size_text
            return data

        elif self.category == "isyeri":
            return {"metrekare": self._extract_text(element, self.selectors.get("size", "span.celly.squareMeter.list-view-size"))}

        elif self.category == "devremulk":
            return {
                "oda_sayisi": self._extract_text(element, self.selectors.get("room_count", "span.houseRoomCount")),
                "metrekare": self._extract_text(element, self.selectors.get("size", "span.celly.squareMeter.list-view-size")),
                "bina_yasi": self._extract_text(element, self.selectors.get("building_age", "span.buildingAge")),
                "kat": self._extract_text(element, self.selectors.get("floor", "span.floortype"))
            }

        elif self.category == "turistik_isletme":
            return {
                "oda_sayisi": self._extract_text(element, self.selectors.get("room_count", "span.workRoomCount")),
                "otel_tipi": self._extract_text(element, self.selectors.get("star_count", "span.startCount"))
            }

        return {}

    def _select_listing_elements(self, soup: BeautifulSoup):
        primary_selector = self.common_selectors.get("listing_container", "li.listing-item:not(.listing-item--promo)")
        fallback_selectors = [
            primary_selector,
            "li.listing-item",
            "li[class*='listing']",
            "article[class*='listing']",
            ".listing-card",
        ]
        for selector in fallback_selectors:
            elements = soup.select(selector)
            if elements:
                return elements
        return []

    def extract_listings_from_page(
        self,
        soup: BeautifulSoup,
        city: Optional[str] = None,
        district: Optional[str] = None,
        page_url: str = ""
    ) -> List[Dict[str, Any]]:
        """Extract listings from a page"""
        listings: List[Dict[str, Any]] = []
        try:
            listing_elements = self._select_listing_elements(soup)
            source_url = page_url

            for element in listing_elements:
                data = self._extract_common_data(element, page_url=source_url)
                data.update(self._extract_category_specific_data(element))

                if not data:
                    continue

                if not data.get("ilan_linki") or str(data.get("ilan_linki")).lower().startswith("belirtilmem"):
                    continue

                # Override location if provided
                if city and (not data.get("il") or str(data.get("il")).lower().startswith("belirtilmem")):
                    data["il"] = city
                if district and (not data.get("ilce") or str(data.get("ilce")).lower().startswith("belirtilmem")):
                    data["ilce"] = district

                data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["scraping_method"] = "go_proxy"

                listings.append(data)

        except Exception as exc:
            task_log.error(f"Error extracting listings from page: {exc}")

        return listings

    def _persist_listings(self, listings: List[Dict[str, Any]]) -> Tuple[int, int, int]:
        """Save listings to database"""
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

    def _log_location_start(self, location_name: str, location_url: str) -> None:
        """Log location scraping start"""
        task_log.section(
            f"Scanning: {location_name}",
            f"URL: {location_url}",
            "Method: Go Proxy (uTLS + Mobile IP)",
        )

    def _scrape_location(
        self,
        location_name: str,
        location_url: str,
        max_pages: Optional[int],
        city: Optional[str] = None,
        district: Optional[str] = None,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """Scrape a location (city or district)"""
        listings: List[Dict[str, Any]] = []
        self._log_location_start(location_name, location_url)

        # Fetch first page
        first_page = self._fetch_page_with_retry(location_url)
        if not first_page:
            task_log.warning(f"First page could not be fetched: {location_name}")
            return listings

        # Get pagination
        pages_to_scrape = self._resolve_page_limit(self.get_total_pages(first_page), max_pages)
        task_log.info(f"Pages to scrape: {pages_to_scrape}")

        # Scrape pages
        for page_num in range(1, pages_to_scrape + 1):

            current_url = self._build_page_url(location_url, page_num)
            task_log.info(f"[{page_num}/{pages_to_scrape}] {location_name} - page {page_num} is being scraped...")

            # Fetch page
            soup = first_page if page_num == 1 else self._fetch_page_with_retry(current_url)
            if not soup:
                task_log.warning(f"   Page {page_num} could not be fetched, skipping")
                continue

            # Update progress
            if progress_callback:
                progress_callback(
                    f"{location_name} - Sayfa {page_num}/{pages_to_scrape}",
                    current=page_num,
                    total=pages_to_scrape,
                    progress=int((page_num / max(1, pages_to_scrape)) * 100),
                )

            # Extract listings
            page_listings = self.extract_listings_from_page(
                soup,
                city=city,
                district=district,
                page_url=current_url,
            )

            listings.extend(page_listings)
            new_count, updated_count, unchanged_count = self._persist_listings(page_listings)

            task_log.info(f"   Page {page_num}: extracted {len(page_listings)} listings")
            task_log.info(f"   Page {page_num}: {new_count} new, {updated_count} updated, {unchanged_count} unchanged")

            self.metrics["total_pages"] += 1

            # Random delay between pages
            if page_num < pages_to_scrape:
                time.sleep(random.uniform(1, 3))

        task_log.info(f"{location_name} completed - processed {len(listings)} listings")
        return listings

    def _resolve_page_limit(self, detected_total_pages: Optional[int], requested_max_pages: Optional[int]) -> int:
        """Resolve the final page limit"""
        total_pages = max(1, detected_total_pages or 1)
        if requested_max_pages is None or requested_max_pages <= 0:
            return total_pages
        return min(requested_max_pages, total_pages)

    def _make_city_progress_callback(self, progress_callback, current_city_idx: int, num_cities: int, city_name: str):
        """Create a city-specific progress callback"""
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

    def start_scraping_api(self, max_pages: Optional[int] = None, progress_callback=None) -> Dict[str, Any]:
        """API-compatible entry point used by Celery tasks."""
        return self.start_scraping(
            max_pages_per_city=max_pages,
            max_pages_per_district=max_pages,
            progress_callback=progress_callback,
        )

    def start_scraping(
        self,
        max_pages_per_city: int = 3,
        max_pages_per_district: int = 2,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Start scraping process"""
        task_log.section(
            "GO PROXY CLOUDFLARE BYPASS SCRAPER STARTED",
            f"Platform: HepsiEmlak {self.listing_type.capitalize()} {self.category.capitalize()}",
            f"Proxy URL: {self.proxy_url}",
            f"Cities: {', '.join(self.selected_cities)}",
        )

        self.metrics["start_time"] = time.time()

        try:
            all_listings: List[Dict[str, Any]] = []
            total_cities = len(self.selected_cities)

            for city_idx, city in enumerate(self.selected_cities, 1):
                city_callback = self._make_city_progress_callback(progress_callback, city_idx, total_cities, city)

                # Check if we need to scrape districts
                if self.selected_districts and city in self.selected_districts:
                    districts = self.selected_districts[city]

                    for district_idx, district in enumerate(districts, 1):

                        district_data = self._scrape_location(
                            location_name=f"{district} ({district_idx}/{len(districts)})",
                            location_url=self._get_district_url(district),
                            max_pages=max_pages_per_district,
                            city=city,
                            district=district,
                            progress_callback=city_callback,
                        )

                        if district_data:
                            all_listings.extend(district_data)

                        if district_idx < len(districts):
                            time.sleep(random.uniform(1, 3))

                else:
                    # Scrape the entire city
                    city_listings = self._scrape_location(
                        location_name=city,
                        location_url=self._get_city_url(city),
                        max_pages=max_pages_per_city,
                        city=city,
                        progress_callback=city_callback,
                    )

                    if city_listings:
                        all_listings.extend(city_listings)

                if city_idx < total_cities:
                    time.sleep(random.uniform(2, 4))

            self.metrics["end_time"] = time.time()
            self.metrics["total_duration"] = self.metrics["end_time"] - self.metrics["start_time"]
            self.metrics["total_listings"] = len(all_listings)

            task_log.section(
                "GO PROXY SCRAPER TAMAMLANDI",
                f"Total listings: {len(all_listings)}",
                f"Total duration: {self.metrics['total_duration']:.2f} seconds",
                f"Successful requests: {self.metrics['successful_requests']}",
                f"Failed requests: {self.metrics['failed_requests']}",
                f"Cloudflare challenges: {self.metrics['cloudflare_challenges']}",
            )

            return {
                "listings": all_listings,
                "metrics": self.metrics,
                "summary": self.get_summary()
            }

        except Exception as exc:
            task_log.error(f"Scraping error: {exc}")
            return {
                "listings": [],
                "metrics": self.metrics,
                "error": str(exc)
            }

    def get_summary(self) -> Dict[str, Any]:
        """Get scraping summary"""
        total_requests = self.metrics["successful_requests"] + self.metrics["failed_requests"]
        return {
            "scraping_method": "go_proxy",
            "proxy_url": self.proxy_url,
            "total_duration_seconds": round(self.metrics["total_duration"], 2),
            "total_listings": self.metrics["total_listings"],
            "total_pages": self.metrics["total_pages"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "cloudflare_challenges": self.metrics["cloudflare_challenges"],
            "success_rate": round(self.metrics["successful_requests"] / max(1, total_requests) * 100, 2),
            "listings_per_second": round(self.metrics["total_listings"] / max(1, self.metrics["total_duration"]), 2),
            "pages_per_second": round(self.metrics["total_pages"] / max(1, self.metrics["total_duration"]), 2),
        }

    def print_summary(self):
        """Print detailed summary"""
        summary = self.get_summary()
        task_log.section(
            "GO PROXY SCRAPER - SUMMARY",
            f"Method: {summary['scraping_method']}",
            f"Proxy: {summary['proxy_url']}",
            f"Total duration: {summary['total_duration_seconds']} seconds",
            f"Total listings: {summary['total_listings']}",
            f"Total pages: {summary['total_pages']}",
            f"Successful requests: {summary['successful_requests']}",
            f"Failed requests: {summary['failed_requests']}",
            f"Cloudflare challenges: {summary['cloudflare_challenges']}",
            f"Success rate: {summary['success_rate']}%",
            f"Listings per second: {summary['listings_per_second']}",
            f"Pages per second: {summary['pages_per_second']}",
        )


def test_go_proxy_scraper():
    """Test the Go proxy scraper (Docker compatible)"""
    task_log.section("GO PROXY SCRAPER TEST STARTED")

    # Auto-detect proxy URL based on environment
    import os
    proxy_url = None  # Let auto-detection handle it

    # Override for testing if needed
    # proxy_url = os.getenv("GO_PROXY_URL", "http://127.0.0.1:8080")

    scraper = HepsiemlakGoProxyScraper(
        listing_type="kiralik",
        category="konut",
        selected_cities=["Istanbul"],
        selected_districts={"Istanbul": ["Kadikoy"]},
        proxy_url=proxy_url,  # Will be auto-detected
    )

    try:
        result = scraper.start_scraping(max_pages_per_city=1, max_pages_per_district=1)
        scraper.print_summary()

        task_log.info(f"Test successful! Total listings: {len(result.get('listings', []))}")
        return result

    except Exception as exc:
        task_log.error(f"Test error: {exc}")
        return None


if __name__ == "__main__":
    test_go_proxy_scraper()

