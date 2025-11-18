import time
import json
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

class GunlukKiralikKonutScraper:
    def __init__(self, driver, base_url, selected_locations=None):
        self.driver = driver
        self.base_url = base_url
        self.selected_locations = selected_locations or {'iller': [], 'ilceler': [], 'mahalleler': []}
        self.all_listings = []
        self.wait = WebDriverWait(self.driver, 10)
        
    def get_location_options(self, location_type, current_url):
        """İl, ilçe veya mahalle seçeneklerini alır - EmlakJet Main'den alındı"""
        try:
            print(f"\n🔍 {location_type} seçenekleri taranıyor...")
            
            # Sayfayı yenile
            self.driver.get(current_url)
            time.sleep(3)
            
            location_options = []
            
            # Lokasyon linklerini bul
            location_links = self.driver.find_elements(By.CSS_SELECTOR, "section.styles_section__xzOd3 a.styles_link__7WOOd")
            
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
    
    def get_user_choice(self, max_option):
        """Kullanıcıdan seçim al"""
        try:
            user_input = input(f"\nSeçiminiz (1-{max_option}): ").strip()
            
            # Çoklu seçim için özel kontrol
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
                
                # Farklı formatları destekle
                selections = set()
                
                if ',' in user_input:
                    parts = user_input.split(',')
                    for part in parts:
                        part = part.strip()
                        if '-' in part:
                            range_parts = part.split('-')
                            if len(range_parts) == 2:
                                start = int(range_parts[0].strip())
                                end = int(range_parts[1].strip())
                                selections.update(range(start, end + 1))
                        else:
                            if part.isdigit():
                                selections.add(int(part))
                
                elif ' ' in user_input:
                    parts = user_input.split()
                    for part in parts:
                        part = part.strip()
                        if '-' in part:
                            range_parts = part.split('-')
                            if len(range_parts) == 2:
                                start = int(range_parts[0].strip())
                                end = int(range_parts[1].strip())
                                selections.update(range(start, end + 1))
                        else:
                            if part.isdigit():
                                selections.add(int(part))
                
                elif '-' in user_input:
                    range_parts = user_input.split('-')
                    if len(range_parts) == 2:
                        start = int(range_parts[0].strip())
                        end = int(range_parts[1].strip())
                        selections.update(range(start, end + 1))
                
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
    
    def add_province_selection(self, base_url):
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
                
                if any(p['name'] == selected_province['name'] for p in selected_provinces):
                    selected_provinces = [p for p in selected_provinces if p['name'] != selected_province['name']]
                    print(f"❌ {selected_province['name']} kaldırıldı")
                else:
                    selected_provinces.append(selected_province)
                    print(f"✅ {selected_province['name']} eklendi")
            else:
                print("❌ Geçersiz seçim!")
    
    def add_district_selection(self, base_url):
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
                district['il'] = il['name']
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
                
                if any(d['name'] == selected_district['name'] and d['il'] == selected_district['il'] for d in selected_districts):
                    selected_districts = [d for d in selected_districts if not (d['name'] == selected_district['name'] and d['il'] == selected_district['il'])]
                    print(f"❌ {selected_district['il']} - {selected_district['name']} kaldırıldı")
                else:
                    selected_districts.append(selected_district)
                    print(f"✅ {selected_district['il']} - {selected_district['name']} eklendi")
            else:
                print("❌ Geçersiz seçim!")
    
    def add_neighborhood_selection(self, base_url):
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
                
                if any(n['name'] == selected_neighborhood['name'] and n['ilce'] == selected_neighborhood['ilce'] for n in selected_neighborhoods):
                    selected_neighborhoods = [n for n in selected_neighborhoods if not (n['name'] == selected_neighborhood['name'] and n['ilce'] == selected_neighborhood['ilce'])]
                    print(f"❌ {selected_neighborhood['il']} - {selected_neighborhood['ilce']} - {selected_neighborhood['name']} kaldırıldı")
                else:
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
    
    def location_selection_menu(self):
        """İl, ilçe ve mahalle seçim menüsü - ÇOKLU SEÇİM"""
        base_url = self.base_url
        
        while True:
            print(f"\n🌍 GÜNLÜK KİRALIK KONUT LOKASYON SEÇİMİ - ÇOKLU SEÇİM")
            self.display_selected_locations()
            
            print(f"\n" + "="*50)
            print("🎯 GÜNLÜK KİRALIK KONUT LOKASYON SEÇİM MENÜSÜ")
            print("="*50)
            print("1. 🏙️  İl Ekle")
            print("2. 🏘️  İlçe Ekle") 
            print("3. 🏡 Mahalle Ekle")
            print("4. 🗑️  Seçilmiş Lokasyonları Temizle")
            print("5. ✅ Seçimleri Tamamla ve Scraping'e Başla")
            print("6. ↩️  Lokasyon Seçmeden Scraping'e Başla")
            print("7. 🚪 Çıkış")
            
            choice = self.get_user_choice(7)
            
            if choice == 1:
                self.add_province_selection(base_url)
            elif choice == 2:
                self.add_district_selection(base_url)
            elif choice == 3:
                self.add_neighborhood_selection(base_url)
            elif choice == 4:
                self.clear_selected_locations()
            elif choice == 5:
                return self.build_location_queue()
            elif choice == 6:
                print("ℹ️  Lokasyon seçimi atlandı, varsayılan URL kullanılacak.")
                return [{
                    'type': 'genel',
                    'label': 'Varsayılan Kategori',
                    'url': self.base_url
                }]
            elif choice == 7:
                print("👋 Çıkış yapılıyor...")
                exit()
            else:
                print("❌ Geçersiz seçim!")
    
    def build_location_queue(self):
        """Seçilen tüm lokasyonlar için URL kuyruğu oluştur.
        Öncelik sırası: Mahalle > İlçe > İl (tekrarlayan scrape'leri önlemek için)
        """
        targets = []
        seen_urls = set()
    
        def clean_name(name):
            if not isinstance(name, str):
                return ''
            cleaned = name
            for token in [' Günlük Kiralık Konut', ' Günlük Kiralık', ' Günlük', ' Satılık', ' Kiralık']:
                cleaned = cleaned.replace(token, '')
            return cleaned.strip()
    
        def add_target(url, label, level):
            if not url or url in seen_urls:
                return
            seen_urls.add(url)
            targets.append({
                'type': level,
                'label': label or 'Lokasyon',
                'url': url
            })
    
        def compose_label(parts):
            cleaned_parts = [clean_name(part) for part in parts if part]
            return " / ".join([part for part in cleaned_parts if part]) or 'Lokasyon'
    
        # Öncelik sırası: Mahalle > İlçe > İl
        # Eğer mahalle seçimi varsa, sadece mahalle URL'leri ekle
        if self.selected_locations.get('mahalleler'):
            for neighborhood in self.selected_locations['mahalleler']:
                label = compose_label([neighborhood.get('il'), neighborhood.get('ilce'), neighborhood.get('name')])
                add_target(neighborhood.get('url'), label, 'mahalle')
        
        # Eğer mahalle yok ama ilçe varsa, sadece ilçe URL'leri ekle
        elif self.selected_locations.get('ilceler'):
            for district in self.selected_locations['ilceler']:
                label = compose_label([district.get('il'), district.get('name')])
                add_target(district.get('url'), label, 'ilçe')
        
        # Eğer ilçe ve mahalle yok ama il varsa, sadece il URL'leri ekle
        elif self.selected_locations.get('iller'):
            for province in self.selected_locations['iller']:
                label = compose_label([province.get('name')])
                add_target(province.get('url'), label, 'il')
        
        # Hiçbiri yoksa varsayılan URL
        if not targets:
            add_target(self.base_url, 'Varsayılan Kategori', 'genel')
    
        print(f"\n✅ {len(targets)} lokasyon kuyruğa eklendi.")
        for idx, target in enumerate(targets, 1):
            print(f"   {idx}. {target['label']} -> {target['url']}")
        return targets
        
    def start_scraping(self):
        """Scraping işlemini başlat"""
        print(f"🚀 Günlük Kiralık Konut Scraper başlatılıyor: {self.base_url}")
        
        try:
            # Önce lokasyon seçim menüsünü göster
            print(f"\n📍 GÜNLÜK KİRALIK KONUT İÇİN LOKASYON SEÇİMİ")
            location_queue = self.location_selection_menu()
            if not location_queue:
                print("❌ Lokasyon kuyruğu oluşturulamadı!")
                return
    
            # Kullanıcıdan bir kere sayfa sayısını al
            user_max_pages = self.get_user_page_count()
            if user_max_pages is None:
                print("❌ Scraping iptal edildi!")
                return
    
            total_locations = len(location_queue)
            
            for idx, target in enumerate(location_queue, 1):
                target_url = target.get('url', self.base_url)
                target_label = target.get('label', f"Lokasyon {idx}")
    
                print("\n" + "="*70)
                print(f"📍 {idx}/{total_locations} - {target_label}")
                print(f"🔗 URL: {target_url}")
                print("="*70)
    
                # URL'nin maksimum sayfa sayısını al
                url_max_pages = self.get_max_pages(target_url)
                # Kullanıcının girdiği değer ile URL'nin maksimum sayfa sayısının minimumunu al
                max_pages = min(user_max_pages, url_max_pages)
                
                print(f"📊 Bu lokasyon için {url_max_pages} sayfa bulunuyor. {max_pages} sayfa taranacak.")
    
                # Sayfaları tara
                should_skip = self.scrape_pages(target_url, max_pages)
                if should_skip:
                    print("⏭️  Bu lokasyon atlandı (ilan bulunamadı).")
                    continue
            
            # Verileri kaydet
            self.save_data()
            
            print(f"\n✅ Scraping tamamlandı! Toplam {len(self.all_listings)} ilan bulundu.")
            
        except Exception as e:
            print(f"❌ Scraping sırasında hata: {e}")
    
    def get_user_page_count(self):
        """Kullanıcıdan kaç sayfa taranacağını al (1-50 aralığında)"""
        try:
            while True:
                try:
                    user_input = input(f"\n🔢 Kaç sayfa scrape edilecek? (1-50): ").strip()
                    
                    if not user_input:
                        print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
                        continue
                    
                    page_count = int(user_input)
                    
                    if page_count < 1:
                        print("❌ En az 1 sayfa seçmelisiniz!")
                        continue
                    
                    if page_count > 50:
                        print(f"❌ Maksimum 50 sayfa seçebilirsiniz!")
                        continue
                    
                    print(f"✅ {page_count} sayfa scrape edilecek (her lokasyon için maksimum değer olarak kullanılacak).")
                    return page_count
                    
                except ValueError:
                    print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
                except KeyboardInterrupt:
                    print("\n⏹️  İşlem kullanıcı tarafından iptal edildi.")
                    return None
                    
        except Exception as e:
            print(f"❌ Sayfa sayısı alınırken hata: {e}")
            return 1
    
    def scrape_pages(self, target_url, max_pages):
        """Belirtilen sayıda sayfayı tarar. Eğer ilk sayfada ilan yoksa ve max_pages 1 ise True döndürür (atla)"""
        first_page_listings = 0
        
        for current_page in range(1, max_pages + 1):
            print(f"\n🔍 Sayfa {current_page} taranıyor...")
            
            try:
                # Sayfaya git
                if current_page > 1:
                    separator = '&' if '?' in target_url else '?'
                    page_url = f"{target_url}{separator}sayfa={current_page}"
                else:
                    page_url = target_url
                self.driver.get(page_url)
                time.sleep(2)
                
                # İlanları çek
                listings = self.scrape_current_page()
                self.all_listings.extend(listings)
                
                # İlk sayfadaki ilan sayısını kaydet
                if current_page == 1:
                    first_page_listings = len(listings)
                
                print(f"   ✅ Sayfa {current_page}: {len(listings)} ilan bulundu")
                
            except Exception as e:
                print(f"   ❌ Sayfa {current_page} taranırken hata: {e}")
                continue
        
        # Eğer ilk sayfada hiç ilan yoksa ve maksimum sayfa 1 ise, bu URL'yi atla
        if first_page_listings == 0 and max_pages == 1:
            return True
        
        return False
    
    def get_max_pages(self, target_url):
        """Maksimum sayfa sayısını bul"""
        try:
            self.driver.get(target_url)
            time.sleep(2)
            
            # Sayfalama elementlerini bul
            pagination = self.driver.find_elements(By.CSS_SELECTOR, "ul.styles_list__zqOeW li")
            
            if not pagination:
                return 1
            
            # Sayfa numaralarını topla
            page_numbers = []
            for item in pagination:
                try:
                    # Aktif sayfa
                    active_page = item.find_element(By.CSS_SELECTOR, "span.styles_selected__hilA_")
                    page_numbers.append(int(active_page.text))
                except:
                    pass
                
                try:
                    # Link sayfaları
                    page_link = item.find_element(By.CSS_SELECTOR, "a")
                    page_text = page_link.text
                    if page_text.isdigit():
                        page_numbers.append(int(page_text))
                except:
                    pass
            
            return max(page_numbers) if page_numbers else 1
            
        except Exception as e:
            print(f"❌ Sayfa sayısı alınırken hata: {e}")
            return 1
    
    def scrape_current_page(self):
        """Mevcut sayfadaki ilanları çeker"""
        listings = []
        
        try:
            # İlan container'larını bul
            listing_containers = self.driver.find_elements(By.CSS_SELECTOR, "a.styles_wrapper__587DT")
            
            for container in listing_containers:
                try:
                    listing_data = self.extract_listing_data(container)
                    if listing_data:
                        listings.append(listing_data)
                        
                except Exception:
                    continue
            
        except Exception:
            pass
        
        return listings
    
    def extract_listing_data(self, container):
        """Tek bir ilanın verilerini çıkarır - GÜNLÜK KİRALIK KONUT ÖZEL"""
        try:
            # HTML'DE GÖRDÜĞÜMÜZ TEMEL BİLGİLER
            title = self.get_element_text(container, "h3.styles_title__aKEGQ")
            location = self.get_element_text(container, "span.styles_location__OwJiQ")
            price = self.get_element_text(container, "span.styles_price__F3pMQ")
            
            # Quick info'dan temel detaylar
            quick_info = self.get_element_text(container, "div.styles_quickinfoWrapper__Vsnk5")
            
            # Görsel URL
            image_url = self.get_element_attribute(container, "img.styles_imageClass___SLvt", "src")
            
            # İlan URL
            listing_url = container.get_attribute("href")
            
            # Badge bilgileri
            badges = self.extract_badges(container)
            
            # Günlük kiralık konut özel detayları parse et
            details = self.parse_gunluk_kiralik_konut_details(quick_info, title)
            
            listing_data = {
                'baslik': title,
                'lokasyon': location,
                'fiyat': price,
                'ilan_url': listing_url,
                'resim_url': image_url,
                'one_cikan': 'ÖNE ÇIKAN' in badges,
                'yeni': 'YENİ' in badges,
                'konut_tipi': details['konut_tipi'],
                'oda_sayisi': details['oda_sayisi'],
                'kat': details['kat'],
                'metrekare': details['metrekare'],
                'kiralik_tipi': 'Günlük Kiralık',
                'lukus_durumu': details['lukus_durumu'],
                'tarih': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Temel bilgiler eksikse atla
            if not all([title, location, price]):
                return None
                
            return listing_data
            
        except Exception:
            return None
    
    def parse_gunluk_kiralik_konut_details(self, quick_info, title):
        """Günlük kiralık konut özel detaylarını parse et"""
        details = {
            'konut_tipi': '',
            'oda_sayisi': '',
            'kat': '',
            'metrekare': '',
            'lukus_durumu': ''
        }
        
        # Quick info'dan konut detayları
        if quick_info:
            try:
                # "Daire | 1+1 | 1. Kat | 100 m²" formatını parse et
                parts = [part.strip() for part in quick_info.split('|')]
                
                for part in parts:
                    part_lower = part.lower()
                    
                    # Konut tipi
                    if any(tip in part_lower for tip in ['daire', 'residence', 'villa', 'müstakil', 'apart', 'stüdyo']):
                        details['konut_tipi'] = part
                    
                    # Oda sayısı
                    elif '+' in part:  # 1+1, 2+1 vb.
                        details['oda_sayisi'] = part
                    
                    # Kat bilgisi
                    elif 'kat' in part_lower:
                        details['kat'] = part
                    
                    # Metrekare
                    elif 'm²' in part or 'm2' in part_lower:
                        details['metrekare'] = part
                        
            except:
                pass
        
        # Başlıktan lüks durumu ve diğer bilgiler çıkar
        if title:
            title_lower = title.lower()
            
            # Lüks durumu
            if any(luks in title_lower for luks in ['lüx', 'lux', 'lüks', 'ultra lüx', 'ultra lux', 'premium']):
                details['lukus_durumu'] = 'Lüks'
            elif any(ekonomik in title_lower for ekonomik in ['ekonomik', 'uygun', 'ucuz']):
                details['lukus_durumu'] = 'Ekonomik'
            
            # Konut tipi başlıkta da olabilir
            if not details['konut_tipi']:
                if any(tip in title_lower for tip in ['daire', 'residence', 'villa', 'müstakil', 'apart', 'stüdyo']):
                    for tip in ['Daire', 'Residence', 'Villa', 'Müstakil', 'Apart', 'Stüdyo']:
                        if tip.lower() in title_lower:
                            details['konut_tipi'] = tip
                            break
            
            # Özel özellikler
            if 'deniz manzaralı' in title_lower or 'manzaralı' in title_lower:
                details['lukus_durumu'] = details.get('lukus_durumu', '') + ' Manzaralı'
            if 'havuzlu' in title_lower:
                details['lukus_durumu'] = details.get('lukus_durumu', '') + ' Havuzlu'
        
        return details
    
    def extract_badges(self, container):
        """Badge bilgilerini çıkarır"""
        badges = []
        try:
            badge_elements = container.find_elements(By.CSS_SELECTOR, "div.styles_badgewrapper__pS0rt")
            for badge in badge_elements:
                badge_text = badge.text.strip()
                if badge_text:
                    badges.append(badge_text)
        except:
            pass
        return badges
    
    def get_element_text(self, container, selector):
        """Element metnini al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except:
            return ""
    
    def get_element_attribute(self, container, selector, attribute):
        """Element attribute değerini al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute)
        except:
            return ""
    
    def save_data(self):
        """Verileri JSON ve CSV formatında kaydet"""
        if not self.all_listings:
            print("❌ Kaydedilecek veri bulunamadı!")
            return
        
        # Klasör oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"scraped_gunluk_kiralik_konut_data_{timestamp}"
        os.makedirs(folder_name, exist_ok=True)
        
        # JSON kaydet
        json_filename = os.path.join(folder_name, "gunluk_kiralik_konut_ilanlari.json")
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_listings, f, ensure_ascii=False, indent=2)
        
        # CSV kaydet
        csv_filename = os.path.join(folder_name, "gunluk_kiralik_konut_ilanlari.csv")
        self.save_to_csv(csv_filename)
        
        print(f"💾 Veriler kaydedildi:")
        print(f"   📄 JSON: {json_filename}")
        print(f"   📊 CSV: {csv_filename}")
    
    def save_to_csv(self, filename):
        """Verileri CSV formatında kaydet - GÜNLÜK KİRALIK KONUT ÖZEL"""
        if not self.all_listings:
            return
        
        # Günlük kiralık konut özel sütunlar
        fieldnames = [
            'baslik', 'lokasyon', 'fiyat', 'ilan_url', 'resim_url',
            'one_cikan', 'yeni', 'konut_tipi', 'oda_sayisi', 'kat', 
            'metrekare', 'kiralik_tipi', 'lukus_durumu', 'tarih'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for listing in self.all_listings:
                writer.writerow(listing)

def setup_driver():
    """Chrome driver'ı sessiz modda başlat"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Tüm logları kapat
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-tools")
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

# Test için standalone çalıştırma
def test_scraper():
    """Test fonksiyonu"""
    driver = setup_driver()
    
    try:
        # Test URL'si
        test_url = "https://www.emlakjet.com/gunluk-kiralik-konut"
        
        scraper = GunlukKiralikKonutScraper(driver, test_url)
        scraper.start_scraping()
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_scraper()