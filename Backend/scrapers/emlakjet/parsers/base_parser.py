"""EmlakJet ilan parser'ı temel sınıfı"""

import os
import sys
from typing import Any

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from core.selectors import get_common_selectors, get_selectors


class BaseEmlakJetParser:
    """EmlakJet ilanları için temel parser"""

    PLATFORM = "emlakjet"

    def __init__(self, category: str):
        """Parser'ı başlat"""
        self.category = category
        self.selectors = get_selectors(self.PLATFORM, category)
        self.common_selectors = get_common_selectors(self.PLATFORM)

    def get_elements_text(self, container: WebElement, selector: str) -> list[str]:
        """Elementlerin metinlerini güvenli şekilde liste olarak al"""
        try:
            elements = container.find_elements(By.CSS_SELECTOR, selector)
            return [element.text.strip() for element in elements]
        except Exception:  # nosec
            return []

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

    def extract_badges(self, container: WebElement) -> list[str]:
        """İlan rozetlerini çıkar"""
        badges = []
        try:
            badge_selector = self.common_selectors.get(
                "badge_wrapper", "span[class*='px-2 py-0.5']"
            )
            badge_elements = container.find_elements(By.CSS_SELECTOR, badge_selector)
            for badge in badge_elements:
                badge_text = badge.text.strip()
                if badge_text:
                    badges.append(badge_text.upper())
        except Exception:  # nosec
            pass
        return badges

    def extract_common_data(self, container: WebElement) -> dict[str, Any]:
        """İlan konteynerinden ortak verileri çıkar"""
        title_sel = self.common_selectors.get("title", "h3[data-listing-title] a")
        location_sel = self.common_selectors.get("location", "p.text-xs")
        price_sel = self.common_selectors.get(
            "price", "span.shrink-0.whitespace-nowrap"
        )
        quick_info_sel = self.common_selectors.get("quick_info", "p.text-xs")
        image_sel = self.common_selectors.get("image", "img[src*='/listing/']")

        title = self.get_element_text(container, title_sel)
        location = self.get_element_text(container, location_sel)
        price = self.get_element_text(container, price_sel)

        # Yeni yapı: konum 1. p.text-xs, özellikler 2. p.text-xs
        quick_info = ""
        text_elements = self.get_elements_text(container, quick_info_sel)
        if len(text_elements) > 1:
            quick_info = text_elements[1]

        image_url = self.get_element_attribute(container, image_sel, "src")
        listing_url = self.get_element_attribute(container, title_sel, "href")

        badges = self.extract_badges(container)

        return {
            "baslik": title,
            "lokasyon": location,
            "fiyat": price,
            "ilan_url": listing_url,
            "resim_url": image_url,
            "one_cikan": "ÖNE ÇIKAN" in badges,
            "yeni": "YENİ" in badges,
            "_quick_info": quick_info,  # Kategoriye özel parse işlemi için
        }

    def parse_category_details(self, quick_info: str, title: str) -> dict[str, Any]:
        """Kategori detaylarını parse et, alt sınıflarda override edilmeli"""
        return {}

    def extract_listing_data(self, container: WebElement) -> dict[str, Any] | None:
        """Tam ilan verisini çıkar"""
        try:
            # Ortak verileri al
            data = self.extract_common_data(container)

            # Zorunlu alanlar eksikse atla
            if not all([data.get("baslik"), data.get("lokasyon"), data.get("fiyat")]):
                return None

            # Kategoriye özel detayları al
            quick_info = data.pop("_quick_info", "")
            category_data = self.parse_category_details(
                quick_info, data.get("baslik", "")
            )
            data.update(category_data)

            return data

        except Exception:
            return None

    def get_csv_fields(self) -> list[str]:
        """Bu kategori için CSV alan adlarını getir"""
        return self.selectors.get(
            "csv_fields",
            [
                "baslik",
                "lokasyon",
                "fiyat",
                "ilan_url",
                "resim_url",
                "one_cikan",
                "yeni",
                "tarih",
            ],
        )
