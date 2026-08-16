"""HepsiEmlak Turistik İşletme parser'ı"""

from typing import Any

from selenium.webdriver.remote.webelement import WebElement

from .base_parser import BaseHepsiemlakParser


class TuristikParser(BaseHepsiemlakParser):
    """HepsiEmlak turistik işletme ilanları parser'ı"""

    def __init__(self):
        super().__init__("turistik_isletme")

    def extract_category_data(self, container: WebElement) -> dict[str, Any]:
        """Turistik işletmeye özel verileri çıkar"""
        data = {"oda_sayisi": "Belirtilmemiş", "otel_tipi": "Belirtilmemiş"}
        data.update(self.extract_spec_map_data(container))
        return data
