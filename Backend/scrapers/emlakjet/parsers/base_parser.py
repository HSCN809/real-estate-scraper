# -*- coding: utf-8 -*-
"""
Base parser for EmlakJet listings
"""

from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.selectors import get_selectors, get_common_selectors


class BaseEmlakJetParser:
    """
    Base parser for EmlakJet listings.
    Provides common element extraction methods.
    """
    
    PLATFORM = "emlakjet"
    
    def __init__(self, category: str):
        """
        Initialize parser.
        
        Args:
            category: Category name ('konut', 'arsa', etc.)
        """
        self.category = category
        self.selectors = get_selectors(self.PLATFORM, category)
        self.common_selectors = get_common_selectors(self.PLATFORM)
    
    def get_element_text(self, container: WebElement, selector: str) -> str:
        """Safely get text from an element"""
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
        """Safely get attribute from an element"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute) or ""
        except NoSuchElementException:
            return ""
    
    def extract_badges(self, container: WebElement) -> List[str]:
        """Extract badge texts from listing"""
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
        """
        Extract common data fields from a listing container.
        
        Args:
            container: WebElement containing the listing
            
        Returns:
            Dictionary with common fields
        """
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
            '_quick_info': quick_info,  # For category-specific parsing
        }
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """
        Parse category-specific details. Override in subclasses.
        
        Args:
            quick_info: Quick info text
            title: Listing title
            
        Returns:
            Dictionary with category-specific fields
        """
        return {}
    
    def extract_listing_data(self, container: WebElement) -> Optional[Dict[str, Any]]:
        """
        Extract complete listing data.
        
        Args:
            container: WebElement containing the listing
            
        Returns:
            Dictionary with all listing data or None if invalid
        """
        try:
            # Get common data
            data = self.extract_common_data(container)
            
            # Skip if missing required fields
            if not all([data.get('baslik'), data.get('lokasyon'), data.get('fiyat')]):
                return None
            
            # Get category-specific details
            quick_info = data.pop('_quick_info', '')
            category_data = self.parse_category_details(quick_info, data.get('baslik', ''))
            data.update(category_data)
            
            return data
            
        except Exception:
            return None
    
    def get_csv_fields(self) -> List[str]:
        """Get CSV field names for this category"""
        return self.selectors.get('csv_fields', [
            'baslik', 'lokasyon', 'fiyat', 'ilan_url', 'resim_url',
            'one_cikan', 'yeni', 'tarih'
        ])
