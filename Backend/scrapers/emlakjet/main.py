# -*- coding: utf-8 -*-
"""EmlakJet Ana Scraper - gizli mod"""

import time
import random
import unicodedata
from typing import Dict, List, Any, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_scraper import BaseScraper
from core.driver_manager import DriverManager
from core.selectors import get_selectors, get_common_selectors
from core.config import get_emlakjet_config
from core.failed_pages_tracker import FailedPagesTracker, FailedPageInfo, failed_pages_tracker
from utils.logger import get_logger
from utils.data_exporter import DataExporter

from .parsers import KonutParser, ArsaParser, IsyeriParser, TuristikTesisParser

logger = get_logger(__name__)


class EmlakJetScraper(BaseScraper):
    """EmlakJet platformu ana scraper sınıfı"""
    
    CATEGORY_PARSERS = {
        'konut': KonutParser,
        'arsa': ArsaParser,
        'isyeri': IsyeriParser,
        'turistik_tesis': TuristikTesisParser,
        'kat_karsiligi_arsa': ArsaParser,  # Arsa parser'ı kullanır
        'devren_isyeri': IsyeriParser,     # İşyeri parser'ı kullanır
        'gunluk_kiralik': KonutParser,     # Konut parser'ı kullanır
    }
    
    def __init__(
        self,
        driver: WebDriver,
        base_url: str = "https://www.emlakjet.com",
        category: str = "konut",
        selected_locations: Optional[Dict] = None,
        listing_type: Optional[str] = None,  # satilik/kiralik
        subtype_path: Optional[str] = None  # Alt kategori URL path'i (örn: /satilik-daire)
    ):
        super().__init__(driver, base_url, "emlakjet", category, selected_locations)

        self.emlakjet_config = get_emlakjet_config()
        self.listing_type = listing_type
        self.subtype_path = subtype_path

        # Alt kategori adını çıkar
        subtype_name = None
        if subtype_path:
            # /satilik-daire -> daire
            path_part = subtype_path.strip('/').split('-')
            if len(path_part) >= 2:
                subtype_name = path_part[-1].replace('-', '_')

        # Hiyerarşik klasör yapısı: Outputs/EmlakJet Output/{listing_type}/{category}/{subtype}/
        self.exporter = DataExporter(
            output_dir="Outputs/EmlakJet Output",
            listing_type=listing_type,
            category=category,
            subtype=subtype_name
        )

        # Uygun parser'ı başlat
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Kategori parser'ı ile ilan verisini çıkar"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Kategori parser'ı ile detayları parse et"""
        return self.parser.parse_category_details(quick_info, title)
    
    @property
    def subtype_name(self) -> Optional[str]:
        """Dosya adlandırma için subtype_path'inden alt kategori adını çıkar"""
        if self.subtype_path:
            # /satilik-daire -> daire
            path_part = self.subtype_path.strip('/').split('-')
            if len(path_part) >= 2:
                return path_part[-1].replace('-', '_')
        return None

    def get_file_prefix(self) -> str:
        """Alt kategori varsa dosya öneki oluştur"""
        if self.subtype_name:
            return f"emlakjet_{self.listing_type}_{self.category}_{self.subtype_name}"
        return f"emlakjet_{self.listing_type}_{self.category}"

    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """Mevcut sayfadaki tüm ilanları tara"""
        from datetime import datetime

        listings = []
        try:
            container_selector = self.common_selectors.get("listing_container")
            if not container_selector:
                logger.error("No listing_container selector defined")
                return []

            containers = self.find_elements_safe(container_selector)

            # EmlakJet: "Benzer İlanlar" bölümündeki kartları hariç tut
            if containers:
                filtered = []
                for c in containers:
                    try:
                        is_similar = self.driver.execute_script(
                            "return arguments[0].closest('[class*=\"similarListing\"], [class*=\"similarlisting\"]') !== null;", c
                        )
                        if not is_similar:
                            filtered.append(c)
                    except Exception:
                        filtered.append(c)
                if len(filtered) < len(containers):
                    logger.info(f"Filtered out {len(containers) - len(filtered)} 'Benzer İlanlar' listings")
                containers = filtered

            print(f"   🔍 {len(containers)} ilan elementi bulundu")

            for container in containers:
                try:
                    data = self.extract_listing_data(container)
                    if data:
                        data['tarih'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        listings.append(data)
                except Exception as e:
                    logger.warning(f"İlan çıkarma hatası: {e}")
                    continue

            print(f"   ✓ {len(listings)} ilan başarıyla parse edildi")

        except Exception as e:
            logger.error(f"Sayfa tarama hatası: {e}")

        return listings

    def get_location_options(self, location_type: str, current_url: str) -> tuple:
        """Mevcut sayfadan lokasyon seçeneklerini ve ilan sayısını al"""
        try:
            logger.info(f"Getting {location_type} options...")

            self.driver.get(current_url)
            self.random_long_wait()  # Gizli mod: lokasyon listesi

            # Sayfa zaten yüklü — ilan sayısını da aynı anda al
            listing_count = self._parse_listing_count()

            location_options = []
            location_selector = self.common_selectors.get("location_links")

            location_links = self.driver.find_elements(By.CSS_SELECTOR, location_selector)

            for link in location_links:
                try:
                    location_name = link.text.strip().split()[0]
                    location_url = link.get_attribute("href")

                    if location_name and location_url:
                        location_options.append({
                            'name': location_name,
                            'url': location_url
                        })
                except Exception:
                    continue

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
                            name = location_options[idx]['name'][:col_width - 4]
                            row += f"{idx + 1:2d}. {name:<{col_width - 4}}"
                    print(row)

                print(f"\nToplam {len(location_options)} {location_type.lower()} bulundu.")

            return location_options, listing_count

        except Exception as e:
            logger.error(f"Error getting {location_type} options: {e}")
            return [], 0
    
    def get_max_pages(self, target_url: Optional[str] = None) -> int:
        """URL için yeniden deneme ile maksimum sayfa sayısını al"""
        max_retries = 3

        try:
            if target_url:
                self.driver.get(target_url)
                self.random_medium_wait()  # Gizli mod

            pagination_sel = self.common_selectors.get("pagination_list")
            active_sel = self.common_selectors.get("active_page")

            for retry in range(max_retries):
                pagination = self.driver.find_elements(By.CSS_SELECTOR, pagination_sel)

                if pagination:
                    print(f"✓ Pagination bulundu: {len(pagination)} link")
                    break

                if retry < max_retries - 1:
                    print(f"⚠️ Pagination bulunamadı, tekrar deneniyor... ({retry + 1}/{max_retries})")
                    time.sleep(2)
                else:
                    print(f"⚠️ Pagination bulunamadı - tek sayfa varsayılıyor")
                    return 1

            page_numbers = []
            for item in pagination:
                try:
                    active_page = item.find_element(By.CSS_SELECTOR, active_sel)
                    page_numbers.append(int(active_page.text))
                except:
                    pass

                try:
                    page_link = item.find_element(By.CSS_SELECTOR, "a")
                    page_text = page_link.text
                    if page_text.isdigit():
                        page_numbers.append(int(page_text))
                except:
                    pass

            max_page = max(page_numbers) if page_numbers else 1
            return max_page

        except Exception as e:
            logger.error(f"Error getting max pages: {e}")
            return 1
    
    # Emlakjet sayfalama limiti: 50 sayfa x 30 ilan = 1500 ilan
    PAGINATION_LIMIT = 1500

    def _parse_listing_count(self) -> int:
        """Zaten yüklenmiş sayfadan ilan sayısını parse et"""
        try:
            # "uygun ilan bulunamadı" kontrolü
            no_results = self.driver.find_elements(
                By.CSS_SELECTOR, "span.styles_adsCount__A1YW5"
            )
            for el in no_results:
                if "bulunamadı" in el.text.lower():
                    return 0

            # İlan sayısını çek
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "span.styles_adsCount__A1YW5 strong.styles_strong__cw1jn"
            )
            if count_element:
                text = count_element[0].text.strip().replace('.', '').replace(',', '')
                return int(text) if text.isdigit() else 0

            # Alternatif seçici
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "strong.styles_strong__cw1jn"
            )
            if count_element:
                text = count_element[0].text.strip().replace('.', '').replace(',', '')
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
    
    def select_provinces(self, api_indices: Optional[List[int]] = None, provinces: Optional[List[Dict]] = None) -> List[Dict]:
        """Taranacak illeri seç"""
        print(f"\n🏙️  İL SEÇİMİ")
        if provinces is None:
            provinces, _ = self.get_location_options("İller", self.base_url)
        if not provinces:
            print("❌ İl bulunamadı!")
            return []

        if api_indices:
             selected = [provinces[i - 1] for i in api_indices if 0 < i <= len(provinces)]
             if selected:
                 print(f"\n✅ API: {len(selected)} il seçildi")
                 return selected
             # Geçersiz indeksler için yedek
             return []

        print("\n🎯 ÇOKLU İL SEÇİMİ")
        print("Birden fazla seçim için: 1,3,5 veya 1-5")

        while True:
            user_input = input(f"\nİl numaralarını girin (1-{len(provinces)}): ").strip()
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
    
    def select_districts_for_province(self, province: Dict, api_mode: bool = False, api_districts: Optional[List[str]] = None) -> tuple:
        """Belirli bir il için ilçeleri seç"""
        print(f"\n🏘️  {province['name']} İLÇELERİ")
        districts, _ = self.get_location_options("İlçeler", province['url'])

        if not districts:
            print(f"❌ {province['name']} için ilçe bulunamadı!")
            return ([province], False)  # İlçe yoksa ilin kendisini döndür

        if api_mode:
            # API modunda, isimle belirtilen ilçeler varsa eşleştir
            if api_districts:
                selected = [d for d in districts if d['name'] in api_districts]
                if selected:
                    for d in selected:
                        d['il'] = province['name']
                    return (selected, True)
                return ([], False)

            # API modunda ilçe belirtilmemişse tümünü tara
            for d in districts:
                d['il'] = province['name']
            return (districts, True)

        print("\n1. Tüm ilçeleri tara (her ilçe için mahalle seç)")
        print("2. Tüm ili direkt tara (ilçe/mahalle seçimi yapma)")
        print("3. Belirli ilçeleri seç")
        print("4. Bu ili atla")

        choice = self.get_user_choice(4)

        if choice == 1:
            for d in districts:
                d['il'] = province['name']
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
                d['il'] = province['name']
            print(f"✅ {len(selected)} ilçe seçildi")
            return (selected, True)
        else:
            return ([province], False)
    
    def select_neighborhoods_for_district(self, district: Dict, api_mode: bool = False) -> List[Dict]:
        """Belirli bir ilçe için mahalleleri seç"""
        province_name = district.get('il', '')
        district_name = district['name']

        print(f"\n🏡 {province_name} / {district_name} MAHALLELERİ")
        neighborhoods, _ = self.get_location_options("Mahalleler", district['url'])

        if not neighborhoods:
            return [district]  # Mahalle yoksa ilçenin kendisini döndür

        if api_mode:
            for n in neighborhoods:
                n['il'] = province_name
                n['ilce'] = district_name
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
        user_input = input(f"Mahalle numaralarını girin (1-{len(neighborhoods)}): ").strip()

        selections = self._parse_selection_input(user_input, len(neighborhoods))
        if selections:
            selected = [neighborhoods[i - 1] for i in selections]
            for n in selected:
                n['il'] = province_name
                n['ilce'] = district_name
            print(f"✅ {len(selected)} mahalle seçildi")
            return selected
        else:
            return [district]
    
    def _is_stop_requested(self) -> bool:
        """Durdurma isteği olup olmadığını kontrol et"""
        return self._stop_checker is not None and self._stop_checker()

    def _is_listing_limit_reached(self) -> bool:
        """Maksimum ilan limitine ulaşılıp ulaşılmadığını kontrol et"""
        return self._max_listings > 0 and len(self.all_listings) >= self._max_listings

    def _make_page_callback(self, prov_name: str, dist_name: str, tgt: Dict, page_num_ref: List[int]):
        """Her sayfa sonrası ilanları DB'ye kaydetmek için callback oluştur"""
        def _on_page_scraped(page_listings):
            for listing in page_listings:
                listing['il'] = prov_name
                if tgt['type'] == 'mahalle':
                    listing['ilce'] = dist_name
                    listing['mahalle'] = tgt['label'].split('/')[-1].strip()
                elif tgt['type'] == 'ilce':
                    listing['ilce'] = dist_name

            if self.db:
                from database import crud
                new_count = 0
                updated_count = 0
                unchanged_count = 0

                for data in page_listings:
                    try:
                        listing, status = crud.upsert_listing(
                            self.db,
                            data=data,
                            platform="emlakjet",
                            kategori=self.category,
                            ilan_tipi=self.listing_type,
                            alt_kategori=self.subtype_name,
                            scrape_session_id=self.scrape_session_id
                        )
                        if status == 'created':
                            new_count += 1
                        elif status == 'updated':
                            updated_count += 1
                        elif status == 'unchanged':
                            unchanged_count += 1
                    except Exception as e:
                        logger.warning(f"Sayfa bazlı DB kayıt hatası: {e}")
                try:
                    self.db.commit()
                    page_num_ref[0] += 1
                    logger.info(f"💾 Sayfa {page_num_ref[0]}: {new_count} yeni, {updated_count} güncellendi, {unchanged_count} değişmedi")
                except Exception as e:
                    logger.error(f"Sayfa bazlı DB commit hatası: {e}")
                    self.db.rollback()
        return _on_page_scraped

    def scrape_pages(self, target_url: str, max_pages: int, on_page_scraped=None,
                     location_label: str = "", province: str = "", district: str = "") -> bool:
        """Başarısız sayfa takibi ile sayfa tarama"""
        first_page_count = 0

        for current_page in range(1, max_pages + 1):
            if hasattr(self, '_stop_checker') and self._stop_checker and self._stop_checker():
                logger.info("Durdurma isteği alındı, sayfa tarama sonlandırılıyor")
                break

            if hasattr(self, '_max_listings') and self._max_listings > 0 and len(self.all_listings) >= self._max_listings:
                logger.info(f"İlan limitine ulaşıldı ({self._max_listings}), sayfa tarama sonlandırılıyor")
                break

            print(f"\n🔍 Sayfa {current_page} taranıyor...")

            try:
                if current_page > 1:
                    separator = '&' if '?' in target_url else '?'
                    page_url = f"{target_url}{separator}sayfa={current_page}"
                else:
                    page_url = target_url

                self.driver.get(page_url)
                time.sleep(self.config.wait_between_pages)

                # Sıfır ilan kontrolü (ilk sayfa)
                if current_page == 1:
                    try:
                        no_results = self.driver.find_elements(
                            By.CSS_SELECTOR, "span.styles_title__e_y3h"
                        )
                        for element in no_results:
                            if "ilan bulunamadı" in element.text.lower():
                                print("⚠️  Bu lokasyonda ilan bulunamadı, atlanıyor...")
                                return True
                    except:
                        pass

                listings = self.scrape_current_page()

                # 0 ilan bulunduysa ve ilk sayfa değilse → failed page olarak kaydet
                if len(listings) == 0 and current_page > 1:
                    print(f"   ⚠️ Sayfa {current_page}'de 0 ilan - retry listesine eklendi")
                    failed_pages_tracker.add_failed_page(FailedPageInfo(
                        url=page_url,
                        page_number=current_page,
                        city=province,
                        district=district,
                        error="0 listings found on page",
                        max_pages=max_pages,
                        listing_type=self.listing_type or "",
                        category=self.category or "",
                        subtype_path=self.subtype_path
                    ))
                else:
                    self.all_listings.extend(listings)

                    if on_page_scraped and listings:
                        on_page_scraped(listings)

                if current_page == 1:
                    first_page_count = len(listings)

                print(f"   ✅ Sayfa {current_page}: {len(listings)} ilan bulundu")

            except Exception as e:
                logger.error(f"Error scraping page {current_page}: {e}")
                print(f"   ⚠️ Sayfa {current_page} yüklenemedi - retry listesine eklendi")
                # Sayfa yükleme hatası → başarısız sayfa
                page_url = target_url if current_page == 1 else f"{target_url}{'&' if '?' in target_url else '?'}sayfa={current_page}"
                failed_pages_tracker.add_failed_page(FailedPageInfo(
                    url=page_url,
                    page_number=current_page,
                    city=province,
                    district=district,
                    error=str(e),
                    max_pages=max_pages,
                    listing_type=self.listing_type or "",
                    category=self.category or "",
                    subtype_path=self.subtype_path
                ))
                continue

        return first_page_count == 0 and max_pages == 1

    def _scrape_target(self, target: Dict, province_name: str, district_name: str) -> bool:
        """Tek bir hedefi (il/ilçe/mahalle) tara"""
        url_max_pages = self.get_max_pages(target['url'])
        print(f"📊 {url_max_pages} sayfa mevcut, tamamı taranacak.")

        page_num_ref = [0]  # Callback içinde sayfa sayacı için değiştirilebilir referans
        page_callback = self._make_page_callback(province_name, district_name, target, page_num_ref)
        should_skip = self.scrape_pages(
            target['url'], url_max_pages,
            on_page_scraped=page_callback,
            location_label=target['label'],
            province=province_name,
            district=district_name
        )
        return should_skip

    def start_scraping_api(self, cities: Optional[List[str]] = None, districts: Optional[Dict[str, List[str]]] = None, max_listings: int = 0, progress_callback=None, stop_checker=None):
        """İki katmanlı optimizasyonla API tarama giriş noktası"""
        self._stop_checker = stop_checker
        self._max_listings = max_listings

        subtype_info = f" ({self.subtype_name})" if self.subtype_name else ""
        limit_info = f" (limit: {max_listings} ilan)" if max_listings > 0 else " (limitsiz)"
        print(f"\n🚀 API: EmlakJet {self.listing_type.capitalize()} {self.category.capitalize()}{subtype_info} Scraper başlatılıyor{limit_info}")

        if progress_callback:
            progress_callback(f"{self.category.capitalize()}{subtype_info} taraması başlatılıyor...", 0, 100, 0)

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
                api_indices = []
                cities_lower = [c.lower() for c in cities]
                for idx, p in enumerate(all_provinces, 1):
                    if p['name'].lower() in cities_lower:
                        api_indices.append(idx)

                if not api_indices:
                    logger.error(f"Şehirler için eşleşen il bulunamadı: {cities}")
                    logger.info(f"Mevcut iller: {[p['name'] for p in all_provinces[:5]]}...")
                    return

                provinces = self.select_provinces(api_indices=api_indices, provinces=all_provinces)
            else:
                logger.error("API taraması için şehir belirtilmedi")
                return

            # Adım 2: Her ili optimizasyonla işle
            stopped = False
            scrape_stats = {}  # {il_adı: {ilçe_adı: ilan_sayısı}} — özet rapor için
            for prov_idx, province in enumerate(provinces, 1):
                if self._is_stop_requested():
                    print(f"\n⚠️ Durdurma isteği alındı! {len(self.all_listings)} ilan toplandı.")
                    logger.warning(f"⚠️ Tarama erken durduruldu: {len(self.all_listings)} ilan")
                    stopped = True
                    break
                if self._is_listing_limit_reached():
                    stopped = True
                    break

                # İl sayfasına git ve ilan sayısını al (get_listing_count sayfayı yükler)
                province_count = self.get_listing_count(province['url'])

                print("\n" + "=" * 70)
                print(f"🏙️  İL {prov_idx}/{len(provinces)}: {province['name']} (Toplam İlan: {province_count})")
                print("=" * 70)

                if progress_callback:
                    base_progress = ((prov_idx - 1) / len(provinces)) * 100
                    progress_callback(f"İşleniyor: {province['name']}...", prov_idx, len(provinces), base_progress)

                # ── OPTİMİZASYON: İl seviyesi kontrol ──
                if province_count == 0:
                    print(f"⏭️  {province['name']} → 0 ilan, il atlanıyor.")
                    continue

                if province_count <= self.PAGINATION_LIMIT:
                    # İl genelinde ≤1500 ilan — ilçe/mahalleye inmeye gerek yok
                    print(f"⚡ {province['name']} → {province_count} ilan (≤{self.PAGINATION_LIMIT}), il seviyesinden taranıyor.")
                    target = {'url': province['url'], 'label': province['name'], 'type': 'il'}
                    print(f"\n📍 Taranıyor: {target['label']}")
                    listings_before = len(self.all_listings)
                    should_skip = self._scrape_target(target, province['name'], province['name'])
                    scraped_count = len(self.all_listings) - listings_before
                    if should_skip:
                        print("⏭️  Bu lokasyon atlandı.")
                    else:
                        print(f"   📦 Toplam: {len(self.all_listings)} ilan toplandı")
                        scrape_stats[province['name']] = {'(il seviyesi)': scraped_count}

                    if progress_callback:
                        overall = (prov_idx / len(provinces)) * 100
                        progress_callback(
                            f"{province['name']} (il seviyesi)",
                            1, 1, min(int(overall), 99),
                        )
                    continue

                # İl > 1500 ilan — ilçelere iniyoruz
                print(f"📊 {province['name']} → {province_count} ilan (>{self.PAGINATION_LIMIT}), ilçe seviyesine iniliyor...")

                # İlçe filtreleme var mı kontrol et
                province_name = province['name']
                api_districts_for_province = None
                if districts and province_name in districts:
                    api_districts_for_province = districts[province_name]
                    logger.info(f"{province_name} için ilçe filtresi aktif: {api_districts_for_province}")

                # İlçe listesini al
                district_list, _ = self.get_location_options("İlçeler", province['url'])

                if not district_list:
                    print(f"⏭️  {province['name']} ilçe bulunamadı, atlanıyor.")
                    continue

                # İlçe filtresi uygula
                if api_districts_for_province:
                    district_list = [d for d in district_list if d['name'] in api_districts_for_province]
                    if not district_list:
                        print(f"⏭️  {province['name']} için eşleşen ilçe bulunamadı.")
                        continue

                for d in district_list:
                    d['il'] = province_name

                # Her ilçeyi işle
                for dist_idx, district in enumerate(district_list, 1):
                    if self._is_stop_requested():
                        print(f"\n⚠️ Durdurma isteği alındı! {len(self.all_listings)} ilan toplandı.")
                        logger.warning(f"⚠️ Tarama erken durduruldu: {len(self.all_listings)} ilan")
                        stopped = True
                        break
                    if self._is_listing_limit_reached():
                        stopped = True
                        break

                    # İlçe sayfasına git ve ilan sayısını al
                    district_count = self.get_listing_count(district['url'])

                    print(f"\n📍 İlçe {dist_idx}/{len(district_list)}: {district['name']} (İlan: {district_count})")

                    # ── OPTİMİZASYON: İlçe seviyesi kontrol ──
                    if district_count == 0:
                        print(f"⏭️  {district['name']} → 0 ilan, ilçe atlanıyor.")
                        continue

                    if district_count <= self.PAGINATION_LIMIT:
                        # İlçede ≤1500 ilan — mahalleye inmeye gerek yok
                        print(f"⚡ {district['name']} → {district_count} ilan (≤{self.PAGINATION_LIMIT}), ilçe seviyesinden taranıyor.")
                        target = {
                            'url': district['url'],
                            'label': f"{province_name} / {district['name']}",
                            'type': 'ilce'
                        }
                        print(f"\n📍 Taranıyor: {target['label']}")
                        listings_before = len(self.all_listings)
                        should_skip = self._scrape_target(target, province_name, district['name'])
                        scraped_count = len(self.all_listings) - listings_before

                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(district_list), 1)
                            overall = province_base + dist_idx * district_range
                            progress_callback(
                                f"{province_name} > {district['name']}",
                                dist_idx, len(district_list), min(int(overall), 99),
                            )

                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {len(self.all_listings)} ilan toplandı")
                            scrape_stats.setdefault(province_name, {})[district['name']] = scraped_count
                        continue

                    # İlçe > 1500 ilan — mahallelere iniyoruz
                    print(f"📊 {district['name']} → {district_count} ilan (>{self.PAGINATION_LIMIT}), mahalle seviyesine iniliyor...")

                    neighborhoods, _ = self.get_location_options("Mahalleler", district['url'])

                    if not neighborhoods:
                        # Mahalle bulunamadı — ilçe seviyesinden tara
                        target = {
                            'url': district['url'],
                            'label': f"{province_name} / {district['name']}",
                            'type': 'ilce'
                        }
                        print(f"\n📍 Mahalle bulunamadı, ilçe seviyesinden taranıyor: {target['label']}")
                        should_skip = self._scrape_target(target, province_name, district['name'])
                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {len(self.all_listings)} ilan toplandı")
                        continue

                    for n in neighborhoods:
                        n['il'] = province_name
                        n['ilce'] = district['name']

                    targets = [
                        {
                            'url': n['url'],
                            'label': f"{n.get('il', '')} / {n.get('ilce', '')} / {n['name']}",
                            'type': 'mahalle'
                        }
                        for n in neighborhoods
                    ]

                    total_targets = len(targets)
                    for target_idx, target in enumerate(targets, 1):
                        if self._is_stop_requested():
                            print(f"\n⚠️ Durdurma isteği alındı! {len(self.all_listings)} ilan toplandı.")
                            logger.warning(f"⚠️ Tarama erken durduruldu: {len(self.all_listings)} ilan")
                            stopped = True
                            break
                        if self._is_listing_limit_reached():
                            stopped = True
                            break

                        print(f"\n📍 Taranıyor: {target['label']} ({target_idx}/{total_targets})")
                        listings_before = len(self.all_listings)
                        should_skip = self._scrape_target(target, province_name, district['name'])
                        scraped_count = len(self.all_listings) - listings_before

                        # Mahalle bazlı istatistikler — ilçe altında topla
                        if scraped_count > 0:
                            scrape_stats.setdefault(province_name, {})
                            scrape_stats[province_name][district['name']] = scrape_stats[province_name].get(district['name'], 0) + scraped_count

                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(district_list), 1)
                            target_range = district_range / max(total_targets, 1)
                            overall = province_base + (dist_idx - 1) * district_range + target_idx * target_range
                            progress_callback(
                                f"{province_name} > {district['name']} > {target['label'].split('/')[-1].strip()}",
                                target_idx, total_targets, min(int(overall), 99),
                            )

                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {len(self.all_listings)} ilan toplandı")

                    if stopped:
                        break
                if stopped:
                    break

            if self._is_listing_limit_reached():
                print(f"\n🎯 İlan limitine ulaşıldı: {len(self.all_listings)} / {self._max_listings}")

            # ── HİYERARŞİK ÖZET RAPOR ──
            print(f"\n{'=' * 70}")
            if stopped and self._is_stop_requested():
                print("⚠️  ERKEN DURDURULDU")
                logger.warning(f"⚠️ Tarama erken durduruldu: {len(scrape_stats)} il, {len(self.all_listings)} ilan")
            elif self.all_listings:
                print("✅ TARAMA BAŞARIYLA TAMAMLANDI")
                logger.info(f"✅ Tarama tamamlandı: {len(scrape_stats)} il, {len(self.all_listings)} ilan")
            else:
                print("❌ HİÇ İLAN BULUNAMADI")
                logger.warning("⚠️ Hiç ilan bulunamadı")

            if scrape_stats:
                print(f"📊 Taranan İl Sayısı: {len(scrape_stats)}")
                print(f"📊 Toplam İlan Sayısı: {len(self.all_listings)}")
                for city, districts_data in scrape_stats.items():
                    city_total = sum(districts_data.values())
                    print(f"   • {city}: {city_total} ilan ({len(districts_data)} ilçe/bölge)")
                    for district_name, count in districts_data.items():
                        print(f"      - {district_name}: {count} ilan")
            print("=" * 70)

            # ── RETRY MEKANİZMASI ──
            max_retries = 3
            retry_round = 0
            successful_retries = 0

            while failed_pages_tracker.has_failed_pages() and retry_round < max_retries:
                if self._is_stop_requested():
                    print(f"\n⚠️ Retry durduruldu!")
                    break

                retry_round += 1
                failed_pages = failed_pages_tracker.get_unretried(max_retry_count=max_retries)

                if not failed_pages:
                    break

                print(f"\n{'=' * 70}")
                print(f"🔄 YENİDEN DENEME #{retry_round}/{max_retries}")
                print(f"📊 {len(failed_pages)} başarısız sayfa tekrar taranacak")
                print("=" * 70)

                if progress_callback:
                    progress_callback(
                        f"🔄 Retry #{retry_round} - {len(failed_pages)} sayfa",
                        0, len(failed_pages), 0
                    )

                for idx, page_info in enumerate(failed_pages, 1):
                    if self._is_stop_requested():
                        print(f"\n⚠️ Retry durduruldu!")
                        break

                    print(f"\n🔄 [{idx}/{len(failed_pages)}] {page_info.city}/{page_info.district or 'tüm'} - Sayfa {page_info.page_number}")

                    if progress_callback:
                        progress_callback(
                            f"🔄 Retry #{retry_round}: {page_info.city} Sayfa {page_info.page_number}",
                            idx, len(failed_pages), int((idx / len(failed_pages)) * 100)
                        )

                    try:
                        retry_manager = DriverManager()
                        retry_driver = retry_manager.start()

                        try:
                            print(f"   🌐 {page_info.url}")
                            retry_driver.get(page_info.url)
                            time.sleep(self.config.wait_between_pages + 1)

                            # İlanları tara
                            container_selector = self.common_selectors.get("listing_container")
                            containers = retry_driver.find_elements(By.CSS_SELECTOR, container_selector)

                            if containers:
                                listings = []
                                for container in containers:
                                    try:
                                        data = self.extract_listing_data(container)
                                        if data:
                                            listings.append(data)
                                    except:
                                        continue

                                if listings:
                                    print(f"   ✅ {len(listings)} ilan bulundu!")
                                    self.all_listings.extend(listings)

                                    # DB'ye kaydet
                                    if self.db:
                                        from database import crud
                                        for data in listings:
                                            try:
                                                crud.upsert_listing(
                                                    self.db, data=data,
                                                    platform="emlakjet",
                                                    kategori=self.category,
                                                    ilan_tipi=self.listing_type,
                                                    alt_kategori=self.subtype_name,
                                                    scrape_session_id=self.scrape_session_id
                                                )
                                            except:
                                                pass
                                        try:
                                            self.db.commit()
                                        except:
                                            self.db.rollback()

                                    failed_pages_tracker.mark_as_success(
                                        page_info.city, page_info.district, page_info.page_number
                                    )
                                    successful_retries += 1
                                else:
                                    print(f"   ⚠️ 0 ilan - devam ediliyor")
                                    failed_pages_tracker.increment_retry_count(
                                        page_info.city, page_info.district, page_info.page_number
                                    )
                            else:
                                print(f"   ⚠️ Element bulunamadı")
                                failed_pages_tracker.increment_retry_count(
                                    page_info.city, page_info.district, page_info.page_number
                                )
                        finally:
                            retry_manager.stop()

                    except Exception as e:
                        logger.error(f"Retry hatası: {e}")
                        failed_pages_tracker.increment_retry_count(
                            page_info.city, page_info.district, page_info.page_number
                        )

                    time.sleep(random.uniform(1, 2))

            # Yeniden deneme özeti
            summary = failed_pages_tracker.get_summary()
            if summary["failed_count"] > 0 or successful_retries > 0:
                print(f"\n{'=' * 70}")
                print("📊 RETRY ÖZETİ")
                print(f"   ✅ Başarılı retry: {successful_retries}")
                print(f"   ❌ Kalan başarısız: {summary['failed_count']}")
                print("=" * 70)

                if summary["failed_count"] > 0:
                    logger.warning(f"⚠️ {summary['failed_count']} sayfa retry sonrası hala başarısız")
                    for fp in summary["failed_pages"]:
                        logger.warning(f"   - {fp['city']}/{fp['district'] or 'tüm'} Sayfa {fp['page_number']}: {fp['error']}")

        except Exception as e:
            logger.error(f"API tarama hatası: {e}")
            raise e

