"""Çekirdek modül başlatma"""

from .config import (
    EmlakJetConfig,
    HepsiemlakConfig,
    ScraperConfig,
    get_config,
    get_emlakjet_config,
    get_hepsiemlak_config,
)
from .selectors import SELECTORS, get_selectors


# Selenium bağımlı modüller için gecikmeli import
def get_driver_manager():
    from .driver_manager import DriverManager

    return DriverManager


def get_base_scraper():
    from .base_scraper import BaseScraper

    return BaseScraper


__all__ = [
    "SELECTORS",
    "EmlakJetConfig",
    "HepsiemlakConfig",
    "ScraperConfig",
    "get_base_scraper",
    "get_config",
    "get_driver_manager",
    "get_emlakjet_config",
    "get_hepsiemlak_config",
    "get_selectors",
]
