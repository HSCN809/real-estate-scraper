"""HepsiEmlak Devremülk parser'ı"""

from typing import Any

from selenium.webdriver.remote.webelement import WebElement

from .base_parser import BaseHepsiemlakParser


class DevremulkParser(BaseHepsiemlakParser):
    """HepsiEmlak devremülk ilanları parser'ı"""

    def __init__(self):
        super().__init__("devremulk")

    def extract_category_data(self, container: WebElement) -> dict[str, Any]:
        """Devremülke özel verileri çıkar"""
        data = {
            "oda_sayisi": "Belirtilmemiş",
            "metrekare": "Belirtilmemiş",
            "bina_yasi": "Belirtilmemiş",
            "kat": "Belirtilmemiş",
        }
        data.update(self.extract_spec_map_data(container))
        return data
