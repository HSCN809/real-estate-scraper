import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re


class HepsiemlakSatilikScraper:
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
        
        # Kategori bilgileri
        self.categories = {
            "konut": {"url": "https://www.hepsiemlak.com/satilik", "title": "Satılık Konut"},
            "arsa": {"url": "https://www.hepsiemlak.com/satilik/arsa", "title": "Satılık Arsa"},
            "isyeri": {"url": "https://www.hepsiemlak.com/satilik/isyeri", "title": "Satılık İşyeri"},
            "devremulk": {"url": "https://www.hepsiemlak.com/satilik/devremulk", "title": "Satılık Devremülk"},
            "turistik-isletme": {"url": "https://www.hepsiemlak.com/satilik/turistik-isletme", "title": "Satılık Turistik İşletme"}
        }

    def select_category(self):
        """Kullanıcıdan kategori seçmesini iste"""
        print("\n" + "="*50)
        print("KATEGORİ SEÇİMİ")
        print("="*50)
        
        categories_list = list(self.categories.keys())
        for i, category in enumerate(categories_list, 1):
            print(f"{i}. {self.categories[category]['title']}")
        
        while True:
            try:
                choice = int(input(f"\nLütfen bir kategori numarası seçin (1-{len(categories_list)}): "))
                if 1 <= choice <= len(categories_list):
                    selected_category = categories_list[choice-1]
                    print(f"Seçilen kategori: {self.categories[selected_category]['title']}")
                    return selected_category
                else:
                    print(f"Geçersiz seçim! Lütfen 1-{len(categories_list)} arasında bir numara girin.")
            except ValueError:
                print("Lütfen geçerli bir sayı girin!")

    def get_cities(self, category):
        """Tüm illeri getir ve kullanıcıya çoklu şehir seçtir"""
        print(f"\n{self.categories[category]['title']} sitesine gidiliyor...")
        self.driver.get(self.categories[category]["url"])
        time.sleep(4)

        try:
            # İl seçiniz dropdown'ını bul ve tıkla
            print("Şehir dropdown'ı aranıyor...")
            city_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.he-select-base__container, div[data-name='city']"))
            )
            city_dropdown.click()
            print("Şehir dropdown'ı tıklandı...")
            time.sleep(2)

            # Dropdown container'ını bul
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

            # Tüm şehir list item'larını al
            city_items = self.driver.find_elements(By.CSS_SELECTOR, "li.he-select__list-item, li.he-select-base__list-item")

            cities = []
            for idx, city_item in enumerate(city_items):
                try:
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
                    print(f"\nŞu an seçili şehirler ({len(selected_cities)}): {selected_cities}")
                    option = input("\nSeçenek (1-5): ").strip()
                    
                    if option == "5":
                        if selected_cities:
                            print(f"\nSeçim tamamlandı. Seçilen {len(selected_cities)} şehir: {', '.join(selected_cities)}")
                            # Dropdown'ı kapat
                            try:
                                self.driver.execute_script("document.elementFromPoint(10, 10).click();")
                            except:
                                pass
                            time.sleep(1)
                            return selected_cities
                        else:
                            print("En az bir şehir seçmelisiniz!")
                            continue
                    
                    elif option == "3":
                        # Tüm şehirleri seç
                        selected_cities = cities.copy()
                        print("Tüm şehirler seçildi!")
                        continue
                        
                    elif option == "4":  
                    # ŞEHİR SİLME KODU
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
                        # Tek tek şehir seç
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
        """Tek bir şehir seç - DÜZELTİLDİ"""
        try:
            # Sayfayı yenile ve temiz başla
            self.driver.get(self.categories[self.current_category]["url"])
            time.sleep(3)

            # İl seçiniz dropdown'ını bul ve tıkla
            print(f"{city_name} şehri seçiliyor...")
            city_dropdown = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.he-select-base__container, div[data-name='city']"))
            )
            city_dropdown.click()
            time.sleep(2)

            # Dropdown container'ını bul
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
    
            # Tüm şehir list item'larını al
            city_items = self.driver.find_elements(By.CSS_SELECTOR, "li.he-select__list-item, li.he-select-base__list-item")

            # İstenen şehri bul ve seç
            city_found = False
            for city_item in city_items:
                try:
                    city_link = city_item.find_element(By.CSS_SELECTOR, "a.js-city-filter__list-link, span.he-select-base__text")
                    current_city_name = city_link.text.strip()

                    if current_city_name == city_name:
                        # SADECE BURADA SEÇİM YAP - TEK YER
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

            # Dropdown'ı kapat
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
        """Ara butonuna tıkla ve filtreyi uygula - GÜNCELLENDİ"""
        try:
            # Farklı ara butonu seçenekleri
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
                
                # Sayfanın yüklendiğinden emin ol
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

    def extract_konut_data(self, listing_element):
        """Konut ilanının verilerini çıkar"""
        try:
            data = {}
            # Temel bilgiler
            try:
                price_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-price")
                data["fiyat"] = price_element.text.strip()
            except:
                data["fiyat"] = "Belirtilmemiş"

            try:
                title_element = listing_element.find_element(By.CSS_SELECTOR, "h3")
                data["baslik"] = title_element.text.strip()
            except:
                data["baslik"] = "Belirtilmemiş"

            try:
                location_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-location")
                location_text = location_element.text.strip()
                location_parts = [part.strip() for part in location_text.split('/')]
                data["il"] = location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş"
                data["ilce"] = location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş"
                data["mahalle"] = location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş"
            except:
                data["il"] = data["ilce"] = data["mahalle"] = "Belirtilmemiş"

            try:
                link_element = listing_element.find_element(By.CSS_SELECTOR, "a.card-link")
                data["ilan_linki"] = link_element.get_attribute("href")
            except:
                data["ilan_linki"] = "Belirtilmemiş"

            try:
                date_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-date")
                data["ilan_tarihi"] = date_element.text.strip()
            except:
                data["ilan_tarihi"] = "Belirtilmemiş"

            # Konut özellikleri
            try:
                room_element = listing_element.find_element(By.CSS_SELECTOR, "span.houseRoomCount")
                data["oda_sayisi"] = room_element.text.strip()
            except:
                data["oda_sayisi"] = "Belirtilmemiş"

            try:
                size_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-size")
                data["metrekare"] = size_element.text.strip()
            except:
                data["metrekare"] = "Belirtilmemiş"

            try:
                age_element = listing_element.find_element(By.CSS_SELECTOR, "span.buildingAge")
                data["bina_yasi"] = age_element.text.strip()
            except:
                data["bina_yasi"] = "Belirtilmemiş"

            try:
                floor_element = listing_element.find_element(By.CSS_SELECTOR, "span.floortype")
                data["kat"] = floor_element.text.strip()
            except:
                data["kat"] = "Belirtilmemiş"

            try:
                firm_element = listing_element.find_element(By.CSS_SELECTOR, "p.listing-card--owner-info__firm-name")
                data["emlak_ofisi"] = firm_element.text.strip()
            except:
                data["emlak_ofisi"] = "Belirtilmemiş"

            return data

        except Exception as e:
            print(f"Konut verisi çıkarılırken hata: {e}")
            return None

    def extract_arsa_data(self, listing_element):
        """Arsa ilanının verilerini çıkar"""
        try:
            data = {}
            # Temel bilgiler
            try:
                price_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-price")
                data["fiyat"] = price_element.text.strip()
            except:
                data["fiyat"] = "Belirtilmemiş"

            try:
                title_element = listing_element.find_element(By.CSS_SELECTOR, "h3")
                data["baslik"] = title_element.text.strip()
            except:
                data["baslik"] = "Belirtilmemiş"

            try:
                location_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-location")
                location_text = location_element.text.strip()
                location_parts = [part.strip() for part in location_text.split('/')]
                data["il"] = location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş"
                data["ilce"] = location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş"
                data["mahalle"] = location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş"
            except:
                data["il"] = data["ilce"] = data["mahalle"] = "Belirtilmemiş"

            try:
                link_element = listing_element.find_element(By.CSS_SELECTOR, "a.card-link")
                data["ilan_linki"] = link_element.get_attribute("href")
            except:
                data["ilan_linki"] = "Belirtilmemiş"

            try:
                date_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-date")
                data["ilan_tarihi"] = date_element.text.strip()
            except:
                data["ilan_tarihi"] = "Belirtilmemiş"

            # Arsa özellikleri
            try:
                size_elements = listing_element.find_elements(By.CSS_SELECTOR, "span.celly.squareMeter.list-view-size")
                for size_element in size_elements:
                    size_text = size_element.text.strip()
                    if "m²" in size_text and "TL / m²" not in size_text:
                        data["arsa_metrekare"] = size_text
                    elif "TL / m²" in size_text:
                        data["metrekare_fiyat"] = size_text
            except:
                data["arsa_metrekare"] = "Belirtilmemiş"
                data["metrekare_fiyat"] = "Belirtilmemiş"

            try:
                firm_element = listing_element.find_element(By.CSS_SELECTOR, "p.listing-card--owner-info__firm-name")
                data["emlak_ofisi"] = firm_element.text.strip()
            except:
                data["emlak_ofisi"] = "Belirtilmemiş"

            return data

        except Exception as e:
            print(f"Arsa verisi çıkarılırken hata: {e}")
            return None

    def extract_isyeri_data(self, listing_element):
        """İşyeri ilanının verilerini çıkar"""
        try:
            data = {}
            # Temel bilgiler
            try:
                price_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-price")
                data["fiyat"] = price_element.text.strip()
            except:
                data["fiyat"] = "Belirtilmemiş"

            try:
                title_element = listing_element.find_element(By.CSS_SELECTOR, "h3")
                data["baslik"] = title_element.text.strip()
            except:
                data["baslik"] = "Belirtilmemiş"

            try:
                location_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-location")
                location_text = location_element.text.strip()
                location_parts = [part.strip() for part in location_text.split('/')]
                data["il"] = location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş"
                data["ilce"] = location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş"
                data["mahalle"] = location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş"
            except:
                data["il"] = data["ilce"] = data["mahalle"] = "Belirtilmemiş"

            try:
                link_element = listing_element.find_element(By.CSS_SELECTOR, "a.card-link")
                data["ilan_linki"] = link_element.get_attribute("href")
            except:
                data["ilan_linki"] = "Belirtilmemiş"

            try:
                date_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-date")
                data["ilan_tarihi"] = date_element.text.strip()
            except:
                data["ilan_tarihi"] = "Belirtilmemiş"

            # İşyeri özellikleri
            try:
                size_element = listing_element.find_element(By.CSS_SELECTOR, "span.celly.squareMeter.list-view-size")
                data["metrekare"] = size_element.text.strip()
            except:
                data["metrekare"] = "Belirtilmemiş"

            try:
                firm_element = listing_element.find_element(By.CSS_SELECTOR, "p.listing-card--owner-info__firm-name")
                data["emlak_ofisi"] = firm_element.text.strip()
            except:
                data["emlak_ofisi"] = "Belirtilmemiş"

            return data

        except Exception as e:
            print(f"İşyeri verisi çıkarılırken hata: {e}")
            return None

    def extract_devremulk_data(self, listing_element):
        """Devremülk ilanının verilerini çıkar"""
        try:
            data = {}
            # Temel bilgiler
            try:
                price_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-price")
                data["fiyat"] = price_element.text.strip()
            except:
                data["fiyat"] = "Belirtilmemiş"

            try:
                title_element = listing_element.find_element(By.CSS_SELECTOR, "h3")
                data["baslik"] = title_element.text.strip()
            except:
                data["baslik"] = "Belirtilmemiş"

            try:
                location_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-location")
                location_text = location_element.text.strip()
                location_parts = [part.strip() for part in location_text.split('/')]
                data["il"] = location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş"
                data["ilce"] = location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş"
                data["mahalle"] = location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş"
            except:
                data["il"] = data["ilce"] = data["mahalle"] = "Belirtilmemiş"

            try:
                link_element = listing_element.find_element(By.CSS_SELECTOR, "a.card-link")
                data["ilan_linki"] = link_element.get_attribute("href")
            except:
                data["ilan_linki"] = "Belirtilmemiş"

            try:
                date_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-date")
                data["ilan_tarihi"] = date_element.text.strip()
            except:
                data["ilan_tarihi"] = "Belirtilmemiş"

            # Devremülk özellikleri
            try:
                room_element = listing_element.find_element(By.CSS_SELECTOR, "span.houseRoomCount")
                data["oda_sayisi"] = room_element.text.strip()
            except:
                data["oda_sayisi"] = "Belirtilmemiş"

            try:
                size_element = listing_element.find_element(By.CSS_SELECTOR, "span.celly.squareMeter.list-view-size")
                data["metrekare"] = size_element.text.strip()
            except:
                data["metrekare"] = "Belirtilmemiş"

            try:
                age_element = listing_element.find_element(By.CSS_SELECTOR, "span.buildingAge")
                data["bina_yasi"] = age_element.text.strip()
            except:
                data["bina_yasi"] = "Belirtilmemiş"

            try:
                floor_element = listing_element.find_element(By.CSS_SELECTOR, "span.floortype")
                data["kat"] = floor_element.text.strip()
            except:
                data["kat"] = "Belirtilmemiş"

            return data

        except Exception as e:
            print(f"Devremülk verisi çıkarılırken hata: {e}")
            return None

    def extract_turistik_isletme_data(self, listing_element):
        """Turistik işletme ilanının verilerini çıkar"""
        try:
            data = {}
            # Temel bilgiler
            try:
                price_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-price")
                data["fiyat"] = price_element.text.strip()
            except:
                data["fiyat"] = "Belirtilmemiş"

            try:
                title_element = listing_element.find_element(By.CSS_SELECTOR, "h3")
                data["baslik"] = title_element.text.strip()
            except:
                data["baslik"] = "Belirtilmemiş"

            try:
                location_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-location")
                location_text = location_element.text.strip()
                location_parts = [part.strip() for part in location_text.split('/')]
                data["il"] = location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş"
                data["ilce"] = location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş"
                data["mahalle"] = location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş"
            except:
                data["il"] = data["ilce"] = data["mahalle"] = "Belirtilmemiş"

            try:
                link_element = listing_element.find_element(By.CSS_SELECTOR, "a.card-link")
                data["ilan_linki"] = link_element.get_attribute("href")
            except:
                data["ilan_linki"] = "Belirtilmemiş"

            try:
                date_element = listing_element.find_element(By.CSS_SELECTOR, "span.list-view-date")
                data["ilan_tarihi"] = date_element.text.strip()
            except:
                data["ilan_tarihi"] = "Belirtilmemiş"

            # Turistik işletme özellikleri
            try:
                room_element = listing_element.find_element(By.CSS_SELECTOR, "span.workRoomCount")
                data["oda_sayisi"] = room_element.text.strip()
            except:
                data["oda_sayisi"] = "Belirtilmemiş"

            try:
                start_element = listing_element.find_element(By.CSS_SELECTOR, "span.startCount")
                data["otel_tipi"] = start_element.text.strip()
            except:
                data["otel_tipi"] = "Belirtilmemiş"

            return data

        except Exception as e:
            print(f"Turistik işletme verisi çıkarılırken hata: {e}")
            return None

    def extract_listing_data(self, listing_element, category):
        """Kategoriye göre doğru extract fonksiyonunu çağır"""
        extractors = {
            "konut": self.extract_konut_data,
            "arsa": self.extract_arsa_data,
            "isyeri": self.extract_isyeri_data,
            "devremulk": self.extract_devremulk_data,
            "turistik-isletme": self.extract_turistik_isletme_data
        }
        
        if category in extractors:
            return extractors[category](listing_element)
        else:
            return self.extract_konut_data(listing_element)

    def scrape_page(self, category):
        """Mevcut sayfadaki tüm satılık ilanları scrape et - DÜZELTİLDİ"""
        listings_data = []

        try:
            # İlan container'ını bekle
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-items-container, .search-results"))
            )

            # Tüm ilan elementlerini al - SADECE BİR KEZ
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.listing-item:not(.listing-item--promo)")
            actual_count = len(listing_elements)
            print(f"Bulunan ilan sayısı: {actual_count}")

            for idx, listing_element in enumerate(listing_elements):
                try:
                    listing_data = self.extract_listing_data(listing_element, category)
                    if listing_data:
                        listings_data.append(listing_data)
                    time.sleep(0.05)  # Daha kısa bekleme
                except Exception as e:
                    print(f"İlan {idx} işlenirken hata: {e}")
                    continue

            print(f"Başarıyla işlenen ilan sayısı: {len(listings_data)}")
            return listings_data

        except Exception as e:
            print(f"Sayfa scrape edilirken hata: {e}")
            return []

    def get_total_pages(self):
        """Toplam sayfa sayısını bul"""
        try:
            # Farklı pagination seçenekleri
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

    def go_to_page(self, page_number, category):
        """Belirtilen sayfaya git"""
        try:
            base_url = self.categories[category]["url"]
            if page_number == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page_number}"

            self.driver.get(url)
            time.sleep(4)
            
            # Sayfanın yüklendiğinden emin ol
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-items-container, .listing-item, .search-results"))
            )
            return True
        except Exception as e:
            print(f"Sayfa {page_number} açılırken hata: {e}")
            return False

    def scrape_city_listings(self, category, city):
        """Tek bir şehir için tüm ilanları scrape et - GÜNCELLENDİ"""
        print(f"\n{'='*60}")
        print(f"{city} İÇİN SCRAPING BAŞLIYOR")
        print(f"{'='*60}")
        
        try:
            # Mevcut kategoriyi kaydet
            self.current_category = category
            
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
                    print(f"⚠️  {city} için 0 ilan bulundu, atlanıyor...")
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
                print(f"{city} için hiç ilan bulunamadı veya sayfa sayısı hatalı!")
                return []

            # Kullanıcıdan kaç sayfa scrape edileceğini sor
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
                    if not self.go_to_page(page, category):
                        print(f"Sayfa {page} açılamadı, devam ediliyor...")
                        continue

                page_listings = self.scrape_page(category)
                if page_listings:
                    city_listings.extend(page_listings)
                    print(f"{city} - Sayfa {page} tamamlandı. Toplam ilan: {len(city_listings)}")
                else:
                    print(f"{city} - Sayfa {page}'da ilan bulunamadı")

                if page < pages_to_scrape:
                    time.sleep(3)  # Sayfalar arası bekleme süresini artırdık
            
            print(f"✓ {city} için scraping tamamlandı. Toplam {len(city_listings)} ilan bulundu.")
            return city_listings
            
        except Exception as e:
            print(f"{city} için scraping sırasında hata: {e}")
            return []

    def scrape_all_cities(self, category, selected_cities):
        """Tüm seçilen şehirler için ayrı ayrı scrape yap"""
        all_results = {}
        
        for city in selected_cities:
            city_listings = self.scrape_city_listings(category, city)
            if city_listings:
                all_results[city] = city_listings
            else:
                print(f"{city} için hiç ilan bulunamadı")
            
            # Bir sonraki şehir için bekle
            time.sleep(2)
        
        return all_results

    def save_to_excel_multiple(self, all_results, category):
        """Her şehir için ayrı Excel dosyasına kaydet"""
        if not all_results:
            print("Kaydedilecek veri yok!")
            return

        total_ilan = 0
        category_title = self.categories[category]['title'].replace(' ', '_').lower()
        
        for city, data in all_results.items():
            if data:
                filename = f"hepsiemlak_{city.lower()}_{category_title}.xlsx"
                
                df = pd.DataFrame(data)
                df.to_excel(filename, index=False, engine="openpyxl")
                print(f"✓ {city} verileri {filename} dosyasına kaydedildi! ({len(data)} ilan)")
                total_ilan += len(data)
        
        print(f"\n🎉 TOPLAM: {len(all_results)} şehir için {total_ilan} ilan kaydedildi!")

    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()


def main():
    while True:
        print("\n" + "="*60)
        print("🏠 HEPSİEMLAK SATILIK SCRAPER")
        print("="*60)
        print("1. Scraping işlemi başlat")
        print("2. Çıkış")
        
        choice = input("\nSeçiminiz (1-2): ")
        
        if choice == "2":
            print("Program sonlandırılıyor...")
            break
        elif choice == "1":
            scraper = HepsiemlakSatilikScraper()

            try:
                # 1. Kategori seçimi
                selected_category = scraper.select_category()
                
                # 2. Şehir seçimi (çoklu)
                selected_cities = scraper.get_cities(selected_category)
                if not selected_cities:
                    print("Şehir seçilemedi!")
                    scraper.close()
                    continue

                # 3. Her şehir için ayrı ayrı scrape yap
                all_results = scraper.scrape_all_cities(selected_category, selected_cities)

                # 4. Her şehir için ayrı Excel dosyasına kaydet
                if all_results:
                    scraper.save_to_excel_multiple(all_results, selected_category)
                else:
                    print("Hiç satılık ilan bulunamadı!")

            except Exception as e:
                print(f"Ana işlemde hata: {e}")
            finally:
                scraper.close()
        else:
            print("Geçersiz seçim! Lütfen 1 veya 2 girin.")


if __name__ == "__main__":
    main()