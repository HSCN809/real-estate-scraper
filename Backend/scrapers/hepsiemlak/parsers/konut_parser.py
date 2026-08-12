# -*- coding: utf-8 -*-
"""HepsiEmlak Konut parser'ı"""

from typing import Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class KonutParser(BaseHepsiemlakParser):
    """HepsiEmlak konut ilanları parser'ı"""

    def __init__(self):
        super().__init__("konut")

    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Konuta özel verileri çıkar"""
        data = {
            "oda_sayisi": "Belirtilmemiş",
            "metrekare": "Belirtilmemiş",
            "bina_yasi": "Belirtilmemiş",
            "kat": "Belirtilmemiş",
        }
        data.update(self.extract_spec_map_data(container))
        return data
