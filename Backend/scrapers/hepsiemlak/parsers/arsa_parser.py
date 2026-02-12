# -*- coding: utf-8 -*-
"""HepsiEmlak Arsa parser'ı"""

from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class ArsaParser(BaseHepsiemlakParser):
    """HepsiEmlak arsa ilanları parser'ı"""
    
    def __init__(self):
        super().__init__("arsa")
    
    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Arsaya özel verileri çıkar"""
        data = {
            'arsa_metrekare': 'Belirtilmemiş',
            'metrekare_fiyat': 'Belirtilmemiş'
        }
        
        try:
            size_sel = self.selectors.get("size", "span.celly.squareMeter.list-view-size")
            size_elements = container.find_elements(By.CSS_SELECTOR, size_sel)
            
            for size_element in size_elements:
                size_text = size_element.text.strip()
                if "m²" in size_text and "TL / m²" not in size_text:
                    data['arsa_metrekare'] = size_text
                elif "TL / m²" in size_text:
                    data['metrekare_fiyat'] = size_text
        except:
            pass
        
        return data
