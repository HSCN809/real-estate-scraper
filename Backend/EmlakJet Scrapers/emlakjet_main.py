import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# TÜM SCRAPER MODÜLLERİNİ İMPORT ET
from konut_scraper import KonutScraper
from günlük_kiralik_konut_scraper import GunlukKiralikKonutScraper
from arsa_scraper import ArsaScraper
from isyeri_scraper import IsyeriScraper
from turistik_tesis_scraper import TuristikTesisScraper
from kat_karsiligi_arsa_scraper import KatKarsiligiArsaScraper
from devren_isyeri_scraper import DevrenIsyeriScraper

class EmlakJetCategorySelector:
    def __init__(self):
        self.driver = None
        self.selected_locations = {
            'iller': [],
            'ilceler': [], 
            'mahalleler': []
        }
        self.setup_driver()
    
    def setup_driver(self):
        """Chrome driver'ı başlat"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Logları kapat
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-dev-tools")
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 15)
    
    def get_main_categories(self):
        """Ana kategorileri (Satılık, Kiralık) ve alt kategorilerini alır"""
        try:
            print("🔄 EmlakJet ana sayfasına gidiliyor...")
            self.driver.get("https://www.emlakjet.com/")
            time.sleep(3)
            
            categories = {}
            
            # Satılık kategorisini al
            satilik_categories = self.get_category_submenu("Satılık")
            if satilik_categories:
                categories["Satılık"] = satilik_categories
            
            # Kiralık kategorisini al
            kiralik_categories = self.get_category_submenu("Kiralık")
            if kiralik_categories:
                categories["Kiralık"] = kiralik_categories
            
            return categories
            
        except Exception as e:
            print(f"Kategoriler alınırken hata: {e}")
            return {}
    
    def get_category_submenu(self, category_name):
        """Belirtilen ana kategoriye tıklar ve alt kategorileri alır"""
        try:
            # Ana kategori butonunu bul ve tıkla
            category_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    f"//div[@role='button' and contains(text(), '{category_name}')]"))
            )
            category_button.click()
            print(f"✓ {category_name} menüsü açıldı")
            time.sleep(1)
            
            # Alt kategorileri al
            sub_categories = []
            
            # Tüm açık menüleri bul
            sub_menus = self.driver.find_elements(By.CSS_SELECTOR, "ul.styles_wrapper__xd9_i")
            
            # Görünür olan menüyü bul
            visible_menu = None
            for menu in sub_menus:
                if menu.is_displayed():
                    visible_menu = menu
                    break
            
            if visible_menu:
                sub_items = visible_menu.find_elements(By.TAG_NAME, "a")
                for item in sub_items:
                    sub_name = item.text.strip()
                    sub_href = item.get_attribute("href")
                    if sub_name:
                        sub_categories.append({
                            'name': sub_name,
                            'url': sub_href
                        })
                        print(f"  └── {sub_name}")
            
            # Menüyü kapat
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            
            return sub_categories
            
        except Exception as e:
            print(f"{category_name} alt kategorileri alınırken hata: {e}")
            return []
    
    def get_sub_sub_categories(self, current_url):
        """Mevcut sayfadaki alt kategorileri alır - BASİT YAKLAŞIM"""
        try:
            print(f"\n🔍 Alt kategoriler taranıyor...")
            
            # Sayfayı yenile
            self.driver.get(current_url)
            time.sleep(3)
            
            sub_sub_categories = []
            
            # Tüm alt kategori elementlerini bul
            category_elements = self.driver.find_elements(By.CSS_SELECTOR, "ul.styles_ulSubMenu__E0zyf li.styles_subMenu2__BskGl")
            
            for element in category_elements:
                try:
                    # Link elementini bul
                    link = element.find_element(By.TAG_NAME, "a")
                    
                    # Kategori ismini al (ilk span)
                    name_spans = link.find_elements(By.CSS_SELECTOR, "span")
                    if name_spans:
                        category_name = name_spans[0].text.strip()
                    else:
                        category_name = link.text.strip()
                    
                    # URL'yi al
                    category_url = link.get_attribute("href")
                    
                    # İlan sayısını al
                    ad_count = "0"
                    count_spans = link.find_elements(By.CSS_SELECTOR, "span.styles_adCount__M4_Qr")
                    if count_spans:
                        ad_count = count_spans[0].text.strip()
                    
                    if category_name and category_url:
                        # Ana kategorileri filtrele (Konut, Arsa vb.)
                        main_categories = ["Konut", "Arsa", "İşyeri", "Turistik Tesis", "Kat Karşılığı Arsa", "Devren İşyeri"]
                        if category_name not in main_categories:
                            sub_sub_categories.append({
                                'name': category_name,
                                'url': category_url,
                                'ad_count': ad_count
                            })
                            print(f"  └── {category_name} ({ad_count})")
                            
                except Exception as e:
                    continue
            
            return sub_sub_categories
            
        except Exception as e:
            print(f"Alt kategoriler alınırken hata: {e}")
            return []
    
    def get_location_options(self, location_type, current_url):
        """İl, ilçe veya mahalle seçeneklerini alır"""
        try:
            print(f"\n🔍 {location_type} seçenekleri taranıyor...")
            
            # Sayfayı yenile
            self.driver.get(current_url)
            time.sleep(3)
            
            location_options = []
            
            # Lokasyon linklerini bul
            location_links = self.driver.find_elements(By.CSS_SELECTOR, "p.styles_paragraph__QR1cn a.styles_link__7WOOd")
            
            for link in location_links:
                try:
                    location_name = link.text.strip()
                    location_url = link.get_attribute("href")
                    
                    if location_name and location_url:
                        location_options.append({
                            'name': location_name,
                            'url': location_url
                        })
                        print(f"  └── {location_name}")
                        
                except Exception as e:
                    continue
            
            return location_options
            
        except Exception as e:
            print(f"{location_type} seçenekleri alınırken hata: {e}")
            return []
    
    def display_selected_locations(self):
        """Seçilmiş lokasyonları göster"""
        if any(self.selected_locations.values()):
            print(f"\n📍 SEÇİLİ LOKASYONLAR:")
            if self.selected_locations['iller']:
                print(f"   🏙️  İller: {', '.join([il['name'] for il in self.selected_locations['iller']])}")
            if self.selected_locations['ilceler']:
                print(f"   🏘️  İlçeler: {', '.join([ilce['name'] for ilce in self.selected_locations['ilceler']])}")
            if self.selected_locations['mahalleler']:
                print(f"   🏡 Mahalleler: {', '.join([mah['name'] for mah in self.selected_locations['mahalleler']])}")
        else:
            print(f"\n📍 SEÇİLİ LOKASYONLAR: Henüz lokasyon seçilmedi")
    
    def build_final_url(self, base_url):
        """Seçilen lokasyonlara göre final URL oluştur"""
        return base_url
    
    def location_selection_menu(self, current_url, selected_path):
        """İl, ilçe ve mahalle seçim menüsü - ÇOKLU SEÇİM"""
        base_url = current_url
        
        while True:
            print(f"\n🌍 LOKASYON SEÇİMİ - ÇOKLU SEÇİM")
            self.display_selected_locations()
            
            print(f"\n" + "="*50)
            print("🎯 LOKASYON SEÇİM MENÜSÜ")
            print("="*50)
            print("1. 🏙️  İl Ekle")
            print("2. 🏘️  İlçe Ekle") 
            print("3. 🏡 Mahalle Ekle")
            print("4. 🗑️  Seçilmiş Lokasyonları Temizle")
            print("5. ✅ Seçimleri Tamamla ve Devam Et")
            print("6. ↩️  Lokasyon Seçmeden Devam Et")
            print("7. 🚪 Çıkış")
            
            choice = self.get_user_choice(7)
            
            if choice == 1:
                self.add_province_selection(base_url, selected_path)
            elif choice == 2:
                self.add_district_selection(base_url, selected_path)
            elif choice == 3:
                self.add_neighborhood_selection(base_url, selected_path)
            elif choice == 4:
                self.clear_selected_locations()
            elif choice == 5:
                final_url = self.build_final_url(base_url)
                return final_url
            elif choice == 6:
                return base_url
            elif choice == 7:
                print("👋 Çıkış yapılıyor...")
                exit()
            else:
                print("❌ Geçersiz seçim!")
    
    def add_province_selection(self, base_url, selected_path):
        """İl ekleme menüsü - ÇOKLU SEÇİM"""
        print(f"\n🏙️  İL EKLEME - ÇOKLU SEÇİM")
        provinces = self.get_location_options("İller", base_url)
        if not provinces:
            print("❌ İl bulunamadı!")
            return
        
        selected_provinces = self.selected_locations['iller'].copy()
        
        while True:
            print(f"\n" + "="*50)
            print("🎯 İL SEÇİMİ - ÇOKLU SEÇİM")
            print("="*50)
            print("📋 Mevcut Seçimler:")
            if selected_provinces:
                for i, province in enumerate(selected_provinces, 1):
                    print(f"   {i}. {province['name']}")
            else:
                print("   Henüz il seçilmedi")
            
            print(f"\n📝 Seçenekler:")
            for i, province in enumerate(provinces, 1):
                is_selected = any(p['name'] == province['name'] for p in selected_provinces)
                status = "✅" if is_selected else "  "
                print(f"{i}. {status} {province['name']}")
            
            print(f"\n{len(provinces) + 1}. ➕ Tümünü Seç")
            print(f"{len(provinces) + 2}. ➖ Tümünü Kaldır")
            print(f"{len(provinces) + 3}. 🔢 ÇOKLU SEÇİM (numara aralığı)")
            print(f"{len(provinces) + 4}. ✅ Seçimleri Tamamla")
            print(f"{len(provinces) + 5}. ↩️  Üst Menüye Dön")
            
            max_option = len(provinces) + 5
            choice = self.get_user_choice(max_option)
            
            if choice is None:
                continue
                
            if choice == len(provinces) + 1:  # Tümünü seç
                selected_provinces = provinces.copy()
                print("✅ Tüm iller seçildi!")
                
            elif choice == len(provinces) + 2:  # Tümünü kaldır
                selected_provinces = []
                print("✅ Tüm iller kaldırıldı!")
                
            elif choice == len(provinces) + 3:  # Çoklu seçim
                self.multiple_selection_menu(provinces, selected_provinces, "il")
                
            elif choice == len(provinces) + 4:  # Seçimleri tamamla
                self.selected_locations['iller'] = selected_provinces
                print("✅ İl seçimleri kaydedildi!")
                return
                
            elif choice == len(provinces) + 5:  # Üst menüye dön
                return
                
            elif 1 <= choice <= len(provinces):
                selected_province = provinces[choice - 1]
                
                # Seçili mi değil mi kontrol et
                if any(p['name'] == selected_province['name'] for p in selected_provinces):
                    # Zaten seçili, kaldır
                    selected_provinces = [p for p in selected_provinces if p['name'] != selected_province['name']]
                    print(f"❌ {selected_province['name']} kaldırıldı")
                else:
                    # Seçili değil, ekle
                    selected_provinces.append(selected_province)
                    print(f"✅ {selected_province['name']} eklendi")
            else:
                print("❌ Geçersiz seçim!")
    
    def multiple_selection_menu(self, items, selected_items, item_type):
        """Çoklu seçim menüsü"""
        print(f"\n🎯 ÇOKLU {item_type.upper()} SEÇİMİ")
        print("Birden fazla seçim yapmak için numaraları virgülle veya boşlukla ayırarak girin.")
        print("Örnek: 1,3,5 veya 1 3 5 veya 1-5")
        
        while True:
            try:
                user_input = input(f"\nSeçimlerinizi girin (1-{len(items)}): ").strip()
                
                if not user_input:
                    print("❌ Boş giriş! Lütfen numara girin.")
                    continue
                
                # Farklı formatları destekle: "1,3,5", "1 3 5", "1-5"
                selections = set()
                
                # Virgülle ayrılmış
                if ',' in user_input:
                    parts = user_input.split(',')
                    for part in parts:
                        part = part.strip()
                        if '-' in part:
                            # Aralık formatı: 1-5
                            range_parts = part.split('-')
                            if len(range_parts) == 2:
                                start = int(range_parts[0].strip())
                                end = int(range_parts[1].strip())
                                selections.update(range(start, end + 1))
                        else:
                            # Tek numara
                            if part.isdigit():
                                selections.add(int(part))
                
                # Boşlukla ayrılmış
                elif ' ' in user_input:
                    parts = user_input.split()
                    for part in parts:
                        part = part.strip()
                        if '-' in part:
                            # Aralık formatı: 1-5
                            range_parts = part.split('-')
                            if len(range_parts) == 2:
                                start = int(range_parts[0].strip())
                                end = int(range_parts[1].strip())
                                selections.update(range(start, end + 1))
                        else:
                            # Tek numara
                            if part.isdigit():
                                selections.add(int(part))
                
                # Aralık formatı: 1-5
                elif '-' in user_input:
                    range_parts = user_input.split('-')
                    if len(range_parts) == 2:
                        start = int(range_parts[0].strip())
                        end = int(range_parts[1].strip())
                        selections.update(range(start, end + 1))
                
                # Tek numara
                else:
                    if user_input.isdigit():
                        selections.add(int(user_input))
                
                # Seçimleri kontrol et ve uygula
                valid_selections = []
                invalid_selections = []
                
                for selection in selections:
                    if 1 <= selection <= len(items):
                        valid_selections.append(selection)
                    else:
                        invalid_selections.append(selection)
                
                if invalid_selections:
                    print(f"❌ Geçersiz numaralar: {invalid_selections}")
                
                if valid_selections:
                    # Mevcut seçimleri temizle ve yeni seçimleri ekle
                    selected_items.clear()
                    for selection in valid_selections:
                        selected_item = items[selection - 1]
                        selected_items.append(selected_item)
                    
                    print(f"✅ {len(valid_selections)} {item_type} seçildi:")
                    for selection in valid_selections:
                        print(f"   - {items[selection - 1]['name']}")
                    
                    return
                else:
                    print("❌ Geçerli seçim bulunamadı!")
                    
            except ValueError:
                print("❌ Geçersiz giriş! Lütfen numara girin.")
            except Exception as e:
                print(f"❌ Hata: {e}")
    
    def add_district_selection(self, base_url, selected_path):
        """İlçe ekleme menüsü - ÇOKLU SEÇİM"""
        print(f"\n🏘️  İLÇE EKLEME - ÇOKLU SEÇİM")
        
        if not self.selected_locations['iller']:
            print("❌ Önce il seçmelisiniz!")
            return
        
        # Tüm seçili illerin ilçelerini topla
        all_districts = []
        for il in self.selected_locations['iller']:
            print(f"🔍 {il['name']} ilçeleri taranıyor...")
            districts = self.get_location_options("İlçeler", il['url'])
            for district in districts:
                district['il'] = il['name']  # İl bilgisini ekle
                all_districts.append(district)
        
        if not all_districts:
            print("❌ İlçe bulunamadı!")
            return
        
        selected_districts = self.selected_locations['ilceler'].copy()
        
        while True:
            print(f"\n" + "="*50)
            print("🎯 İLÇE SEÇİMİ - ÇOKLU SEÇİM")
            print("="*50)
            print("📋 Mevcut Seçimler:")
            if selected_districts:
                for i, district in enumerate(selected_districts, 1):
                    print(f"   {i}. {district['il']} - {district['name']}")
            else:
                print("   Henüz ilçe seçilmedi")
            
            print(f"\n📝 Seçenekler:")
            for i, district in enumerate(all_districts, 1):
                is_selected = any(d['name'] == district['name'] and d['il'] == district['il'] for d in selected_districts)
                status = "✅" if is_selected else "  "
                print(f"{i}. {status} {district['il']} - {district['name']}")
            
            print(f"\n{len(all_districts) + 1}. ➕ Tümünü Seç")
            print(f"{len(all_districts) + 2}. ➖ Tümünü Kaldır")
            print(f"{len(all_districts) + 3}. 🔢 ÇOKLU SEÇİM (numara aralığı)")
            print(f"{len(all_districts) + 4}. ✅ Seçimleri Tamamla")
            print(f"{len(all_districts) + 5}. ↩️  Üst Menüye Dön")
            
            max_option = len(all_districts) + 5
            choice = self.get_user_choice(max_option)
            
            if choice is None:
                continue
                
            if choice == len(all_districts) + 1:  # Tümünü seç
                selected_districts = all_districts.copy()
                print("✅ Tüm ilçeler seçildi!")
                
            elif choice == len(all_districts) + 2:  # Tümünü kaldır
                selected_districts = []
                print("✅ Tüm ilçeler kaldırıldı!")
                
            elif choice == len(all_districts) + 3:  # Çoklu seçim
                self.multiple_selection_menu(all_districts, selected_districts, "ilçe")
                
            elif choice == len(all_districts) + 4:  # Seçimleri tamamla
                self.selected_locations['ilceler'] = selected_districts
                print("✅ İlçe seçimleri kaydedildi!")
                return
                
            elif choice == len(all_districts) + 5:  # Üst menüye dön
                return
                
            elif 1 <= choice <= len(all_districts):
                selected_district = all_districts[choice - 1]
                
                # Seçili mi değil mi kontrol et
                if any(d['name'] == selected_district['name'] and d['il'] == selected_district['il'] for d in selected_districts):
                    # Zaten seçili, kaldır
                    selected_districts = [d for d in selected_districts if not (d['name'] == selected_district['name'] and d['il'] == selected_district['il'])]
                    print(f"❌ {selected_district['il']} - {selected_district['name']} kaldırıldı")
                else:
                    # Seçili değil, ekle
                    selected_districts.append(selected_district)
                    print(f"✅ {selected_district['il']} - {selected_district['name']} eklendi")
            else:
                print("❌ Geçersiz seçim!")
    
    def add_neighborhood_selection(self, base_url, selected_path):
        """Mahalle ekleme menüsü - ÇOKLU SEÇİM"""
        print(f"\n🏡 MAHALLE EKLEME - ÇOKLU SEÇİM")
        
        if not self.selected_locations['ilceler']:
            print("❌ Önce ilçe seçmelisiniz!")
            return
        
        # Tüm seçili ilçelerin mahallelerini topla
        all_neighborhoods = []
        for ilce in self.selected_locations['ilceler']:
            print(f"🔍 {ilce['il']} - {ilce['name']} mahalleleri taranıyor...")
            neighborhoods = self.get_location_options("Mahalleler", ilce['url'])
            for neighborhood in neighborhoods:
                neighborhood['il'] = ilce['il']
                neighborhood['ilce'] = ilce['name']
                all_neighborhoods.append(neighborhood)
        
        if not all_neighborhoods:
            print("❌ Mahalle bulunamadı!")
            return
        
        selected_neighborhoods = self.selected_locations['mahalleler'].copy()
        
        while True:
            print(f"\n" + "="*50)
            print("🎯 MAHALLE SEÇİMİ - ÇOKLU SEÇİM")
            print("="*50)
            print("📋 Mevcut Seçimler:")
            if selected_neighborhoods:
                for i, neighborhood in enumerate(selected_neighborhoods, 1):
                    print(f"   {i}. {neighborhood['il']} - {neighborhood['ilce']} - {neighborhood['name']}")
            else:
                print("   Henüz mahalle seçilmedi")
            
            print(f"\n📝 Seçenekler:")
            for i, neighborhood in enumerate(all_neighborhoods, 1):
                is_selected = any(n['name'] == neighborhood['name'] and n['ilce'] == neighborhood['ilce'] for n in selected_neighborhoods)
                status = "✅" if is_selected else "  "
                print(f"{i}. {status} {neighborhood['il']} - {neighborhood['ilce']} - {neighborhood['name']}")
            
            print(f"\n{len(all_neighborhoods) + 1}. ➕ Tümünü Seç")
            print(f"{len(all_neighborhoods) + 2}. ➖ Tümünü Kaldır")
            print(f"{len(all_neighborhoods) + 3}. 🔢 ÇOKLU SEÇİM (numara aralığı)")
            print(f"{len(all_neighborhoods) + 4}. ✅ Seçimleri Tamamla")
            print(f"{len(all_neighborhoods) + 5}. ↩️  Üst Menüye Dön")
            
            max_option = len(all_neighborhoods) + 5
            choice = self.get_user_choice(max_option)
            
            if choice is None:
                continue
                
            if choice == len(all_neighborhoods) + 1:  # Tümünü seç
                selected_neighborhoods = all_neighborhoods.copy()
                print("✅ Tüm mahalleler seçildi!")
                
            elif choice == len(all_neighborhoods) + 2:  # Tümünü kaldır
                selected_neighborhoods = []
                print("✅ Tüm mahalleler kaldırıldı!")
                
            elif choice == len(all_neighborhoods) + 3:  # Çoklu seçim
                self.multiple_selection_menu(all_neighborhoods, selected_neighborhoods, "mahalle")
                
            elif choice == len(all_neighborhoods) + 4:  # Seçimleri tamamla
                self.selected_locations['mahalleler'] = selected_neighborhoods
                print("✅ Mahalle seçimleri kaydedildi!")
                return
                
            elif choice == len(all_neighborhoods) + 5:  # Üst menüye dön
                return
                
            elif 1 <= choice <= len(all_neighborhoods):
                selected_neighborhood = all_neighborhoods[choice - 1]
                
                # Seçili mi değil mi kontrol et
                if any(n['name'] == selected_neighborhood['name'] and n['ilce'] == selected_neighborhood['ilce'] for n in selected_neighborhoods):
                    # Zaten seçili, kaldır
                    selected_neighborhoods = [n for n in selected_neighborhoods if not (n['name'] == selected_neighborhood['name'] and n['ilce'] == selected_neighborhood['ilce'])]
                    print(f"❌ {selected_neighborhood['il']} - {selected_neighborhood['ilce']} - {selected_neighborhood['name']} kaldırıldı")
                else:
                    # Seçili değil, ekle
                    selected_neighborhoods.append(selected_neighborhood)
                    print(f"✅ {selected_neighborhood['il']} - {selected_neighborhood['ilce']} - {selected_neighborhood['name']} eklendi")
            else:
                print("❌ Geçersiz seçim!")
    
    def clear_selected_locations(self):
        """Seçilmiş lokasyonları temizle"""
        print(f"\n🗑️  LOKASYONLARI TEMİZLE")
        print("1. 🏙️  Sadece İlleri Temizle")
        print("2. 🏘️  Sadece İlçeleri Temizle") 
        print("3. 🏡 Sadece Mahalleleri Temizle")
        print("4. 💥 Tümünü Temizle")
        print("5. ↩️  İptal")
        
        choice = self.get_user_choice(5)
        
        if choice == 1:
            self.selected_locations['iller'].clear()
            print("✅ İller temizlendi!")
        elif choice == 2:
            self.selected_locations['ilceler'].clear()
            print("✅ İlçeler temizlendi!")
        elif choice == 3:
            self.selected_locations['mahalleler'].clear()
            print("✅ Mahalleler temizlendi!")
        elif choice == 4:
            self.selected_locations = {'iller': [], 'ilceler': [], 'mahalleler': []}
            print("✅ Tüm lokasyonlar temizlendi!")
        elif choice == 5:
            print("İptal edildi.")
        else:
            print("❌ Geçersiz seçim!")
    
    def display_menu(self, title, items, show_back=True, show_exit=True):
        """Menüyü güzel bir şekilde göster"""
        print(f"\n" + "="*50)
        print(f"🎯 {title}")
        print("="*50)

        for i, item in enumerate(items, 1):
            # Eğer item bir sözlükse (alt kategoriler)
            if isinstance(item, dict) and 'name' in item:
                # SADECE alt-alt kategorilerde ilan sayısı göster
                # Ana alt kategorilerde sadece isim göster
                if 'ad_count' in item and item['ad_count'] != "0" and "ALT KATEGORİLERİ" in title:
                    # Name'deki parantez içindeki sayıyı kaldır
                    clean_name = item['name'].split('(')[0].strip()
                    print(f"{i}. {clean_name} İlan Sayısı: {item['ad_count']}")
                else:
                    # Ana alt kategorilerde sadece isim
                    print(f"{i}. {item['name']}")
            # Eğer item string ise (ana kategoriler)
            else:
                print(f"{i}. {item}")

        option_number = len(items) + 1

        if show_back:
            print(f"{option_number}. ↩️ Üst menüye dön")
            option_number += 1

        if show_exit:
            print(f"{option_number}. 🚪 Çıkış")

        return option_number
    
    def get_user_choice(self, max_option):
        """Kullanıcıdan seçim al"""
        try:
            user_input = input(f"\nSeçiminiz (1-{max_option}): ").strip()
            
            # Çoklu seçim için özel kontrol - eğer virgül, boşluk veya tire içeriyorsa None döndür
            if any(char in user_input for char in [',', ' ', '-']):
                return None
                
            choice = int(user_input)
            if 1 <= choice <= max_option:
                return choice
            else:
                print(f"❌ Geçersiz seçim! Lütfen 1-{max_option} arasında bir sayı girin.")
                return None
        except ValueError:
            print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
            return None
    
    def start_appropriate_scraper(self, final_url, category_name, selected_path):
        """Kategoriye uygun scraper'ı başlat"""
        try:
            print(f"\n🚀 Scraper başlatılıyor: {selected_path}")
            print("📍 Seçilen Lokasyonlar:")
            self.display_selected_locations()
            
            # Kategori ismine göre uygun scraper'ı seç
            scraper = None
            
            # KONUT SCRAPER'LARI
            if any(keyword in category_name.lower() for keyword in ['daire', 'konut', 'ev', 'apartman', 'rezidans']):
                if 'günlük' in category_name.lower():
                    scraper = GunlukKiralikKonutScraper(self.driver, final_url, self.selected_locations)
                else:
                    scraper = KonutScraper(self.driver, final_url, self.selected_locations)
            
            # ARSA SCRAPER'LARI
            elif any(keyword in category_name.lower() for keyword in ['arsa', 'tarla', 'arazi']):
                if 'kat karşılığı' in category_name.lower():
                    scraper = KatKarsiligiArsaScraper(self.driver, final_url, self.selected_locations)
                else:
                    scraper = ArsaScraper(self.driver, final_url, self.selected_locations)
            
            # İŞYERİ SCRAPER'LARI
            elif any(keyword in category_name.lower() for keyword in ['işyeri', 'dükkan', 'mağaza', 'ofis', 'plaza']):
                if 'devren' in category_name.lower():
                    scraper = DevrenIsyeriScraper(self.driver, final_url, self.selected_locations)
                else:
                    scraper = IsyeriScraper(self.driver, final_url, self.selected_locations)
            
            # TURİSTİK TESİS
            elif any(keyword in category_name.lower() for keyword in ['turistik', 'otel', 'pansiyon', 'tatil köyü']):
                scraper = TuristikTesisScraper(self.driver, final_url, self.selected_locations)
            
            # Varsayılan olarak genel konut scraper'ı
            else:
                scraper = KonutScraper(self.driver, final_url, self.selected_locations)
                print(f"ℹ️  Varsayılan Konut Scraper kullanılıyor: {category_name}")
            
            if scraper:
                print(f"✅ {scraper.__class__.__name__} başlatılıyor...")
                scraper.start_scraping()
            else:
                print(f"❌ {category_name} kategorisi için uygun scraper bulunamadı!")
                
        except Exception as e:
            print(f"❌ Scraper başlatılırken hata: {e}")
    
    def main_menu(self):
        """Ana menüyü göster ve seçim al"""
        while True:
            print("🔄 Kategoriler taranıyor...")
            categories = self.get_main_categories()
            
            if not categories:
                print("❌ Kategori bulunamadı!")
                return
            
            # Ana kategorileri listele
            main_cats = list(categories.keys())
            max_option = self.display_menu("EMLAKJET KATEGORİLERİ", main_cats, show_back=False)
            
            choice = self.get_user_choice(max_option)
            if choice is None:
                continue
            
            if choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                return
            
            if 1 <= choice <= len(main_cats):
                selected_main = main_cats[choice - 1]
                self.sub_category_menu(categories[selected_main], selected_main)
            else:
                print("❌ Geçersiz seçim!")
    
    def sub_category_menu(self, sub_categories, main_category_name):
        """Alt kategori menüsünü göster"""
        while True:
            max_option = self.display_menu(f"{main_category_name} ALT KATEGORİLERİ", sub_categories)
            
            choice = self.get_user_choice(max_option)
            if choice is None:
                continue
            
            if choice == max_option - 1:  # Üst menüye dön
                return
            elif choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                exit()
            elif 1 <= choice <= len(sub_categories):
                selected_sub = sub_categories[choice - 1]
                print(f"\n✅ Seçilen: {main_category_name} → {selected_sub['name']}")
                self.final_category_menu(selected_sub['url'], selected_sub['name'])
            else:
                print("❌ Geçersiz seçim!")
    
    def final_category_menu(self, category_url, category_name):
        """Son kategori seçim menüsünü göster"""
        # Kategori sayfasına git
        if not self.go_to_selected_category(category_url):
            return
        
        # Alt kategorileri al
        sub_sub_categories = self.get_sub_sub_categories(category_url)
        
        while True:
            if sub_sub_categories:
                max_option = self.display_menu(f"{category_name.upper()} ALT KATEGORİLERİ", sub_sub_categories)
                
                choice = self.get_user_choice(max_option)
                if choice is None:
                    continue
                
                if choice == max_option - 1:  # Üst menüye dön
                    return
                elif choice == max_option:  # Çıkış
                    print("👋 Çıkış yapılıyor...")
                    exit()
                elif 1 <= choice <= len(sub_sub_categories):
                    selected_final = sub_sub_categories[choice - 1]
                    selected_path = f"{category_name} → {selected_final['name']}"
                    print(f"\n✅ Seçilen: {selected_path}")
                    
                    # Seçilen kategoriye git
                    final_url = selected_final['url']
                    self.go_to_selected_category(final_url)
                    
                    # LOKASYON SEÇİMİ (İl, İlçe, Mahalle) - ÇOKLU SEÇİM
                    print(f"\n🌍 LOKASYON SEÇİMİ - ÇOKLU SEÇİM")
                    # Lokasyon seçiminden önce seçilmiş lokasyonları temizle
                    self.selected_locations = {'iller': [], 'ilceler': [], 'mahalleler': []}
                    final_url = self.location_selection_menu(final_url, selected_path)
                    
                    # Scraper'ı başlatma seçeneği
                    print("\n" + "="*50)
                    print("🎯 SCRAPER BAŞLATMA SEÇENEKLERİ")
                    print("="*50)
                    print("1. 🚀 Bu kategoride scraper başlat")
                    print("2. 🔄 Yeni kategori seç")
                    print("3. 🚪 Çıkış")
                    
                    final_choice = self.get_user_choice(3)
                    if final_choice == 1:
                        self.start_appropriate_scraper(final_url, selected_final['name'], selected_path)
                        input("\n⏎ Devam etmek için Enter'a basın...")
                        return
                    elif final_choice == 2:
                        return  # Ana menüye dön
                    else:
                        print("👋 Çıkış yapılıyor...")
                        exit()
                else:
                    print("❌ Geçersiz seçim!")
            else:
                print(f"❌ '{category_name}' kategorisinde alt kategori bulunamadı!")
                
                # Direkt bu kategoride scraper başlatma seçeneği
                print("\n" + "="*50)
                print("🎯 SCRAPER BAŞLATMA SEÇENEKLERİ")
                print("="*50)
                print("1. 🚀 Bu kategoride scraper başlat")
                print("2. 🔄 Yeni kategori seç")
                print("3. 🚪 Çıkış")
                
                final_choice = self.get_user_choice(3)
                if final_choice == 1:
                    selected_path = f"{category_name}"
                    final_url = category_url
                    # Lokasyon seçimi
                    self.selected_locations = {'iller': [], 'ilceler': [], 'mahalleler': []}
                    final_url = self.location_selection_menu(final_url, selected_path)
                    self.start_appropriate_scraper(final_url, category_name, selected_path)
                    input("\n⏎ Devam etmek için Enter'a basın...")
                    return
                elif final_choice == 2:
                    return  # Ana menüye dön
                else:
                    print("👋 Çıkış yapılıyor...")
                    exit()
    
    def go_to_selected_category(self, url):
        """Seçilen kategori sayfasına gider"""
        try:
            print(f"\n🌐 Sayfaya gidiliyor: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            print(f"✅ Başarılı! Geçerli URL: {self.driver.current_url}")
            print(f"📄 Sayfa başlığı: {self.driver.title}")
            
            return True
            
        except Exception as e:
            print(f"❌ Sayfaya gidilirken hata: {e}")
            return False
    
    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()


def main():
    """Ana fonksiyon"""
    selector = None
    try:
        selector = EmlakJetCategorySelector()
        selector.main_menu()
        
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
    
    finally:
        if selector:
            selector.close()


if __name__ == "__main__":
    main()