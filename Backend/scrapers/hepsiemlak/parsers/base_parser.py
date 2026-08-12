# -*- coding: utf-8 -*-
"""HepsiEmlak ilanları için temel parser"""

from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from core.selectors import get_selectors, get_common_selectors


class BaseHepsiemlakParser:
    """HepsiEmlak ilanları için temel parser; ortak element çıkarma metotları sağlar"""

    PLATFORM = "hepsiemlak"

    def __init__(self, category: str):
        """Parser'ı başlat; category parametresi kategori adını alır ('konut', 'arsa' vb.)"""
        self.category = category
        self.selectors = get_selectors(self.PLATFORM, category)
        self.common_selectors = get_common_selectors(self.PLATFORM)

    def get_element_text(self, container: WebElement, selector: str) -> str:
        """Elementten güvenli şekilde metin al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except NoSuchElementException:
            return ""

    def get_element_attribute(
        self, container: WebElement, selector: str, attribute: str
    ) -> str:
        """Elementten güvenli şekilde attribute al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute) or ""
        except NoSuchElementException:
            return ""

    def extract_common_data(self, container: WebElement) -> Dict[str, Any]:
        """İlan konteynerinden ortak veri alanlarını çıkar"""
        price_sel = self.common_selectors.get("price", "p.listingCard__price")
        title_sel = self.common_selectors.get("title", "h3.listingCard__title")
        date_sel = self.common_selectors.get("date", "time.listingCard__date")
        link_sel = self.common_selectors.get("link", "a.card-link")
        firm_sel = self.common_selectors.get("firm", "p.listingCard__owner-firm")

        price = self.get_element_text(container, price_sel)
        title = self.get_element_text(container, title_sel)
        date = self.get_element_text(container, date_sel)
        link = self.get_element_attribute(container, link_sel, "href")
        firm = self.get_element_text(container, firm_sel)

        # Lokasyon için birden fazla seçici dene (HepsiEmlak HTML yapısı değişkenlik gösterir)
        location_selectors = [
            "span.listingCard__location address",
            "span.list-view-location address",
            "span.list-view-location",
            ".list-view-location address",
            ".list-view-location",
            "address",
        ]
        location_text = ""
        for loc_sel in location_selectors:
            location_text = self.get_element_text(container, loc_sel)
            if location_text and "/" in location_text:
                break

        # Lokasyonu parse et - format: "İl / İlçe / Mahalle"
        location_parts = [p.strip() for p in location_text.split("/") if p.strip()]

        return {
            "fiyat": price or "Belirtilmemiş",
            "baslik": title or "Belirtilmemiş",
            "il": location_parts[0] if len(location_parts) > 0 else "Belirtilmemiş",
            "ilce": location_parts[1] if len(location_parts) > 1 else "Belirtilmemiş",
            "mahalle": location_parts[2]
            if len(location_parts) > 2
            else "Belirtilmemiş",
            "ilan_linki": link or "Belirtilmemiş",
            "ilan_tarihi": date or "Belirtilmemiş",
            "emlak_ofisi": firm or "Belirtilmemiş",
        }

    def extract_spec_values(self, container: WebElement) -> Dict[str, str]:
        """dl/dt/dd yapısındaki özellikleri label->value haritası olarak çıkar"""
        values: Dict[str, str] = {}
        try:
            spec_items = container.find_elements(
                By.CSS_SELECTOR,
                self.common_selectors.get(
                    "specs", "dl.listingCard__specs div.listingCard__spec-item"
                ),
            )
            for item in spec_items:
                try:
                    label = item.find_element(
                        By.CSS_SELECTOR,
                        self.common_selectors.get(
                            "spec_label", "dt.listingCard__spec-label"
                        ),
                    ).text.strip()
                    value = item.find_element(
                        By.CSS_SELECTOR,
                        self.common_selectors.get("spec_value", "dd"),
                    ).text.strip()
                except NoSuchElementException:
                    continue
                if label and value:
                    values[label] = value
        except Exception:  # nosec
            pass
        return values

    def extract_spec_map_data(self, container: WebElement) -> Dict[str, Any]:
        """spec_map yapılandırmasına göre kategori alanlarını çıkar"""
        spec_map = self.selectors.get("spec_map")
        if not spec_map:
            return {}
        values = self.extract_spec_values(container)
        data: Dict[str, Any] = {}
        for field, labels in spec_map.items():
            data[field] = next(
                (values[label] for label in labels if label in values),
                "Belirtilmemiş",
            )
        return data

    def extract_category_data(self, container: WebElement) -> Dict[str, Any]:
        """Kategoriye özel verileri çıkar; alt sınıflarda override edilmeli"""
        return {}

    def extract_listing_data(self, container: WebElement) -> Optional[Dict[str, Any]]:
        """Tam ilan verisini çıkar; geçersizse None döndürür"""
        try:
            # Ortak verileri al
            data = self.extract_common_data(container)

            # Kategoriye özel verileri al
            category_data = self.extract_category_data(container)
            data.update(category_data)

            return data

        except Exception:
            return None

    def get_csv_fields(self) -> List[str]:
        """Bu kategori için CSV alan adlarını getir"""
        return self.selectors.get(
            "csv_fields",
            [
                "fiyat",
                "baslik",
                "il",
                "ilce",
                "mahalle",
                "ilan_linki",
                "ilan_tarihi",
                "emlak_ofisi",
            ],
        )
