# -*- coding: utf-8 -*-
"""HepsiEmlak Turistik İşletme parser'ı"""

from typing import Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class TuristikParser(BaseHepsiemlakParser):
    """HepsiEmlak turistik işletme ilanları parser'ı"""
    
    def __init__(self):
        super().__init__("turistik_isletme")
    
    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Turistik işletmeye özel verileri çıkar"""
        data = {
            'oda_sayisi': 'Belirtilmemiş',
            'otel_tipi': 'Belirtilmemiş'
        }
        
        try:
            room_sel = self.selectors.get("room_count", "span.workRoomCount")
            data['oda_sayisi'] = self.get_element_text(container, room_sel) or "Belirtilmemiş"
        except:
            pass
        
        try:
            star_sel = self.selectors.get("star_count", "span.startCount")
            data['otel_tipi'] = self.get_element_text(container, star_sel) or "Belirtilmemiş"
        except:
            pass
        
        return data
