import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re


class HepsiemlakKatKarsiligiArsaScraper:
    def __init__(self):
        # Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Gerçek bir tarayıcı gibi görünmek için User-Agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")
        
        # Driver'ı başlatıyoruz
        self.driver = webdriver.Chrome(options=chrome_options)
        
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.wait = WebDriverWait(self.driver, 15)  # Timeout süresini artırdık

    def get_cities(self):
        """Tüm illeri getir ve kullanıcıya çoklu şehir seçtir - GÜNCELLENDİ"""
        print("Hepsiemlak kat karşılığı satılık arsa sitesine gidiliyor...")
        self.driver.get("https://www.hepsiemlak.com/kat-karsiligi-satilik/arsa")
        time.sleep(4)

        try:
            # İl seçiniz dropdown'ını bul ve tıkla - GELİŞTİRİLMİŞ SELECTOR
            print("Şehir dropdown'ı aranıyor...")
            city_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.he-select-base__container, div[data-name='city']"))
            )
            city_dropdown.click()
            print("Şehir dropdown'ı tıklandı...")
            time.sleep(2)

            # Dropdown container'ını bul - GELİŞTİRİLMİŞ SELECTOR
            dropdown_container = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.he-select-base__list, div.he-select__list"))
            )

            # JavaScript ile tüm şehirleri aç
            print("Tüm şehirler yükleniyor...")
            self.driver.execute_script(
                """
                var container = arguments[0];
                container.style.maxHeight = 'none';
                container.style.overflow = 'visible';
                container.style.height = 'auto';
                """,
                dropdown_container,
            )
            time.sleep(3)

            # Tüm şehir list item'larını al - GELİŞTİRİLMİŞ SELECTOR
            city_items = self.driver.find_elements(By.CSS_SELECTOR, "li.he-select__list-item, li.he-select-base__list-item")

            cities = []
            for idx, city_item in enumerate(city_items):
                try:
                    # GELİŞTİRİLMİŞ SELECTOR
                    city_link = city_item.find_element(By.CSS_SELECTOR, "a.js-city-filter__list-link, span.he-select-base__text")
                    city_name = city_link.text.strip()
                    if city_name and city_name != "İl Seçiniz" and city_name not in cities:
                        cities.append(city_name)
                except:
                    continue

            # Şehirleri alfabetik sırala
            cities.sort()

            # TÜM şehirleri listele
            print("\n" + "=" * 50)
            print("TÜM ŞEHİRLER LİSTESİ")
            print("=" * 50)
            for i, city in enumerate(cities):
                print(f"{i+1:2d}. {city}")
            print(f"\nToplam {len(cities)} şehir bulundu.")

            if not cities:
                print("Hiç şehir bulunamadı!")
                return None

            # Kullanıcıdan birden fazla şehir seçmesini iste
            selected_cities = []
            print("\n" + "="*50)
            print("ŞEHİR SEÇİM SEÇENEKLERİ")
            print("="*50)
            print("1. Tek tek şehir seç (örn: 1,3,5)")
            print("2. Aralık seç (örn: 1-5)")
            print("3. Tüm şehirleri seç")
            print("4. Şehir sil")
            print("5. Seçimi bitir")
            
            while True:
                try:
                    print(f"\nŞu an seçili şehirler ({len(selected_cities)}): {', '.join(selected_cities)}")
                    option = input("\nSeçenek (1-5): ").strip()
                    
                    if option == "5":
                        if selected_cities:
                            print(f"\nSeçim tamamlandı. Seçilen {len(selected_cities)} şehir: {', '.join(selected_cities)}")
                            # Dropdown'ı kapat - İYİLEŞTİRİLMİŞ HATA YÖNETİMİ
                            try:
                                self.driver.execute_script("document.elementFromPoint(10, 10).click();")
                            except:
                                pass
                            time.sleep(1)
                            return selected_cities
                        else:
                            print("En az bir şehir seçmelisiniz!")
                            continue
                    
                    elif option == "4":
                        # ŞEHİR SİLME SEÇENEĞİ
                        if not selected_cities:
                            print("Silinecek şehir yok!")
                            continue
                        
                        print("\nMevcut seçili şehirler:")
                        for i, city in enumerate(selected_cities, 1):
                            print(f"{i}. {city}")
                        
                        try:
                            delete_input = input("\nSilmek istediğiniz şehir numaralarını girin (örn: 1,3 veya 1-3): ").strip()
                            
                            cities_to_delete = []
                            
                            if '-' in delete_input:
                                # Aralık silme
                                start, end = map(int, delete_input.split('-'))
                                if 1 <= start <= len(selected_cities) and 1 <= end <= len(selected_cities) and start <= end:
                                    cities_to_delete = selected_cities[start-1:end]
                                else:
                                    print("Geçersiz aralık!")
                                    continue
                            else:
                                # Tek tek silme
                                numbers = []
                                if ',' in delete_input:
                                    numbers = delete_input.split(',')
                                else:
                                    numbers = delete_input.split()
                                
                                for num_str in numbers:
                                    num_str = num_str.strip()
                                    if not num_str:
                                        continue
                                        
                                    try:
                                        choice = int(num_str)
                                        if 1 <= choice <= len(selected_cities):
                                            cities_to_delete.append(selected_cities[choice-1])
                                        else:
                                            print(f"Geçersiz numara: {choice}")
                                    except ValueError:
                                        print(f"Geçersiz sayı: {num_str}")
                            
                            # Şehirleri sil
                            for city in cities_to_delete:
                                if city in selected_cities:
                                    selected_cities.remove(city)
                                    print(f"✓ {city} silindi")
                            
                        except Exception as e:
                            print(f"Silme işleminde hata: {e}")
                    
                    elif option == "3":
                        # Tüm şehirleri seç
                        selected_cities = cities.copy()
                        print("Tüm şehirler seçildi!")
                        continue
                    
                    elif option == "2":
                        # Aralık seç
                        try:
                            range_input = input("Aralık girin (örn: 1-5): ").strip()
                            if '-' in range_input:
                                start, end = map(int, range_input.split('-'))
                                if 1 <= start <= len(cities) and 1 <= end <= len(cities) and start <= end:
                                    for i in range(start, end + 1):
                                        if cities[i-1] not in selected_cities:
                                            selected_cities.append(cities[i-1])
                                    print(f"{end - start + 1} şehir eklendi.")
                                else:
                                    print("Geçersiz aralık!")
                            else:
                                print("Geçersiz format! Örnek: 1-5")
                        except ValueError:
                            print("Geçersiz sayı formatı!")
                    
                    elif option == "1":
                        # Tek tek şehir seç - İYİLEŞTİRİLMİŞ HATA YÖNETİMİ
                        user_input = input("Şehir numaralarını girin (örn: 1,3,5): ").strip()
                        
                        numbers = []
                        if ',' in user_input:
                            numbers = user_input.split(',')
                        else:
                            numbers = user_input.split()
                        
                        for num_str in numbers:
                            num_str = num_str.strip()
                            if not num_str:
                                continue
                                
                            try:
                                choice = int(num_str)
                                
                                if 1 <= choice <= len(cities):
                                    selected_city = cities[choice-1]
                                    
                                    if selected_city in selected_cities:
                                        print(f"{selected_city} zaten seçilmiş!")
                                        continue
                                        
                                    selected_cities.append(selected_city)
                                    print(f"Seçilen şehir: {selected_city}")
                                    
                                else:
                                    print(f"Geçersiz seçim: {choice}! Lütfen 1-{len(cities)} arasında bir numara girin.")
                            except ValueError:
                                print(f"Geçersiz sayı: {num_str}")
                    
                    else:
                        print("Geçersiz seçenek! Lütfen 1-5 arasında bir numara girin.")
                            
                except Exception as e:
                    print(f"Hata: {e}")

        except Exception as e:
            print(f"Şehir seçiminde hata: {e}")
            return None

    def select_single_city(self, city_name):
        """Tek bir şehir seç - GELİŞTİRİLMİŞ VERSİYON"""
        try:
            # Sayfayı yenile ve temiz başla
            self.driver.get("https://www.hepsiemlak.com/kat-karsiligi-satilik/arsa")
            time.sleep(3)

            # İl seçiniz dropdown'ını bul ve tıkla - GELİŞTİRİLMİŞ SELECTOR
            print(f"{city_name} şehri seçiliyor...")
            city_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.he-select-base__container, div[data-name='city']"))
            )
            city_dropdown.click()
            time.sleep(2)

            # Dropdown container'ını bul - GELİŞTİRİLMİŞ SELECTOR
            dropdown_container = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.he-select-base__list, div.he-select__list"))
            )

            # JavaScript ile tüm şehirleri aç
            self.driver.execute_script(
                """
                var container = arguments[0];
                container.style.maxHeight = 'none';
                container.style.overflow = 'visible';
                container.style.height = 'auto';
                """,
                dropdown_container,
            )
            time.sleep(2)
    
            # Tüm şehir list item'larını al - GELİŞTİRİLMİŞ SELECTOR
            city_items = self.driver.find_elements(By.CSS_SELECTOR, "li.he-select__list-item, li.he-select-base__list-item")

            # İstenen şehri bul ve seç
            city_found = False
            for city_item in city_items:
                try:
                    # GELİŞTİRİLMİŞ SELECTOR
                    city_link = city_item.find_element(By.CSS_SELECTOR, "a.js-city-filter__list-link, span.he-select-base__text")
                    current_city_name = city_link.text.strip()

                    if current_city_name == city_name:
                        # GELİŞTİRİLMİŞ SEÇİM MEKANİZMASI
                        try:
                            radio_button = city_item.find_element(By.CSS_SELECTOR, "div.he-radio, input[type='radio']")
                            self.driver.execute_script("arguments[0].click();", radio_button)
                            city_found = True
                            print(f"✓ {city_name} şehri seçildi")
                            break
                        except:
                            # Radio buton bulunamazsa direkt elemente tıkla
                            self.driver.execute_script("arguments[0].click();", city_link)
                            city_found = True
                            print(f"✓ {city_name} şehri seçildi")
                            break
                except:
                    continue

            # Dropdown'ı kapat - İYİLEŞTİRİLMİŞ HATA YÖNETİMİ
            try:
                self.driver.execute_script("document.elementFromPoint(10, 10).click();")
            except:
                pass
            time.sleep(2)

            if city_found:
                # Seçimin uygulanması için kısa bekle
                time.sleep(2)
                return True
            else:
                print(f"✗ {city_name} şehri bulunamadı")
                return False

        except Exception as e:
            print(f"{city_name} şehri seçilirken hata: {e}")
            return False

    def search_listings(self):
        """Ara butonuna tıkla ve filtreyi uygula - GELİŞTİRİLMİŞ VERSİYON"""
        try:
            # Farklı ara butonu seçenekleri - ÇOKLU SELECTOR DESTEĞİ
            search_selectors = [
                "a.btn.btn-red.btn-large",
                "button.btn.btn-red.btn-large", 
                "a[data-tracking-label='SearchSubmit']",
                "button[type='submit']",
                ".btn-red"
            ]
            
            search_button = None
            for selector in search_selectors:
                try:
                    search_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if search_button:
                self.driver.execute_script("arguments[0].click();", search_button)
                print("Arama yapılıyor...")
                
                # Arama sonuçlarının yüklenmesini bekle
                time.sleep(5)
                
                # Sayfanın yüklendiğinden emin ol - GELİŞTİRİLMİŞ KONTROL
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-items-container, .listing-item, .search-results"))
                )
                print("Arama sonuçları yüklendi")
                return True
            else:
                print("Arama butonu bulunamadı")
                return False
                
        except Exception as e:
            print(f"Arama butonunda hata: {e}")
            return False

    def extract_listing_data(self, listing_element):
        """Tek bir kat karşılığı satılık arsa ilanın verilerini çıkar"""
        try:
            data = {}

            # Fiyat (kat karşılığı arsalarda fiyat farklı yerde olabilir)
            try:
                price_element = listing_element.find_element(
                    By.CSS_SELECTOR, "span.list-view-price"
                )
                price_text = price_element.text.strip()
                data["fiyat"] = price_text
            except:
                data["fiyat"] = "Kat Karşılığı"

            # Başlık
            try:
                title_element = listing_element.find_element(By.CSS_SELECTOR, "h3")
                data["baslik"] = title_element.text.strip()
            except:
                data["baslik"] = "Belirtilmemiş"

            # Konum - il, ilçe, mahalle ayrı ayrı
            try:
                location_element = listing_element.find_element(
                    By.CSS_SELECTOR, "span.list-view-location"
                )
                location_text = location_element.text.strip()
                
                # Konum bilgisini parçala: "Kocaeli / Gölcük / Şehitler Mah."
                location_parts = [part.strip() for part in location_text.split('/')]
                
                # İl
                if len(location_parts) > 0:
                    data["il"] = location_parts[0]
                else:
                    data["il"] = "Belirtilmemiş"
                
                # İlçe
                if len(location_parts) > 1:
                    data["ilce"] = location_parts[1]
                else:
                    data["ilce"] = "Belirtilmemiş"
                
                # Mahalle
                if len(location_parts) > 2:
                    data["mahalle"] = location_parts[2]
                else:
                    data["mahalle"] = "Belirtilmemiş"
                    
            except:
                data["il"] = "Belirtilmemiş"
                data["ilce"] = "Belirtilmemiş"
                data["mahalle"] = "Belirtilmemiş"

            # Arsa özellikleri
            try:
                # Metrekare
                try:
                    size_elements = listing_element.find_elements(
                        By.CSS_SELECTOR, "span.celly.squareMeter.list-view-size"
                    )
                    for size_element in size_elements:
                        size_text = size_element.text.strip()
                        if "m²" in size_text and not "TL" in size_text:
                            data["metrekare"] = size_text
                            break
                    else:
                        data["metrekare"] = "Belirtilmemiş"
                except:
                    data["metrekare"] = "Belirtilmemiş"

                # Metrekare fiyatı
                try:
                    price_per_sqm_elements = listing_element.find_elements(
                        By.CSS_SELECTOR, "span.celly.squareMeter.list-view-size"
                    )
                    for price_element in price_per_sqm_elements:
                        price_text = price_element.text.strip()
                        if "TL / m²" in price_text:
                            data["metrekare_fiyati"] = price_text
                            break
                    else:
                        data["metrekare_fiyati"] = "Belirtilmemiş"
                except:
                    data["metrekare_fiyati"] = "Belirtilmemiş"

            except:
                data["metrekare"] = "Belirtilmemiş"
                data["metrekare_fiyati"] = "Belirtilmemiş"

            # Arsa tipi
            try:
                property_type_element = listing_element.find_element(
                    By.CSS_SELECTOR, "span.short-property span.left"
                )
                data["arsa_tipi"] = property_type_element.text.strip()
            except:
                data["arsa_tipi"] = "Belirtilmemiş"

            # İlan tarihi
            try:
                date_element = listing_element.find_element(
                    By.CSS_SELECTOR, "span.list-view-date"
                )
                data["ilan_tarihi"] = date_element.text.strip()
            except:
                data["ilan_tarihi"] = "Belirtilmemiş"

            # Emlak ofisi
            try:
                firm_element = listing_element.find_element(
                    By.CSS_SELECTOR, "a.img-wrp.hasBranded img"
                )
                data["emlak_ofisi"] = firm_element.get_attribute("alt")
            except:
                data["emlak_ofisi"] = "Belirtilmemiş"

            # Fotoğraf sayısı
            try:
                photo_element = listing_element.find_element(
                    By.CSS_SELECTOR, "span.photo-count"
                )
                data["fotograf_sayisi"] = photo_element.text.strip()
            except:
                data["fotograf_sayisi"] = "Belirtilmemiş"

            # İlan linki
            try:
                link_element = listing_element.find_element(
                    By.CSS_SELECTOR, "a.card-link"
                )
                href = link_element.get_attribute("href")
                if href.startswith("/"):
                    data["ilan_linki"] = "https://www.hepsiemlak.com" + href
                else:
                    data["ilan_linki"] = href
            except:
                data["ilan_linki"] = "Belirtilmemiş"

            # İlan tipi
            data["ilan_tipi"] = "Kat Karşılığı Satılık Arsa"

            return data

        except Exception as e:
            print(f"İlan verisi çıkarılırken hata: {e}")
            return None

    def scrape_page(self):
        """Mevcut sayfadaki tüm kat karşılığı satılık arsa ilanları scrape et - GELİŞTİRİLMİŞ VERSİYON"""
        listings_data = []

        try:
            # İlan container'ını bekle - GELİŞTİRİLMİŞ SELECTOR
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-items-container, .search-results"))
            )

            # Tüm ilan elementlerini al - PROMOSYON İLANLARI HARİÇ
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.listing-item:not(.listing-item--promo)")
            actual_count = len(listing_elements)
            print(f"Bulunan kat karşılığı satılık arsa ilan sayısı: {actual_count}")

            for idx, listing_element in enumerate(listing_elements):
                try:
                    listing_data = self.extract_listing_data(listing_element)
                    if listing_data:
                        listings_data.append(listing_data)
                    time.sleep(0.05)  # DAHA KISA BEKLEME SÜRESİ
                except Exception as e:
                    print(f"İlan {idx} işlenirken hata: {e}")
                    continue

            print(f"Başarıyla işlenen kat karşılığı satılık arsa ilan sayısı: {len(listings_data)}")
            return listings_data

        except Exception as e:
            print(f"Sayfa scrape edilirken hata: {e}")
            return []

    def get_total_pages(self):
        """Toplam sayfa sayısını bul - GELİŞTİRİLMİŞ VERSİYON"""
        try:
            # Farklı pagination seçenekleri - ÇOKLU SELECTOR DESTEĞİ
            pagination_selectors = [
                "ul.he-pagination__links li.he-pagination__item a.he-pagination__link",
                ".pagination a",
                ".he-pagination a",
                "a[href*='page=']"
            ]
            
            for selector in pagination_selectors:
                try:
                    pagination_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if pagination_elements:
                        last_page = pagination_elements[-1].get_attribute("href")
                        if last_page:
                            page_match = re.search(r"page=(\d+)", last_page)
                            if page_match:
                                return int(page_match.group(1))
                except:
                    continue
            
            return 1
        except:
            return 1

    def go_to_page(self, page_number):
        """Belirtilen sayfaya git - GELİŞTİRİLMİŞ VERSİYON"""
        try:
            if page_number == 1:
                url = "https://www.hepsiemlak.com/kat-karsiligi-satilik/arsa"
            else:
                url = f"https://www.hepsiemlak.com/kat-karsiligi-satilik/arsa?page={page_number}"

            self.driver.get(url)
            time.sleep(4)
            
            # Sayfanın yüklendiğinden emin ol - GELİŞTİRİLMİŞ KONTROL
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-items-container, .listing-item, .search-results"))
            )
            return True
        except Exception as e:
            print(f"Sayfa {page_number} açılırken hata: {e}")
            return False

    def scrape_city_listings(self, city):
        """Tek bir şehir için tüm ilanları scrape et - GELİŞTİRİLMİŞ VERSİYON"""
        print(f"\n{'='*60}")
        print(f"{city} İÇİN KAT KARŞILIĞI SATILIK ARSA SCRAPING BAŞLIYOR")
        print(f"{'='*60}")
        
        try:
            # Şehir seçimi yap
            if not self.select_single_city(city):
                print(f"{city} şehri seçilemedi, atlanıyor...")
                return []
                
            # Arama yap
            if not self.search_listings():
                print(f"{city} için arama yapılamadı, atlanıyor...")
                return []
            
            # SIFIR ILAN KONTROLÜ
            try:
                zero_ilan_element = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'için 0 ilan bulundu')]")
                if zero_ilan_element:
                    print(f"⚠️  {city} için 0 kat karşılığı satılık arsa ilanı bulundu, atlanıyor...")
                    return []
            except:
                pass
            
            # Şehir filtresinin uygulandığını kontrol et
            try:
                current_url = self.driver.current_url.lower()
                city_lower = city.lower()

                # Türkçe karakter dönüşümü
                turkce_cevir = str.maketrans('ığüşöç', 'igusoc')
                city_url_format = city_lower.translate(turkce_cevir)

                if city_url_format not in current_url and city_lower not in current_url:
                    print(f"UYARI: {city} filtresi URL'de görünmüyor, filtreleme çalışmayabilir!")
                else:
                    print(f"✓ {city} filtresi URL'de doğrulandı")
            except:
                pass
            
            # Toplam sayfa sayısını al
            total_pages = self.get_total_pages()
            print(f"{city} için toplam sayfa sayısı: {total_pages}")
            
            if total_pages == 0 or total_pages > 100:  # 100'den fazla sayfa olması mantıksız
                print(f"{city} için hiç kat karşılığı satılık arsa ilanı bulunamadı veya sayfa sayısı hatalı!")
                return []

            # Kullanıcıdan kaç sayfa scrape edileceğini sor - İYİLEŞTİRİLMİŞ HATA YÖNETİMİ
            if total_pages > 1:
                try:
                    user_input = input(f"{city} için kaç sayfa scrape edilsin? (1-{total_pages}): ")
                    pages_to_scrape = min(int(user_input), total_pages)
                    if pages_to_scrape < 1:
                        pages_to_scrape = 1
                except:
                    pages_to_scrape = min(3, total_pages)
                    print(f"Geçersiz giriş, {pages_to_scrape} sayfa scrape edilecek.")
            else:
                pages_to_scrape = 1

            city_listings = []
            
            for page in range(1, pages_to_scrape + 1):
                print(f"{city} - Sayfa {page}/{pages_to_scrape} scrape ediliyor...")
                
                if page > 1:
                    if not self.go_to_page(page):
                        print(f"Sayfa {page} açılamadı, devam ediliyor...")
                        continue

                page_listings = self.scrape_page()
                if page_listings:
                    city_listings.extend(page_listings)
                    print(f"{city} - Sayfa {page} tamamlandı. Toplam kat karşılığı satılık arsa ilan: {len(city_listings)}")
                else:
                    print(f"{city} - Sayfa {page}'da kat karşılığı satılık arsa ilanı bulunamadı")

                if page < pages_to_scrape:
                    time.sleep(3)  # SAYFALAR ARASI BEKLEME SÜRESİNİ ARTIRDIK
            
            print(f"✓ {city} için scraping tamamlandı. Toplam {len(city_listings)} kat karşılığı satılık arsa ilanı bulundu.")
            return city_listings
            
        except Exception as e:
            print(f"{city} için scraping sırasında hata: {e}")
            return []

    def scrape_all_cities(self, selected_cities):
        """Tüm seçilen şehirler için ayrı ayrı scrape yap"""
        all_results = {}
        
        for city in selected_cities:
            city_listings = self.scrape_city_listings(city)
            if city_listings:
                all_results[city] = city_listings
            else:
                print(f"{city} için hiç kat karşılığı satılık arsa ilanı bulunamadı")
            
            # Bir sonraki şehir için bekle
            time.sleep(2)
        
        return all_results

    def save_to_excel_multiple(self, all_results):
        """Her şehir için ayrı Excel dosyasına kaydet"""
        if not all_results:
            print("Kaydedilecek veri yok!")
            return

        total_ilan = 0
        
        for city, data in all_results.items():
            if data:
                filename = f"hepsiemlak_{city.lower()}_kat_karsiligi_arsa.xlsx"
                
                df = pd.DataFrame(data)
                
                # Sütun sıralamasını düzenle
                preferred_order = [
                    'baslik', 'fiyat', 'il', 'ilce', 'mahalle', 'arsa_tipi', 'metrekare',
                    'metrekare_fiyati', 'fotograf_sayisi', 'emlak_ofisi', 
                    'ilan_tarihi', 'ilan_linki', 'ilan_tipi'
                ]
                
                existing_columns = [col for col in preferred_order if col in df.columns]
                remaining_columns = [col for col in df.columns if col not in existing_columns]
                final_columns = existing_columns + remaining_columns
                
                df = df[final_columns]
                df.to_excel(filename, index=False, engine="openpyxl")
                print(f"✓ {city} verileri {filename} dosyasına kaydedildi! ({len(data)} kat karşılığı satılık arsa ilanı)")
                total_ilan += len(data)
        
        print(f"\n🎉 TOPLAM: {len(all_results)} şehir için {total_ilan} kat karşılığı satılık arsa ilanı kaydedildi!")

    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()


def main():
    while True:
        print("\n" + "="*60)
        print("🏗️ HEPSİEMLAK KAT KARŞILIĞI SATILIK ARSA SCRAPER")
        print("="*60)
        print("1. Scraping işlemi başlat")
        print("2. Çıkış")
        
        choice = input("\nSeçiminiz (1-2): ")
        
        if choice == "2":
            print("Program sonlandırılıyor...")
            break
        elif choice == "1":
            scraper = HepsiemlakKatKarsiligiArsaScraper()

            try:
                # 1. Şehir seçimi (çoklu)
                selected_cities = scraper.get_cities()
                if not selected_cities:
                    print("Şehir seçilemedi!")
                    scraper.close()
                    continue

                # 2. Her şehir için ayrı ayrı scrape yap
                all_results = scraper.scrape_all_cities(selected_cities)

                # 3. Her şehir için ayrı Excel dosyasına kaydet
                if all_results:
                    scraper.save_to_excel_multiple(all_results)
                else:
                    print("Hiç kat karşılığı satılık arsa ilanı bulunamadı!")

            except Exception as e:
                print(f"Ana işlemde hata: {e}")
            finally:
                scraper.close()
        else:
            print("Geçersiz seçim! Lütfen 1 veya 2 girin.")


if __name__ == "__main__":
    main()