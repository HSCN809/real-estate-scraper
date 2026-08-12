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
        data = {"metrekare": "Belirtilmemiş"}
        data.update(self.extract_spec_map_data(container))
        return data
