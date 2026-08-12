# -*- coding: utf-8 -*-
"""HepsiEmlak Arsa parser'ı"""

from typing import Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from .base_parser import BaseHepsiemlakParser


class ArsaParser(BaseHepsiemlakParser):
    """HepsiEmlak arsa ilanları parser'ı"""

    def __init__(self):
        super().__init__("arsa")

    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Arsaya özel verileri çıkar"""
        data = {"arsa_metrekare": "Belirtilmemiş", "metrekare_fiyat": "Belirtilmemiş"}
        data.update(self.extract_spec_map_data(container))
        return data
