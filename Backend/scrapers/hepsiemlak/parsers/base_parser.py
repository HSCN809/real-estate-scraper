# -*- coding: utf-8 -*-
"""HepsiEmlak ilanları için temel parser"""

from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.selectors import get_selectors, get_common_selectors


class BaseHepsiemlakParser:
    """HepsiEmlak ilanları için temel parser; ortak element çıkarma metotları sağlar"""
    
    PLATFORM = "hepsiemlak"
    
    def __init__(self, category: str):
        """Parser'ı başlat; category parametresi kategori adını alır ('konut', 'arsa' vb.)"""
        self.category = category
        self.selectors = get_selectors(self.PLATFORM, category)
        self.common_selectors = get_common_selectors(self.PLATFORM)
    
    def get_element_text(self, container: WebElement, selector: str) -> str:
        """Elementten güvenli şekilde metin al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except NoSuchElementException:
            return ""
    
    def get_element_attribute(
        self,
        container: WebElement,
        selector: str,
        attribute: str
    ) -> str:
        """Elementten güvenli şekilde attribute al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute) or ""
        except NoSuchElementException:
            return ""
    
    def extract_common_data(self, container: WebElement) -> Dict[str, Any]:
        """İlan konteynerinden ortak veri alanlarını çıkar"""
        price_sel = self.common_selectors.get("price", "span.list-view-price")
        title_sel = self.common_selectors.get("title", "h3")
        date_sel = self.common_selectors.get("date", "span.list-view-date")
        link_sel = self.common_selectors.get("link", "a.card-link")
        firm_sel = self.common_selectors.get("firm", "p.listing-card--owner-info__firm-name")

        price = self.get_element_text(container, price_sel)
        title = self.get_element_text(container, title_sel)
        date = self.get_element_text(container, date_sel)
        link = self.get_element_attribute(container, link_sel, "href")
        firm = self.get_element_text(container, firm_sel)

        # Lokasyon için birden fazla seçici dene (HepsiEmlak HTML yapısı değişkenlik gösterir)
        location_selectors = [
            "span.list-view-location address",
            "span.list-view-location",
            ".list-view-location address",
            ".list-view-location",
            "address"
        ]
        location_text = ""
        for loc_sel in location_selectors:
            location_text = self.get_element_text(container, loc_sel)
            if location_text and "/" in location_text:
                break

        # Lokasyonu parse et - format: "İl / İlçe / Mahalle"
        location_parts = [p.strip() for p in location_text.split('/') if p.strip()]

        return {
            'fiyat': price or "Belirtilmemiş",
            'baslik': title or "Belirtilmemiş",
            'il': location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş",
            'ilce': location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş",
            'mahalle': location_parts[2] if len(location_parts) > 2 else "Belirtilmemiş",
            'ilan_linki': link or "Belirtilmemiş",
            'ilan_tarihi': date or "Belirtilmemiş",
            'emlak_ofisi': firm or "Belirtilmemiş",
        }
    
    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Kategoriye özel verileri çıkar; alt sınıflarda override edilmeli"""
        return {}
    
    def extract_listing_data(self, container: WebElement) -> Optional[Dict[str, Any]]:
        """Tam ilan verisini çıkar; geçersizse None döndürür"""
        try:
            # Ortak verileri al
            data = self.extract_common_data(container)
            
            # Kategoriye özel verileri al
            category_data = self.extract_category_data(container)
            data.update(category_data)
            
            return data
            
        except Exception:
            return None
    
    def get_csv_fields(self) -> List[str]:
        """Bu kategori için CSV alan adlarını getir"""
        return self.selectors.get('csv_fields', [
            'fiyat', 'baslik', 'il', 'ilce', 'mahalle',
            'ilan_linki', 'ilan_tarihi', 'emlak_ofisi'
        ])
