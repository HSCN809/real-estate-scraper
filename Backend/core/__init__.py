# -*- coding: utf-8 -*-
"""
Core module initialization
"""

from .config import (
    ScraperConfig,
    EmlakJetConfig,
    HepsiemlakConfig,
    get_config,
    get_emlakjet_config,
    get_hepsiemlak_config
)
from .selectors import SELECTORS, get_selectors

# Lazy imports for selenium-dependent modules
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
