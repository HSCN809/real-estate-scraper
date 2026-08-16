"""EmlakJet Ana Scraper - gizli mod"""

import os
import random
import sys
import time
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.base_scraper import BaseScraper
from core.config import get_emlakjet_config
from core.driver_manager import DriverManager
from core.failed_pages_tracker import FailedPageInfo, failed_pages_tracker
from utils.logger import TaskLogLayout, get_logger

from .listings import CATEGORY_PARSERS, extract_listings_from_html
from .parsers import KonutParser
from .persist import save_listings_to_db
from .urls import build_city_url, parse_location_options, should_scrape_city_level
from .urls import normalize_location_token as _normalize_location_token

logger = get_logger(__name__)
task_log = TaskLogLayout(logger)


class EmlakJetScraper(BaseScraper):
    """EmlakJet platformu ana scraper sınıfı"""

    CATEGORY_PARSERS = CATEGORY_PARSERS

    def __init__(
        self,
        driver: WebDriver,
        base_url: str = "https://www.emlakjet.com",
        category: str = "konut",
        selected_locations: dict | None = None,
        listing_type: str | None = None,  # satilik/kiralik
        subtype_path: str | None = None,  # Alt kategori URL path'i (örn: /satilik-daire)
    ):
        super().__init__(driver, base_url, "emlakjet", category, selected_locations)

        self.emlakjet_config = get_emlakjet_config()
        self.listing_type = listing_type
        self.subtype_path = subtype_path
        self.total_new_listings = 0  # Global kümülatif yeni ilan sayacı
        # Uygun parser'ı başlat
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()

    def extract_listing_data(self, container) -> dict[str, Any] | None:
        html = container.get_attribute("outerHTML") if container is not None else ""
        listings = extract_listings_from_html(
            html,
            page_url=getattr(self.driver, "current_url", ""),
            category=self.category,
            scraping_method="selenium",
        )
        return listings[0] if listings else None

    def parse_category_details(self, quick_info: str, title: str) -> dict[str, Any]:
        """Kategori parser'ı ile detayları parse et"""
        return self.parser.parse_category_details(quick_info, title)

    @property
    def subtype_name(self) -> str | None:
        """Dosya adlandırma için subtype_path'inden alt kategori adını çıkar"""
        if self.subtype_path:
            # /satilik-daire -> daire
            path_part = self.subtype_path.strip("/").split("-")
            if len(path_part) >= 2:
                return path_part[-1].replace("-", "_")
        return None

    def _log_location_start(self, location_name: str, location_url: str) -> None:
        task_log.section(
            f"📍 Taranıyor: {location_name}",
            f"🌐 {location_url}",
            "🧭 Yöntem: selenium",
        )

    def _log_location_plan(self, location_name: str, pages_to_scrape: int) -> None:
        task_log.line(f"{location_name}: scraping {pages_to_scrape} pages via selenium")
        task_log.line(f"📄 {pages_to_scrape} sayfa taranacak")

    def _log_page_start(
        self, location_name: str, page_num: int, total_pages: int
    ) -> None:
        task_log.line(
            f"🔍 [{page_num}/{total_pages}] {location_name} - Sayfa {page_num} taranıyor..."
        )

    def _log_page_result(
        self,
        page_num: int,
        extracted_count: int,
        new_count: int,
        updated_count: int,
        unchanged_count: int,
    ) -> None:
        task_log.line(f"   ✅ Sayfa {page_num}: {extracted_count} ilan çıkarıldı")
        task_log.line(
            f"   💾 Sayfa {page_num}: {new_count} yeni, {updated_count} güncellendi, {unchanged_count} değişmedi"
        )

    def _log_location_complete(self, location_name: str, listing_count: int) -> None:
        task_log.line(f"✅ {location_name} tamamlandı - {listing_count} ilan işlendi")

    def _log_retry_round(
        self, retry_round: int, max_retries: int, failed_count: int
    ) -> None:
        task_log.section(
            f"🔄 YENİDEN DENEME #{retry_round}/{max_retries}",
            f"📊 {failed_count} başarısız sayfa tekrar taranacak",
        )

    def _log_retry_summary(self, successful_retries: int, failed_count: int) -> None:
        task_log.section(
            "📊 RETRY ÖZETİ",
            f"   ✅ Başarılı retry: {successful_retries}",
            f"   ❌ Kalan başarısız: {failed_count}",
        )

    def scrape_current_page(self) -> list[dict[str, Any]]:
        try:
            if not self.common_selectors.get("listing_container"):
                task_log.line("No listing_container selector defined", level="error")
                return []
            return extract_listings_from_html(
                self.driver.page_source,
                page_url=self.driver.current_url,
                category=self.category,
                scraping_method="selenium",
            )
        except Exception as e:
            task_log.line(f"Sayfa tarama hatası: {e}", level="error")
            return []

    def get_location_options(self, location_type: str, current_url: str) -> tuple:
        """Mevcut sayfadan lokasyon seçeneklerini ve ilan sayısını al"""
        try:
            logger.info(f"Getting {location_type} options...")

            self.driver.get(current_url)
            self.random_long_wait()  # Gizli mod: lokasyon listesi

            # Sayfa zaten yüklü — ilan sayısını da aynı anda al
            listing_count = self._parse_listing_count()

            location_options = parse_location_options(
                self.driver.page_source, current_url, location_type
            )

            # Lokasyonları 4 sütunda göster
            if location_options:
                print(f"\n{'=' * 80}")
                print(f"{location_type.upper()} (Toplam ilan: {listing_count})")
                print("=" * 80)

                cols = 4
                col_width = 20
                for i in range(0, len(location_options), cols):
                    row = ""
                    for j in range(cols):
                        idx = i + j
                        if idx < len(location_options):
                            name = location_options[idx]["name"][: col_width - 4]
                            row += f"{idx + 1:2d}. {name:<{col_width - 4}}"
                    print(row)

                print(
                    f"\nToplam {len(location_options)} {location_type.lower()} bulundu."
                )

            return location_options, listing_count

        except Exception as e:
            logger.error(f"Error getting {location_type} options: {e}")
            return [], 0

    def get_max_pages(self, target_url: str | None = None) -> int:
        """URL için binary search ile maksimum sayfa sayısını al"""
        try:
            if target_url:
                self.driver.get(target_url)
                self.random_medium_wait()  # Gizli mod

            # JavaScript ile yükleme beklemesi için explicit wait
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: (
                        d.execute_script("return document.readyState") == "complete"
                    )
                )
                logger.debug("Page fully loaded (document ready)")
            except Exception as e:
                logger.debug(f"Timeout waiting for document ready: {e}")

            # Ekstra bekleme - pagination elementleri yüklenmesi için
            time.sleep(2)

            pagination_links = self.driver.find_elements(
                By.CSS_SELECTOR, "a[href*='sayfa=']"
            )
            if pagination_links:
                from scrapers.common.pagination import max_page_from_hrefs

                hrefs = [link.get_attribute("href") for link in pagination_links]
                max_from_links = max_page_from_hrefs(hrefs, "sayfa")
                if max_from_links > 1:
                    return max_from_links

            right_arrow = self.driver.find_elements(
                By.CSS_SELECTOR, "a[aria-label='Sonraki Sayfa']"
            )
            if not right_arrow or not pagination_links:
                return 1

            # Sonraki ok var - son sayfaya git
            # Son sayfaya gitmek için büyük bir sayfa numarası dene (örn: 1000)
            # Emlakjet otomatik olarak son sayfaya yönlendirecek
            separator = "&" if "?" in target_url else "?"
            last_page_url = f"{target_url}{separator}sayfa=9999"

            print("🔍 Son sayfa aranıyor...")
            self.driver.get(last_page_url)
            time.sleep(2)

            # Son sayfadaki pagination link'lerini al
            last_page_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href, 'sayfa=')]"
            )

            if not last_page_links:
                # Hâlâ pagination yok, 1 varsay
                return 1

            # Son sayfadan maksimum sayfa numarasını çıkar
            page_numbers = []
            for link in last_page_links:
                try:
                    href = link.get_attribute("href")
                    if "?sayfa=" in href:
                        page_num = int(href.split("?sayfa=")[1].split("&")[0])
                        page_numbers.append(page_num)
                except Exception as e:
                    logger.debug(f"Error parsing page number from link: {e}")

            max_page = max(page_numbers) if page_numbers else 1

            # Seçili sayfa (active page) daha büyükse onu kullan
            try:
                selected_page = self.driver.find_element(
                    By.CSS_SELECTOR, "span[aria-current='page']"
                )
                selected_num = int(selected_page.text)
                max_page = max(max_page, selected_num)
            except Exception:  # nosec
                pass

            logger.info(f"Max pages found: {max_page}")
            return max_page

        except Exception as e:
            logger.error(f"Error getting max pages: {e}")
            return 1

    # Emlakjet sayfalama limiti: 50 sayfa x 30 ilan = 1500 ilan
    PAGINATION_LIMIT = 1500

    def _parse_listing_count(self) -> int:
        """Zaten yüklenmiş sayfadan ilan sayısını parse et"""
        try:
            # Yeni yapı: meta description "N adet ... ilanı" bilgisi içerir
            try:
                import re as _re

                meta = self.driver.find_element(
                    By.CSS_SELECTOR, "meta[name='description']"
                )
                meta_content = meta.get_attribute("content") or ""
                match = _re.search(r"(\d[\d\.]*)\s*adet", meta_content)
                if match:
                    return int(_re.sub(r"[^\d]", "", match.group(1)))
            except Exception:  # nosec
                pass

            # Yeni yapı: başlık altındaki ilan sayısı
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "p.text-body span.font-semibold"
            )
            if count_element:
                text = count_element[0].text.strip().replace(".", "").replace(",", "")
                if text.isdigit():
                    return int(text)

            # "uygun ilan bulunamadı" kontrolü
            no_results = self.driver.find_elements(
                By.CSS_SELECTOR, "span.styles_adsCount__A1YW5"
            )
            for el in no_results:
                if "bulunamadı" in el.text.lower():
                    return 0

            # İlan sayısını çek (eski yapı)
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR,
                "span.styles_adsCount__A1YW5 strong.styles_strong__cw1jn",
            )
            if count_element:
                text = count_element[0].text.strip().replace(".", "").replace(",", "")
                return int(text) if text.isdigit() else 0

            # Alternatif seçici (eski yapı)
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "strong.styles_strong__cw1jn"
            )
            if count_element:
                text = count_element[0].text.strip().replace(".", "").replace(",", "")
                return int(text) if text.isdigit() else 0

            return 0
        except Exception:
            return 0

    def get_listing_count(self, url: str) -> int:
        """URL'ye giderek toplam ilan sayısını al"""
        try:
            self.driver.get(url)
            self.random_medium_wait()
            return self._parse_listing_count()
        except Exception:
            return 0

    def select_provinces(
        self,
        api_indices: list[int] | None = None,
        provinces: list[dict] | None = None,
    ) -> list[dict]:
        """Taranacak illeri seç"""
        print("\n🏙️  İL SEÇİMİ")
        if provinces is None:
            provinces, _ = self.get_location_options("İller", self.base_url)
        if not provinces:
            print("❌ İl bulunamadı!")
            return []

        if api_indices:
            selected = [
                provinces[i - 1] for i in api_indices if 0 < i <= len(provinces)
            ]
            if selected:
                print(f"\n✅ API: {len(selected)} il seçildi")
                return selected
            # Geçersiz indeksler için yedek
            return []

        print("\n🎯 ÇOKLU İL SEÇİMİ")
        print("Birden fazla seçim için: 1,3,5 veya 1-5")

        while True:
            user_input = input(
                f"\nİl numaralarını girin (1-{len(provinces)}): "
            ).strip()
            if not user_input:
                print("❌ Boş giriş!")
                continue

            selections = self._parse_selection_input(user_input, len(provinces))
            if selections:
                selected = [provinces[i - 1] for i in selections]
                print(f"\n✅ {len(selected)} il seçildi:")
                for p in selected:
                    print(f"   - {p['name']}")
                return selected
            else:
                print("❌ Geçersiz seçim!")

    def select_districts_for_province(
        self,
        province: dict,
        api_mode: bool = False,
        api_districts: list[str] | None = None,
    ) -> tuple:
        """Belirli bir il için ilçeleri seç"""
        print(f"\n🏘️  {province['name']} İLÇELERİ")
        districts, _ = self.get_location_options("İlçeler", province["url"])

        if not districts:
            print(f"❌ {province['name']} için ilçe bulunamadı!")
            return ([province], False)  # İlçe yoksa ilin kendisini döndür

        if api_mode:
            # API modunda, isimle belirtilen ilçeler varsa eşleştir
            if api_districts:
                normalized_districts = {
                    _normalize_location_token(name) for name in api_districts
                }
                selected = [
                    d
                    for d in districts
                    if _normalize_location_token(d["name"]) in normalized_districts
                ]
                if selected:
                    for d in selected:
                        d["il"] = province["name"]
                    return (selected, True)
                return ([], False)

            # API modunda ilçe belirtilmemişse tümünü tara
            for d in districts:
                d["il"] = province["name"]
            return (districts, True)

        print("\n1. Tüm ilçeleri tara (her ilçe için mahalle seç)")
        print("2. Tüm ili direkt tara (ilçe/mahalle seçimi yapma)")
        print("3. Belirli ilçeleri seç")
        print("4. Bu ili atla")

        choice = self.get_user_choice(4)

        if choice == 1:
            for d in districts:
                d["il"] = province["name"]
            return (districts, True)
        elif choice == 2:
            return ([province], False)
        elif choice == 4:
            return ([], False)

        # Belirli ilçeleri seç
        print("\n🎯 İLÇE SEÇİMİ (örn: 1,3,5 veya 1-5)")
        user_input = input(f"İlçe numaralarını girin (1-{len(districts)}): ").strip()

        selections = self._parse_selection_input(user_input, len(districts))
        if selections:
            selected = [districts[i - 1] for i in selections]
            for d in selected:
                d["il"] = province["name"]
            print(f"✅ {len(selected)} ilçe seçildi")
            return (selected, True)
        else:
            return ([province], False)

    def select_neighborhoods_for_district(
        self, district: dict, api_mode: bool = False
    ) -> list[dict]:
        """Belirli bir ilçe için mahalleleri seç"""
        province_name = district.get("il", "")
        district_name = district["name"]

        print(f"\n🏡 {province_name} / {district_name} MAHALLELERİ")
        neighborhoods, _ = self.get_location_options("Mahalleler", district["url"])

        if not neighborhoods:
            return [district]  # Mahalle yoksa ilçenin kendisini döndür

        if api_mode:
            for n in neighborhoods:
                n["il"] = province_name
                n["ilce"] = district_name
            return neighborhoods

        print("\n1. Tüm mahalleleri tara")
        print("2. Mahalle seç")
        print("3. Bu ilçeyi atla")

        choice = self.get_user_choice(3)

        if choice == 1:
            return [district]
        elif choice == 3:
            return []

        # Belirli mahalleleri seç
        print("\n🎯 MAHALLE SEÇİMİ (örn: 1,3,5 veya 1-5)")
        user_input = input(
            f"Mahalle numaralarını girin (1-{len(neighborhoods)}): "
        ).strip()

        selections = self._parse_selection_input(user_input, len(neighborhoods))
        if selections:
            selected = [neighborhoods[i - 1] for i in selections]
            for n in selected:
                n["il"] = province_name
                n["ilce"] = district_name
            print(f"✅ {len(selected)} mahalle seçildi")
            return selected
        else:
            return [district]

    def _is_listing_limit_reached(self) -> bool:
        """Maksimum ilan limitine ulaşılıp ulaşılmadığını kontrol et"""
        return self._max_listings > 0 and len(self.all_listings) >= self._max_listings

    def _make_page_callback(
        self,
        prov_name: str,
        dist_name: str,
        tgt: dict,
        page_num_ref: list[int],
        new_listings_count_ref: list[int],
    ):
        """Her sayfa sonrası ilanları DB'ye kaydetmek için callback oluştur"""

        def _on_page_scraped(page_listings):
            for listing in page_listings:
                listing["il"] = prov_name
                if tgt["type"] == "mahalle":
                    listing["ilce"] = dist_name
                    listing["mahalle"] = tgt["label"].split("/")[-1].strip()
                elif tgt["type"] == "ilce":
                    listing["ilce"] = dist_name

            if self.db:
                new_count, updated_count, unchanged_count = save_listings_to_db(
                    self.db,
                    page_listings,
                    platform="emlakjet",
                    kategori=self.category,
                    ilan_tipi=self.listing_type,
                    alt_kategori=self.subtype_name,
                    scrape_session_id=self.scrape_session_id,
                    log_db_save=False,
                )
                page_num_ref[0] += 1
                new_listings_count_ref[0] += new_count  # Yeni eklenenleri say
                self._log_page_result(
                    page_num_ref[0],
                    len(page_listings),
                    new_count,
                    updated_count,
                    unchanged_count,
                )

        return _on_page_scraped

    def scrape_pages(
        self,
        target_url: str,
        max_pages: int,
        on_page_scraped=None,
        location_label: str = "",
        province: str = "",
        district: str = "",
        new_listings_count_ref: list[int] | None = None,
    ) -> bool:
        """Başarısız sayfa takibi ile sayfa tarama"""
        first_page_count = 0

        for current_page in range(1, max_pages + 1):
            if (
                hasattr(self, "_max_listings")
                and self._max_listings > 0
                and len(self.all_listings) >= self._max_listings
            ):
                task_log.line(
                    f"İlan limitine ulaşıldı ({self._max_listings}), sayfa tarama sonlandırılıyor",
                    level="warning",
                )
                break

            self._log_page_start(
                location_label or province or district or "Lokasyon",
                current_page,
                max_pages,
            )

            try:
                if current_page > 1:
                    separator = "&" if "?" in target_url else "?"
                    page_url = f"{target_url}{separator}sayfa={current_page}"
                else:
                    page_url = target_url

                self.driver.get(page_url)
                time.sleep(self.config.wait_between_pages)

                # Sıfır ilan kontrolü (ilk sayfa)
                if current_page == 1:
                    try:
                        no_results = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            "span.styles_title__e_y3h, [class*='no-result'], [class*='empty-state']",
                        )
                        for element in no_results:
                            if "ilan bulunamadı" in element.text.lower():
                                task_log.line(
                                    "⚠️ Bu lokasyonda ilan bulunamadı, atlanıyor...",
                                    level="warning",
                                )
                                return True
                    except Exception:  # nosec
                        pass

                listings = self.scrape_current_page()

                # 0 ilan bulunduysa ve ilk sayfa değilse → failed page olarak kaydet
                if len(listings) == 0 and current_page > 1:
                    task_log.line(
                        f"   ⚠️ Sayfa {current_page}'de 0 ilan - retry listesine eklendi",
                        level="warning",
                    )
                    failed_pages_tracker.add_failed_page(
                        FailedPageInfo(
                            url=page_url,
                            page_number=current_page,
                            city=province,
                            district=district,
                            error="0 listings found on page",
                            max_pages=max_pages,
                            listing_type=self.listing_type or "",
                            category=self.category or "",
                            subtype_path=self.subtype_path,
                        )
                    )
                else:
                    self.all_listings.extend(listings)

                    # Sadece yeni eklenenleri saymak için
                    if on_page_scraped and listings:
                        on_page_scraped(listings)
                    elif listings:
                        self._log_page_result(current_page, len(listings), 0, 0, 0)

                if current_page == 1:
                    first_page_count = len(listings)

            except Exception as e:
                task_log.line(f"Error scraping page {current_page}: {e}", level="error")
                task_log.line(
                    f"   ⚠️ Sayfa {current_page} yüklenemedi - retry listesine eklendi",
                    level="warning",
                )
                # Sayfa yükleme hatası → başarısız sayfa
                page_url = (
                    target_url
                    if current_page == 1
                    else f"{target_url}{'&' if '?' in target_url else '?'}sayfa={current_page}"
                )
                failed_pages_tracker.add_failed_page(
                    FailedPageInfo(
                        url=page_url,
                        page_number=current_page,
                        city=province,
                        district=district,
                        error=str(e),
                        max_pages=max_pages,
                        listing_type=self.listing_type or "",
                        category=self.category or "",
                        subtype_path=self.subtype_path,
                    )
                )
                continue

        return first_page_count == 0 and max_pages == 1

    def _scrape_target(
        self, target: dict, province_name: str, district_name: str
    ) -> tuple[bool, int]:
        """Tek bir hedefi (il/ilçe/mahalle) tara"""
        print = task_log.line
        url_max_pages = self.get_max_pages(target["url"])
        requested = getattr(self, "_requested_max_pages", None)
        if requested and requested > 0:
            url_max_pages = min(url_max_pages, requested)
        self._log_location_start(target["label"], target["url"])
        self._log_location_plan(target["label"], url_max_pages)
        print(f"📊 {url_max_pages} sayfa taranacak.")

        page_num_ref = [
            0
        ]  # Callback içinde sayfa sayacı için değiştirilebilir referans
        new_listings_count_ref = [0]  # Yeni eklenen ilan sayacı
        page_callback = self._make_page_callback(
            province_name, district_name, target, page_num_ref, new_listings_count_ref
        )
        should_skip = self.scrape_pages(
            target["url"],
            url_max_pages,
            on_page_scraped=page_callback,
            location_label=target["label"],
            province=province_name,
            district=district_name,
            new_listings_count_ref=new_listings_count_ref,
        )
        # Global kümülatif sayaça ekle
        self.total_new_listings += new_listings_count_ref[0]
        logger.warning(f"📊 EmlakJet Kümülatif Toplam: {self.total_new_listings} ilan")
        if not should_skip:
            self._log_location_complete(target["label"], new_listings_count_ref[0])
        return should_skip, new_listings_count_ref[0]

    def start_scraping_api(
        self,
        cities: list[str] | None = None,
        districts: dict[str, list[str]] | None = None,
        max_listings: int = 0,
        max_pages: int | None = None,
        progress_callback=None,
    ):
        """İki katmanlı optimizasyonla API tarama giriş noktası"""
        print = task_log.line
        self._max_listings = max_listings
        self._requested_max_pages = max_pages

        subtype_info = f" ({self.subtype_name})" if self.subtype_name else ""
        if max_pages:
            limit_info = f" (limit: {max_pages} sayfa)"
        elif max_listings > 0:
            limit_info = f" (limit: {max_listings} ilan)"
        else:
            limit_info = " (tüm sayfalar)"
        print(
            f"\n🚀 API: EmlakJet {self.listing_type.capitalize()} {self.category.capitalize()}{subtype_info} Scraper başlatılıyor{limit_info}"
        )

        if progress_callback:
            progress_callback(
                f"{self.category.capitalize()}{subtype_info} taraması başlatılıyor...",
                0,
                100,
                0,
            )

        try:
            # subtype_path varsa onu kullan, yoksa base_url
            start_url = self.base_url
            if self.subtype_path:
                start_url = f"https://www.emlakjet.com{self.subtype_path}"
                print(f"📋 Alt kategori kullanılıyor: {self.subtype_path}")

            print("İl listesi alınıyor...")
            all_provinces, _ = self.get_location_options("İller", start_url)

            # Adım 1: İlleri seç
            if cities:
                provinces = []
                seen = set()
                for city in cities:
                    matched = [
                        p
                        for p in all_provinces
                        if _normalize_location_token(p["name"])
                        == _normalize_location_token(city)
                    ]
                    if not matched:
                        matched = [
                            {
                                "name": city,
                                "url": build_city_url(
                                    city,
                                    base_url=start_url,
                                    site_base=self.emlakjet_config.base_url,
                                    subtype_path=self.subtype_path,
                                ),
                            }
                        ]
                        logger.info(
                            "Il listesinde yok, URL ile devam: %s -> %s",
                            city,
                            matched[0]["url"],
                        )
                    for province in matched:
                        key = _normalize_location_token(province["name"])
                        if key in seen:
                            continue
                        seen.add(key)
                        provinces.append(province)
                if not provinces:
                    logger.error(f"Şehirler için eşleşen il bulunamadı: {cities}")
                    return
            else:
                logger.error("API taraması için şehir belirtilmedi")
                return

            # Adım 2: Her ili optimizasyonla işle
            stopped = False
            scrape_stats = {}  # {il_adı: {ilçe_adı: ilan_sayısı}} — özet rapor için
            for prov_idx, province in enumerate(provinces, 1):
                if self._is_listing_limit_reached():
                    stopped = True
                    break

                # İl sayfasına git ve ilan sayısını al (get_listing_count sayfayı yükler)
                province_count = self.get_listing_count(province["url"])

                print("\n" + "=" * 70)
                print(
                    f"🏙️  İL {prov_idx}/{len(provinces)}: {province['name']} (Toplam İlan: {province_count})"
                )
                print("=" * 70)

                if progress_callback:
                    base_progress = ((prov_idx - 1) / len(provinces)) * 100
                    progress_callback(
                        f"İşleniyor: {province['name']}...",
                        prov_idx,
                        len(provinces),
                        base_progress,
                    )

                # ── OPTİMİZASYON: İl seviyesi kontrol ──
                if province_count == 0:
                    print(f"⏭️  {province['name']} → 0 ilan, il atlanıyor.")
                    if progress_callback:
                        progress_callback(
                            f"{province['name']} atlandı (0 ilan)",
                            prov_idx,
                            len(provinces),
                            int((prov_idx / len(provinces)) * 100),
                        )
                    continue

                province_name = province["name"]
                api_districts_for_province = None
                if districts:
                    normalized_province_name = _normalize_location_token(province_name)
                    for city_name, district_names in districts.items():
                        if (
                            _normalize_location_token(city_name)
                            == normalized_province_name
                            and district_names
                        ):
                            api_districts_for_province = district_names
                            break

                if should_scrape_city_level(
                    max_pages,
                    province_count,
                    has_district_filter=bool(api_districts_for_province),
                    pagination_limit=self.PAGINATION_LIMIT,
                ):
                    print(
                        f"⚡ {province['name']} → {province_count} ilan, il seviyesinden taranıyor."
                    )
                    target = {
                        "url": province["url"],
                        "label": province["name"],
                        "type": "il",
                    }
                    print(f"\n📍 Taranıyor: {target['label']}")
                    should_skip, new_count = self._scrape_target(
                        target, province["name"], province["name"]
                    )
                    if should_skip:
                        print("⏭️  Bu lokasyon atlandı.")
                    else:
                        print(f"   📦 Toplam: {new_count} yeni ilan toplandı")
                        scrape_stats[province["name"]] = {"(il seviyesi)": new_count}

                    if progress_callback:
                        overall = (prov_idx / len(provinces)) * 100
                        progress_callback(
                            f"{province['name']} (il seviyesi)",
                            prov_idx,
                            len(provinces),
                            min(int(overall), 99),
                            unit="şehir",
                        )
                    continue

                print(
                    f"📊 {province['name']} → {province_count} ilan, ilçe seviyesine iniliyor..."
                )

                # İlçe listesini al
                district_list, _ = self.get_location_options("İlçeler", province["url"])

                if not district_list:
                    print(f"⏭️  {province['name']} ilçe bulunamadı, atlanıyor.")
                    continue

                # İlçe filtresi uygula
                if api_districts_for_province:
                    normalized_districts = {
                        _normalize_location_token(name)
                        for name in api_districts_for_province
                    }
                    district_list = [
                        d
                        for d in district_list
                        if _normalize_location_token(d["name"]) in normalized_districts
                    ]
                    if not district_list:
                        print(f"⏭️  {province['name']} için eşleşen ilçe bulunamadı.")
                        continue

                for d in district_list:
                    d["il"] = province_name

                # Her ilçeyi işle
                for dist_idx, district in enumerate(district_list, 1):
                    if self._is_listing_limit_reached():
                        stopped = True
                        break

                    # İlçe sayfasına git ve ilan sayısını al
                    district_count = self.get_listing_count(district["url"])

                    print(
                        f"\n📍 İlçe {dist_idx}/{len(district_list)}: {district['name']} (İlan: {district_count})"
                    )

                    # ── OPTİMİZASYON: İlçe seviyesi kontrol ──
                    if district_count == 0:
                        print(f"⏭️  {district['name']} → 0 ilan, ilçe atlanıyor.")
                        continue

                    if district_count <= self.PAGINATION_LIMIT:
                        # İlçede ≤1500 ilan — mahalleye inmeye gerek yok
                        print(
                            f"⚡ {district['name']} → {district_count} ilan (≤{self.PAGINATION_LIMIT}), ilçe seviyesinden taranıyor."
                        )
                        target = {
                            "url": district["url"],
                            "label": f"{province_name} / {district['name']}",
                            "type": "ilce",
                        }
                        print(f"\n📍 Taranıyor: {target['label']}")
                        should_skip, new_count = self._scrape_target(
                            target, province_name, district["name"]
                        )

                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(district_list), 1)
                            overall = province_base + dist_idx * district_range
                            progress_callback(
                                f"{province_name} > {district['name']}",
                                dist_idx,
                                len(district_list),
                                min(int(overall), 99),
                                unit="ilçe",
                            )

                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {new_count} yeni ilan toplandı")
                            scrape_stats.setdefault(province_name, {})[
                                district["name"]
                            ] = new_count
                        continue

                    # İlçe > 1500 ilan — mahallelere iniyoruz
                    print(
                        f"📊 {district['name']} → {district_count} ilan (>{self.PAGINATION_LIMIT}), mahalle seviyesine iniliyor..."
                    )

                    neighborhoods, _ = self.get_location_options(
                        "Mahalleler", district["url"]
                    )

                    if not neighborhoods:
                        # Mahalle bulunamadı — ilçe seviyesinden tara
                        target = {
                            "url": district["url"],
                            "label": f"{province_name} / {district['name']}",
                            "type": "ilce",
                        }
                        print(
                            f"\n📍 Mahalle bulunamadı, ilçe seviyesinden taranıyor: {target['label']}"
                        )
                        should_skip, new_count = self._scrape_target(
                            target, province_name, district["name"]
                        )
                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {new_count} yeni ilan toplandı")
                        continue

                    for n in neighborhoods:
                        n["il"] = province_name
                        n["ilce"] = district["name"]

                    targets = [
                        {
                            "url": n["url"],
                            "label": f"{n.get('il', '')} / {n.get('ilce', '')} / {n['name']}",
                            "type": "mahalle",
                        }
                        for n in neighborhoods
                    ]

                    total_targets = len(targets)
                    for target_idx, target in enumerate(targets, 1):
                        if self._is_listing_limit_reached():
                            stopped = True
                            break

                        print(
                            f"\n📍 Taranıyor: {target['label']} ({target_idx}/{total_targets})"
                        )
                        should_skip, new_count = self._scrape_target(
                            target, province_name, district["name"]
                        )

                        # Mahalle bazlı istatistikler — ilçe altında topla
                        if new_count > 0:
                            scrape_stats.setdefault(province_name, {})
                            scrape_stats[province_name][district["name"]] = (
                                scrape_stats[province_name].get(district["name"], 0)
                                + new_count
                            )

                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(district_list), 1)
                            target_range = district_range / max(total_targets, 1)
                            overall = (
                                province_base
                                + (dist_idx - 1) * district_range
                                + target_idx * target_range
                            )
                            progress_callback(
                                f"{province_name} > {district['name']} > {target['label'].split('/')[-1].strip()}",
                                target_idx,
                                total_targets,
                                min(int(overall), 99),
                            )

                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {new_count} yeni ilan toplandı")

                    if stopped:
                        break
                if stopped:
                    break

            if self._is_listing_limit_reached():
                print(
                    f"\n🎯 İlan limitine ulaşıldı: {len(self.all_listings)} / {self._max_listings}"
                )

            # ── HİYERARŞİK ÖZET RAPOR ──
            print(f"\n{'=' * 70}")
            if stopped and self._is_listing_limit_reached():
                print("⚠️  ERKEN DURDURULDU")
                logger.warning(
                    f"⚠️ Tarama erken durduruldu: {self.total_new_listings} yeni ilan"
                )
            elif self.all_listings:
                print("✅ TARAMA BAŞARIYLA TAMAMLANDI")
                logger.info(
                    f"✅ Tarama tamamlandı: {self.total_new_listings} yeni ilan"
                )
            else:
                print("❌ HİÇ İLAN BULUNAMADI")
                logger.warning("⚠️ Hiç ilan bulunamadı")

            if scrape_stats:
                print(f"📊 Taranan İl Sayısı: {len(scrape_stats)}")
                print(f"📊 Toplam Yeni İlan Sayısı: {self.total_new_listings}")
                for city, districts_data in scrape_stats.items():
                    city_total = sum(districts_data.values())
                    print(
                        f"   • {city}: {city_total} ilan ({len(districts_data)} ilçe/bölge)"
                    )
                    for district_name, count in districts_data.items():
                        print(f"      - {district_name}: {count} ilan")
            print("=" * 70)

            # ── RETRY MEKANİZMASI ──
            max_retries = 3
            retry_round = 0
            successful_retries = 0

            while failed_pages_tracker.has_failed_pages() and retry_round < max_retries:
                retry_round += 1
                failed_pages = failed_pages_tracker.get_unretried(
                    max_retry_count=max_retries
                )

                if not failed_pages:
                    break

                print(f"\n{'=' * 70}")
                print(f"🔄 YENİDEN DENEME #{retry_round}/{max_retries}")
                print(f"📊 {len(failed_pages)} başarısız sayfa tekrar taranacak")
                print("=" * 70)

                if progress_callback:
                    progress_callback(
                        f"Yeniden deneme #{retry_round} - {len(failed_pages)} sayfa",
                        0,
                        len(failed_pages),
                    )

                for idx, page_info in enumerate(failed_pages, 1):
                    print(
                        f"\n🔄 [{idx}/{len(failed_pages)}] {page_info.city}/{page_info.district or 'tüm'} - Sayfa {page_info.page_number}"
                    )

                    if progress_callback:
                        progress_callback(
                            f"Yeniden deneme #{retry_round}: {page_info.city} Sayfa {page_info.page_number}",
                            idx,
                            len(failed_pages),
                        )

                    try:
                        retry_manager = DriverManager()
                        retry_driver = retry_manager.start()

                        try:
                            print(f"   🌐 {page_info.url}")
                            retry_driver.get(page_info.url)
                            time.sleep(self.config.wait_between_pages + 1)

                            listings = extract_listings_from_html(
                                retry_driver.page_source,
                                page_url=retry_driver.current_url,
                                category=self.category,
                                city=page_info.city,
                                district=page_info.district,
                                scraping_method="selenium",
                            )

                            if listings:
                                print(f"   ✅ {len(listings)} ilan bulundu!")
                                self.all_listings.extend(listings)
                                if self.db:
                                    save_listings_to_db(
                                        self.db,
                                        listings,
                                        platform="emlakjet",
                                        kategori=self.category,
                                        ilan_tipi=self.listing_type,
                                        alt_kategori=self.subtype_name,
                                        scrape_session_id=self.scrape_session_id,
                                        log_db_save=False,
                                    )
                                failed_pages_tracker.mark_as_success(
                                    page_info.city,
                                    page_info.district,
                                    page_info.page_number,
                                )
                                successful_retries += 1
                            else:
                                print("   ⚠️ 0 ilan - devam ediliyor")
                                failed_pages_tracker.increment_retry_count(
                                    page_info.city,
                                    page_info.district,
                                    page_info.page_number,
                                )
                        finally:
                            retry_manager.stop()

                    except Exception as e:
                        logger.error(f"Retry hatası: {e}")
                        failed_pages_tracker.increment_retry_count(
                            page_info.city, page_info.district, page_info.page_number
                        )

                    time.sleep(random.SystemRandom().uniform(1, 2))

            # Yeniden deneme özeti
            summary = failed_pages_tracker.get_summary()
            if summary["failed_count"] > 0 or successful_retries > 0:
                print(f"\n{'=' * 70}")
                print("📊 RETRY ÖZETİ")
                print(f"   ✅ Başarılı retry: {successful_retries}")
                print(f"   ❌ Kalan başarısız: {summary['failed_count']}")
                print("=" * 70)

                if summary["failed_count"] > 0:
                    logger.warning(
                        f"⚠️ {summary['failed_count']} sayfa retry sonrası hala başarısız"
                    )
                    for fp in summary["failed_pages"]:
                        logger.warning(
                            f"   - {fp['city']}/{fp['district'] or 'tüm'} Sayfa {fp['page_number']}: {fp['error']}"
                        )

        except Exception as e:
            logger.error(f"API tarama hatası: {e}")
            raise
