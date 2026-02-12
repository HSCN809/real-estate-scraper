# -*- coding: utf-8 -*-
"""Çekirdek modül başlatma"""

from .config import (
    ScraperConfig,
    EmlakJetConfig,
    HepsiemlakConfig,
    get_config,
    get_emlakjet_config,
    get_hepsiemlak_config
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
    'ScraperConfig',
    'EmlakJetConfig', 
    'HepsiemlakConfig',
    'get_config',
    'get_emlakjet_config',
    'get_hepsiemlak_config',
    'SELECTORS',
    'get_selectors',
    'get_driver_manager',
    'get_base_scraper'
]
