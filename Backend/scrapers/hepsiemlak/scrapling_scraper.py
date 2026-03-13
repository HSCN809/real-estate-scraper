# -*- coding: utf-8 -*-
"""HepsiEmlak Scrapling tabanli scraper."""

import os
import random
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from scrapling.fetchers import FetcherSession, StealthySession
from scrapling.parser import Selector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.config import get_hepsiemlak_config
from core.selectors import get_common_selectors, get_selectors
from utils.data_exporter import DataExporter
from utils.logger import get_logger

logger = get_logger(__name__)


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
    ):
        base_config = get_hepsiemlak_config()

        if subtype_path:
            category_path = subtype_path
            logger.info(f"Using subtype path: {subtype_path}")
        else:
            category_path = base_config.categories.get(listing_type, {}).get(category, "")

        self.base_config = base_config
        self.base_url = base_config.base_url + category_path
        self.listing_type = listing_type
        self.category = category
        self.subtype_path = subtype_path
        self.selected_cities = selected_cities or []
        self.selected_districts = selected_districts or {}
        self.use_stealth = use_stealth
        self.headless = headless
        self.request_timeout_ms = 45000

        self.subtype_name = None
        if subtype_path:
            parts = subtype_path.strip("/").split("/")
            if len(parts) >= 2:
                self.subtype_name = parts[-1].replace("-", "_")

        self.selectors = get_selectors("hepsiemlak", category)
        self.common_selectors = get_common_selectors("hepsiemlak")

        self.session_context = None
        self.session = None
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

    def _normalize_text(self, text: str) -> str:
        """URL icin Turkce karakterleri donustur ve slug olustur."""
        import unicodedata

        text = unicodedata.normalize("NFC", text)
        replacements = {
            "İ": "i",
            "I": "i",
            "Ğ": "g",
            "Ü": "u",
            "Ş": "s",
            "Ö": "o",
            "Ç": "c",
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
        }
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        return text.lower().replace(" ", "-")

    def _get_category_or_subtype_slug(self) -> str:
        """URL'de listing_type sonrasina eklenecek kategori/subtype slug'ini bul."""
        if self.subtype_path:
            path_parts = self.subtype_path.strip("/").split("/")
            if len(path_parts) >= 2:
                return path_parts[-1]
            return ""

        category_path = self.base_config.categories.get(self.listing_type, {}).get(self.category, "")
        if not category_path:
            return ""

        parts = category_path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[-1]
        return ""

    def _build_location_url(self, location_slug: str) -> str:
        """Sehir veya ilce icin Hepsiemlak URL'i olustur."""
        category_or_subtype = self._get_category_or_subtype_slug()
        base_location_url = f"https://www.hepsiemlak.com/{location_slug}-{self.listing_type}"
        if category_or_subtype:
            return f"{base_location_url}/{category_or_subtype}"
        return base_location_url

    def _get_city_url(self, city: str) -> str:
        """Sehir icin URL olustur."""
        return self._build_location_url(self._normalize_text(city))

    def _get_district_url(self, district: str) -> str:
        """Ilce icin URL olustur."""
        return self._build_location_url(self._normalize_text(district))

    def _create_session(self):
        """Scrapling session olustur."""
        if self.use_stealth:
            logger.info("Creating StealthySession...")
            self.session_context = StealthySession(
                headless=self.headless,
                solve_cloudflare=False,
                google_search=False,
                timeout=self.request_timeout_ms,
                network_idle=True,
                wait_selector=self.common_selectors.get("listing_results"),
            )
        else:
            logger.info("Creating FetcherSession...")
            self.session_context = FetcherSession(
                stealthy_headers=True,
                follow_redirects=True,
                timeout=30,
                retries=3,
                retry_delay=1,
            )

        if hasattr(self.session_context, "__enter__"):
            self.session = self.session_context.__enter__()
        else:
            self.session = self.session_context

        return self.session

    def _close_session(self):
        """Session'i kapat."""
        if not self.session and not self.session_context:
            return

        # Always close via context manager instance when available.
        if self.session_context and hasattr(self.session_context, "__exit__"):
            self.session_context.__exit__(None, None, None)
        elif self.session and hasattr(self.session, "__exit__"):
            self.session.__exit__(None, None, None)

        self.session_context = None
        self.session = None

    def fetch_page(self, url: str) -> Optional[Selector]:
        """Sayfayi fetch et ve Scrapling Response/Selector don."""
        try:
            if self.session is None:
                raise RuntimeError("Session is not initialized. Call _create_session first.")

            start_time = time.time()

            if self.use_stealth:
                fetch_kwargs: Dict[str, Any] = {
                    "network_idle": True,
                    "timeout": self.request_timeout_ms,
                }
                wait_selector = self.common_selectors.get("listing_results")
                if wait_selector:
                    fetch_kwargs["wait_selector"] = wait_selector
                response = self.session.fetch(url, **fetch_kwargs)
            else:
                response = self.session.get(url)

            fetch_time = time.time() - start_time

            if not response:
                self.metrics["failed_requests"] += 1
                logger.warning(f"Failed to fetch {url} - no response")
                return None

            status = getattr(response, "status", 200)
            if isinstance(status, int) and status >= 400:
                self.metrics["failed_requests"] += 1
                logger.warning(f"Failed to fetch {url} - status {status}")
                return None

            body = getattr(response, "body", b"")
            if not body or len(body) <= 100:
                self.metrics["failed_requests"] += 1
                logger.warning(f"Failed to fetch {url} - empty/short content")
                return None

            self.metrics["successful_requests"] += 1
            logger.info(f"Fetched {url} in {fetch_time:.2f}s")
            return response

        except Exception as e:
            self.metrics["failed_requests"] += 1
            logger.error(f"Error fetching {url}: {e}")
            return None

    def get_total_pages(self, selector: Selector) -> int:
        """Sayfalamadan toplam sayfa sayisini al."""
        try:
            count_elements = selector.css("span.applied-filters__count")
            if count_elements:
                count_text = str(count_elements[0].text).strip()
                count_text_clean = count_text.replace(".", "")
                match = re.search(r"(\d+)", count_text_clean)
                if match:
                    total_listings = int(match.group(1))
                    if total_listings <= 24:
                        logger.info(f"Total {total_listings} listings - single page")
                        return 1

            pagination_links = selector.css("ul.he-pagination__links a, ul.he-pagination a")
            max_page = 1

            for link in pagination_links:
                text = str(link.text).strip()
                if text.isdigit():
                    page_num = int(text)
                    if page_num > max_page:
                        max_page = page_num

            logger.info(f"Found {max_page} pages from pagination")
            return max_page

        except Exception as e:
            logger.warning(f"Error detecting pagination: {e}")
            return 1

    def _extract_text(self, element: Selector, css_selector: str, default: str = "Belirtilmemiş") -> str:
        """Selector'dan guvenli text cek."""
        if not css_selector:
            return default
        try:
            elements = element.css(css_selector)
            if not elements:
                return default
            value = str(elements[0].text).strip()
            return value if value else default
        except Exception:
            return default

    def _extract_attribute(
        self,
        element: Selector,
        css_selector: str,
        attribute: str,
        default: str = "Belirtilmemiş",
    ) -> str:
        """Selector'dan guvenli attribute cek."""
        if not css_selector:
            return default
        try:
            elements = element.css(css_selector)
            if not elements:
                return default
            value = str(elements[0].attrib.get(attribute, "")).strip()
            return value if value else default
        except Exception:
            return default

    def _extract_common_data(self, element: Selector, page_url: str = "") -> Dict[str, Any]:
        """Tum kategoriler icin ortak alanlari cikar."""
        price_sel = self.common_selectors.get("price", "span.list-view-price")
        title_sel = self.common_selectors.get("title", "h3")
        date_sel = self.common_selectors.get("date", "span.list-view-date")
        link_sel = self.common_selectors.get("link", "a.card-link")
        firm_sel = self.common_selectors.get("firm", "p.listing-card--owner-info__firm-name")

        listing_link = self._extract_attribute(element, link_sel, "href")
        if listing_link != "Belirtilmemiş" and page_url:
            listing_link = urljoin(page_url, listing_link)

        location_selectors = [
            "span.list-view-location address",
            "span.list-view-location",
            ".list-view-location address",
            ".list-view-location",
            "address",
        ]
        location_text = ""
        for loc_selector in location_selectors:
            location_text = self._extract_text(element, loc_selector, default="")
            if location_text and "/" in location_text:
                break

        location_parts = [part.strip() for part in location_text.split("/") if part.strip()]

        return {
            "fiyat": self._extract_text(element, price_sel),
            "baslik": self._extract_text(element, title_sel),
            "il": location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş",
            "ilce": location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş",
            "mahalle": location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş",
            "ilan_linki": listing_link,
            "ilan_tarihi": self._extract_text(element, date_sel),
            "emlak_ofisi": self._extract_text(element, firm_sel),
        }

    def extract_listings_from_page(
        self,
        selector: Selector,
        city: Optional[str] = None,
        district: Optional[str] = None,
        page_url: str = "",
    ) -> List[Dict[str, Any]]:
        """Sayfadaki ilanlari cikar."""
        listings: List[Dict[str, Any]] = []

        try:
            container_selector = self.common_selectors.get(
                "listing_container",
                "li.listing-item:not(.listing-item--promo)",
            )
            listing_elements = selector.css(container_selector)

            logger.info(f"Found {len(listing_elements)} listing elements")
            source_url = page_url or getattr(selector, "url", "")

            for element in listing_elements:
                try:
                    data = self._extract_from_scrapling_element(element, page_url=source_url)

                    if data:
                        if city and (not data.get("il") or data.get("il") == "Belirtilmemiş"):
                            data["il"] = city
                        if district and (not data.get("ilce") or data.get("ilce") == "Belirtilmemiş"):
                            data["ilce"] = district

                        data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        data["scraping_method"] = "scrapling"
                        listings.append(data)

                except Exception as e:
                    logger.debug(f"Error extracting listing: {e}")
                    continue

            logger.info(f"Successfully extracted {len(listings)} listings")

        except Exception as e:
            logger.error(f"Error extracting listings from page: {e}")

        return listings

    def _extract_from_scrapling_element(self, element: Selector, page_url: str = "") -> Dict[str, Any]:
        """Scrapling Selector element'inden verileri cikar."""
        data = self._extract_common_data(element, page_url=page_url)
        data.update(self._extract_category_specific_data(element))
        return data

    def _extract_category_specific_data(self, element: Selector) -> Dict[str, Any]:
        """Kategoriye ozel alanlari cikar."""
        if self.category == "konut":
            return {
                "oda_sayisi": self._extract_text(
                    element,
                    self.selectors.get("room_count", "span.houseRoomCount"),
                ),
                "metrekare": self._extract_text(
                    element,
                    self.selectors.get("size", "span.list-view-size"),
                ),
                "bina_yasi": self._extract_text(
                    element,
                    self.selectors.get("building_age", "span.buildingAge"),
                ),
                "kat": self._extract_text(
                    element,
                    self.selectors.get("floor", "span.floortype"),
                ),
            }

        if self.category == "arsa":
            data = {
                "arsa_metrekare": "Belirtilmemiş",
                "metrekare_fiyat": "Belirtilmemiş",
            }
            size_selector = self.selectors.get("size", "span.celly.squareMeter.list-view-size")
            for size_element in element.css(size_selector):
                size_text = str(size_element.text).strip()
                if not size_text:
                    continue
                normalized = size_text.lower().replace(" ", "")
                is_price_per_m2 = "tl/m²" in normalized or "tl/m2" in normalized
                if is_price_per_m2 and data["metrekare_fiyat"] == "Belirtilmemiş":
                    data["metrekare_fiyat"] = size_text
                elif ("m²" in normalized or "m2" in normalized) and data["arsa_metrekare"] == "Belirtilmemiş":
                    data["arsa_metrekare"] = size_text
            return data

        if self.category == "isyeri":
            return {
                "metrekare": self._extract_text(
                    element,
                    self.selectors.get("size", "span.celly.squareMeter.list-view-size"),
                )
            }

        if self.category == "devremulk":
            return {
                "oda_sayisi": self._extract_text(
                    element,
                    self.selectors.get("room_count", "span.houseRoomCount"),
                ),
                "metrekare": self._extract_text(
                    element,
                    self.selectors.get("size", "span.celly.squareMeter.list-view-size"),
                ),
                "bina_yasi": self._extract_text(
                    element,
                    self.selectors.get("building_age", "span.buildingAge"),
                ),
                "kat": self._extract_text(
                    element,
                    self.selectors.get("floor", "span.floortype"),
                ),
            }

        if self.category == "turistik_isletme":
            return {
                "oda_sayisi": self._extract_text(
                    element,
                    self.selectors.get("room_count", "span.workRoomCount"),
                ),
                "otel_tipi": self._extract_text(
                    element,
                    self.selectors.get("star_count", "span.startCount"),
                ),
            }

        return {}

    def scrape_city(self, city: str, max_pages: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Tek bir sehir icin ilanlari tara."""
        logger.info(f"Scraping city: {city}")

        city_listings: List[Dict[str, Any]] = []
        city_metrics = {
            "city": city,
            "pages_scraped": 0,
            "listings_found": 0,
            "start_time": time.time(),
            "duration": 0,
        }

        try:
            city_url = self._get_city_url(city)
            logger.info(f"City URL: {city_url}")

            selector = self.fetch_page(city_url)
            if not selector:
                logger.error(f"Failed to fetch city page: {city}")
                city_metrics["duration"] = time.time() - city_metrics["start_time"]
                return [], city_metrics

            total_pages = self.get_total_pages(selector)
            pages_to_scrape = min(max_pages, total_pages)
            logger.info(f"Scraping {pages_to_scrape} pages for {city}")

            for page_num in range(1, pages_to_scrape + 1):
                logger.info(f"Scraping page {page_num}/{pages_to_scrape}")

                current_url = city_url
                if page_num > 1:
                    current_url = f"{city_url}?page={page_num}"
                    selector = self.fetch_page(current_url)
                    if not selector:
                        logger.warning(f"Failed to fetch page {page_num}")
                        continue

                page_listings = self.extract_listings_from_page(
                    selector,
                    city=city,
                    page_url=getattr(selector, "url", current_url),
                )
                city_listings.extend(page_listings)

                city_metrics["pages_scraped"] += 1
                city_metrics["listings_found"] += len(page_listings)
                logger.info(f"Page {page_num}: Found {len(page_listings)} listings")

                if page_num < pages_to_scrape:
                    time.sleep(random.uniform(1, 3))

            city_metrics["duration"] = time.time() - city_metrics["start_time"]
            logger.info(
                f"Completed scraping {city}: {len(city_listings)} listings in {city_metrics['duration']:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error scraping city {city}: {e}")
            city_metrics["duration"] = time.time() - city_metrics["start_time"]

        return city_listings, city_metrics

    def scrape_district(self, city: str, district: str, max_pages: int = 2) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Tek bir ilce icin ilanlari tara."""
        logger.info(f"Scraping district: {city}/{district}")

        district_listings: List[Dict[str, Any]] = []
        district_metrics = {
            "city": city,
            "district": district,
            "pages_scraped": 0,
            "listings_found": 0,
            "start_time": time.time(),
            "duration": 0,
        }

        try:
            district_url = self._get_district_url(district)
            logger.info(f"District URL: {district_url}")

            selector = self.fetch_page(district_url)
            if not selector:
                logger.error(f"Failed to fetch district page: {district}")
                district_metrics["duration"] = time.time() - district_metrics["start_time"]
                return [], district_metrics

            total_pages = self.get_total_pages(selector)
            pages_to_scrape = min(max_pages, total_pages)
            logger.info(f"Scraping {pages_to_scrape} pages for {district}")

            for page_num in range(1, pages_to_scrape + 1):
                logger.info(f"Scraping page {page_num}/{pages_to_scrape}")

                current_url = district_url
                if page_num > 1:
                    current_url = f"{district_url}?page={page_num}"
                    selector = self.fetch_page(current_url)
                    if not selector:
                        logger.warning(f"Failed to fetch page {page_num}")
                        continue

                page_listings = self.extract_listings_from_page(
                    selector,
                    city=city,
                    district=district,
                    page_url=getattr(selector, "url", current_url),
                )
                district_listings.extend(page_listings)

                district_metrics["pages_scraped"] += 1
                district_metrics["listings_found"] += len(page_listings)
                logger.info(f"Page {page_num}: Found {len(page_listings)} listings")

                if page_num < pages_to_scrape:
                    time.sleep(random.uniform(1, 3))

            district_metrics["duration"] = time.time() - district_metrics["start_time"]
            logger.info(
                f"Completed scraping {district}: {len(district_listings)} listings in {district_metrics['duration']:.2f}s"
            )

        except Exception as e:
            logger.error(f"Error scraping district {district}: {e}")
            district_metrics["duration"] = time.time() - district_metrics["start_time"]

        return district_listings, district_metrics

    def start_scraping(self, max_pages_per_city: int = 3, max_pages_per_district: int = 2) -> Dict[str, Any]:
        """Ana tarama fonksiyonu."""
        logger.info("Starting Scrapling-based scraping...")

        self.metrics["start_time"] = time.time()
        all_listings: List[Dict[str, Any]] = []
        detailed_metrics: List[Dict[str, Any]] = []

        try:
            self._create_session()

            for city in self.selected_cities:
                if self.selected_districts and city in self.selected_districts:
                    districts = self.selected_districts[city]
                    logger.info(f"Scraping {len(districts)} districts in {city}")

                    for district in districts:
                        district_listings, district_metrics = self.scrape_district(
                            city, district, max_pages_per_district
                        )
                        all_listings.extend(district_listings)
                        detailed_metrics.append(district_metrics)
                        time.sleep(random.uniform(2, 4))
                else:
                    city_listings, city_metrics = self.scrape_city(city, max_pages_per_city)
                    all_listings.extend(city_listings)
                    detailed_metrics.append(city_metrics)

                if city != self.selected_cities[-1]:
                    time.sleep(random.uniform(3, 6))

            self.metrics["end_time"] = time.time()
            self.metrics["total_duration"] = self.metrics["end_time"] - self.metrics["start_time"]
            self.metrics["total_listings"] = len(all_listings)
            self.metrics["total_pages"] = sum(m.get("pages_scraped", 0) for m in detailed_metrics)

            if all_listings:
                listings_by_city: Dict[str, List[Dict[str, Any]]] = {}
                for listing in all_listings:
                    city_name = str(listing.get("il") or "Belirtilmemiş").strip() or "Belirtilmemiş"
                    listings_by_city.setdefault(city_name, []).append(listing)

                self.exporter.save_by_city(
                    listings_by_city,
                    prefix=f"hepsiemlak_{self.listing_type}_{self.category}_scrapling",
                    format="excel",
                    city_district_map=self.selected_districts if self.selected_districts else None,
                )

                import pandas as pd

                df = pd.DataFrame(all_listings)
                csv_path = (
                    f"Outputs/HepsiEmlak Output/Scrapling/"
                    f"hepsiemlak_{self.listing_type}_{self.category}_scrapling.csv"
                )
                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                logger.info(f"Saved {len(all_listings)} listings to {csv_path}")

            logger.info("Scraping completed successfully!")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        finally:
            self._close_session()

        return {
            "listings": all_listings,
            "metrics": self.metrics,
            "detailed_metrics": detailed_metrics,
            "summary": self.get_summary(),
        }

    def get_summary(self) -> Dict[str, Any]:
        """Ozet metrikleri getir."""
        total_requests = self.metrics["successful_requests"] + self.metrics["failed_requests"]
        return {
            "total_duration_seconds": round(self.metrics["total_duration"], 2),
            "total_listings": self.metrics["total_listings"],
            "total_pages": self.metrics["total_pages"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": round(self.metrics["successful_requests"] / max(1, total_requests) * 100, 2),
            "listings_per_second": round(
                self.metrics["total_listings"] / max(1, self.metrics["total_duration"]), 2
            ),
            "pages_per_second": round(
                self.metrics["total_pages"] / max(1, self.metrics["total_duration"]), 2
            ),
        }

    def print_summary(self):
        """Ozeti konsola yazdir."""
        summary = self.get_summary()

        print("\n" + "=" * 70)
        print("SCRAPLING SCRAPER - OZET RAPOR")
        print("=" * 70)
        print(f"Toplam Sure: {summary['total_duration_seconds']} saniye")
        print(f"Toplam Ilan: {summary['total_listings']}")
        print(f"Toplam Sayfa: {summary['total_pages']}")
        print(f"Basarili Istek: {summary['successful_requests']}")
        print(f"Basarisiz Istek: {summary['failed_requests']}")
        print(f"Basari Orani: {summary['success_rate']}%")
        print(f"Saniyede Ilan: {summary['listings_per_second']}")
        print(f"Saniyede Sayfa: {summary['pages_per_second']}")
        print("=" * 70)


def test_scrapling_scraper():
    """Scrapling scraper'i test et."""
    print("Scrapling Scraper Testi Basliyor...")

    scraper = HepsiemlakScraplingScraper(
        listing_type="kiralik",
        category="konut",
        selected_cities=["Istanbul"],
        selected_districts={"Istanbul": ["Kadikoy"]},
        use_stealth=True,
        headless=True,
    )

    try:
        result = scraper.start_scraping(max_pages_per_city=2, max_pages_per_district=1)
        scraper.print_summary()

        print(f"\nToplam {len(result['listings'])} ilan bulundu.")
        if result["listings"]:
            print("\nIlk 3 ilan:")
            for i, listing in enumerate(result["listings"][:3], 1):
                print(f"{i}. {listing.get('baslik', 'N/A')} - {listing.get('fiyat', 'N/A')}")

        return result

    except Exception as e:
        print(f"Test hatasi: {e}")
        return None


if __name__ == "__main__":
    test_scrapling_scraper()
