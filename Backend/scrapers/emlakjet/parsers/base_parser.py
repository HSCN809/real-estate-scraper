# -*- coding: utf-8 -*-
"""EmlakJet ilan parser'ı temel sınıfı"""

from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.selectors import get_selectors, get_common_selectors


class BaseEmlakJetParser:
    """EmlakJet ilanları için temel parser"""
    
    PLATFORM = "emlakjet"
    
    def __init__(self, category: str):
        """Parser'ı başlat"""
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
    
    def extract_badges(self, container: WebElement) -> List[str]:
        """İlan rozetlerini çıkar"""
        badges = []
        try:
            badge_selector = self.common_selectors.get("badge_wrapper", "div.styles_badgewrapper__pS0rt")
            badge_elements = container.find_elements(By.CSS_SELECTOR, badge_selector)
            for badge in badge_elements:
                badge_text = badge.text.strip()
                if badge_text:
                    badges.append(badge_text.upper())
        except Exception:
            pass
        return badges
    
    def extract_common_data(self, container: WebElement) -> Dict[str, Any]:
        """İlan konteynerinden ortak verileri çıkar"""
        title_sel = self.common_selectors.get("title", "h3.styles_title__aKEGQ")
        location_sel = self.common_selectors.get("location", "span.styles_location__OwJiQ")
        price_sel = self.common_selectors.get("price", "span.styles_price__F3pMQ")
        quick_info_sel = self.common_selectors.get("quick_info", "div.styles_quickinfoWrapper__Vsnk5")
        image_sel = self.common_selectors.get("image", "img.styles_imageClass___SLvt")
        
        title = self.get_element_text(container, title_sel)
        location = self.get_element_text(container, location_sel)
        price = self.get_element_text(container, price_sel)
        quick_info = self.get_element_text(container, quick_info_sel)
        image_url = self.get_element_attribute(container, image_sel, "src")
        listing_url = container.get_attribute("href") or ""
        
        badges = self.extract_badges(container)
        
        return {
            'baslik': title,
            'lokasyon': location,
            'fiyat': price,
            'ilan_url': listing_url,
            'resim_url': image_url,
            'one_cikan': 'ÖNE ÇIKAN' in badges,
            'yeni': 'YENİ' in badges,
            '_quick_info': quick_info,  # Kategoriye özel parse işlemi için
        }
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Kategori detaylarını parse et, alt sınıflarda override edilmeli"""
        return {}
    
    def extract_listing_data(self, container: WebElement) -> Optional[Dict[str, Any]]:
        """Tam ilan verisini çıkar"""
        try:
            # Ortak verileri al
            data = self.extract_common_data(container)
            
            # Zorunlu alanlar eksikse atla
            if not all([data.get('baslik'), data.get('lokasyon'), data.get('fiyat')]):
                return None
            
            # Kategoriye özel detayları al
            quick_info = data.pop('_quick_info', '')
            category_data = self.parse_category_details(quick_info, data.get('baslik', ''))
            data.update(category_data)
            
            return data
            
        except Exception:
            return None
    
    def get_csv_fields(self) -> List[str]:
        """Bu kategori için CSV alan adlarını getir"""
        return self.selectors.get('csv_fields', [
            'baslik', 'lokasyon', 'fiyat', 'ilan_url', 'resim_url',
            'one_cikan', 'yeni', 'tarih'
        ])
