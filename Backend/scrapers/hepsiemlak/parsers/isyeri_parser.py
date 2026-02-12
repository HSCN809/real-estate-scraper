# -*- coding: utf-8 -*-
"""HepsiEmlak İşyeri parser'ı"""

from typing import Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class IsyeriParser(BaseHepsiemlakParser):
    """HepsiEmlak işyeri ilanları parser'ı"""
    
    def __init__(self):
        super().__init__("isyeri")
    
    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """İşyerine özel verileri çıkar"""
        data = {
            'metrekare': 'Belirtilmemiş'
        }
        
        try:
            size_sel = self.selectors.get("size", "span.celly.squareMeter.list-view-size")
            data['metrekare'] = self.get_element_text(container, size_sel) or "Belirtilmemiş"
        except:
            pass
        
        return data
