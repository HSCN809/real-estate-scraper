# -*- coding: utf-8 -*-
"""
Konut (Housing) parser for HepsiEmlak
"""

from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class KonutParser(BaseHepsiemlakParser):
    """Parser for Konut (housing) listings on HepsiEmlak"""
    
    def __init__(self):
        super().__init__("konut")
    
    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Extract konut-specific data"""
        data = {
            'oda_sayisi': 'Belirtilmemiş',
            'metrekare': 'Belirtilmemiş',
            'bina_yasi': 'Belirtilmemiş',
            'kat': 'Belirtilmemiş'
        }
        
        try:
            room_sel = self.selectors.get("room_count", "span.houseRoomCount")
            data['oda_sayisi'] = self.get_element_text(container, room_sel) or "Belirtilmemiş"
        except:
            pass
        
        try:
            size_sel = self.selectors.get("size", "span.list-view-size")
            data['metrekare'] = self.get_element_text(container, size_sel) or "Belirtilmemiş"
        except:
            pass
        
        try:
            age_sel = self.selectors.get("building_age", "span.buildingAge")
            data['bina_yasi'] = self.get_element_text(container, age_sel) or "Belirtilmemiş"
        except:
            pass
        
        try:
            floor_sel = self.selectors.get("floor", "span.floortype")
            data['kat'] = self.get_element_text(container, floor_sel) or "Belirtilmemiş"
        except:
            pass
        
        return data
