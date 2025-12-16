# -*- coding: utf-8 -*-
"""
İşyeri (Commercial) parser for HepsiEmlak
"""

from typing import Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class IsyeriParser(BaseHepsiemlakParser):
    """Parser for İşyeri (commercial) listings on HepsiEmlak"""
    
    def __init__(self):
        super().__init__("isyeri")
    
    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Extract isyeri-specific data"""
        data = {
            'metrekare': 'Belirtilmemiş'
        }
        
        try:
            size_sel = self.selectors.get("size", "span.celly.squareMeter.list-view-size")
            data['metrekare'] = self.get_element_text(container, size_sel) or "Belirtilmemiş"
        except:
            pass
        
        return data
