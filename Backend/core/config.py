# -*- coding: utf-8 -*-
"""
Configuration management for Real Estate Scraper
Environment variable destekli konfigürasyon
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


def get_bool_env(key: str, default: bool) -> bool:
    """Environment variable'dan boolean değer al"""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def get_int_env(key: str, default: int) -> int:
    """Environment variable'dan integer değer al"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_float_env(key: str, default: float) -> float:
    """Environment variable'dan float değer al"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass
class ScraperConfig:
    """Main configuration class for scraper settings - STEALTH OPTIMIZED"""

    # Timeouts
    page_load_timeout: int = field(default_factory=lambda: get_int_env('CHROME_TIMEOUT', 30))
    element_wait_timeout: int = 10

    # Retry settings
    max_retries: int = field(default_factory=lambda: get_int_env('SCRAPER_MAX_RETRIES', 3))
    retry_delay: float = 2.0
    retry_multiplier: float = 2.0  # Exponential backoff

    # Rate limiting - OPTIMIZED for speed while avoiding detection
    wait_between_pages: float = field(default_factory=lambda: get_float_env('SCRAPER_PAGE_DELAY', 1.5))
    wait_between_requests: float = 0.3

    # Rastgele bekleme aralıkları (min, max)
    random_wait_short: tuple = (1.0, 2.0)
    random_wait_medium: tuple = (1.5, 3.5)
    random_wait_long: tuple = (3.0, 6.0)

    # Scraping limits
    max_pages_per_location: int = 100
    default_pages: int = 10

    # Browser settings - STEALTH MODE
    # Docker'da CHROME_HEADLESS=true olmalı
    headless: bool = field(default_factory=lambda: get_bool_env('CHROME_HEADLESS', False))
    disable_images: bool = True

    # User agent
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Output settings
    output_dir: str = field(default_factory=lambda: os.getenv('OUTPUT_DIR', 'outputs'))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    log_to_file: bool = True
    log_file: str = field(default_factory=lambda: os.getenv('LOG_FILE', 'logs/scraper.log'))


@dataclass
class EmlakJetConfig:
    """EmlakJet specific configuration"""
    base_url: str = "https://www.emlakjet.com"
    
    categories: dict = field(default_factory=lambda: {
        "satilik": {
            "konut": "/satilik-konut",
            "arsa": "/satilik-arsa", 
            "isyeri": "/satilik-isyeri",
            "turistik_tesis": "/satilik-turistik-tesis",
            "kat_karsiligi_arsa": "/satilik-kat-karsiligi-arsa",
            "devren_isyeri": "/devren-isyeri"
        },
        "kiralik": {
            "konut": "/kiralik-konut",
            "gunluk_kiralik": "/gunluk-kiralik",
            "arsa": "/kiralik-arsa",
            "isyeri": "/kiralik-isyeri",
            "turistik_tesis": "/kiralik-turistik-tesis"
        }
    })


@dataclass
class HepsiemlakConfig:
    """Hepsiemlak specific configuration"""
    base_url: str = "https://www.hepsiemlak.com"
    
    categories: dict = field(default_factory=lambda: {
        "satilik": {
            "konut": "/satilik",
            "arsa": "/satilik/arsa",
            "isyeri": "/satilik/isyeri",
            "devremulk": "/satilik/devremulk",
            "turistik_isletme": "/satilik/turistik-isletme"
        },
        "kiralik": {
            "konut": "/kiralik",
            "arsa": "/kiralik/arsa",
            "isyeri": "/kiralik/isyeri",
            "devremulk": "/kiralik/devremulk",
            "turistik_isletme": "/kiralik/turistik-isletme"
        }
    })
    # Not: Subcategories artık dinamik olarak websiteden çekiliyor
    # Bkz: scrapers/hepsiemlak/subtype_fetcher.py


# Global config instance
config = ScraperConfig()
emlakjet_config = EmlakJetConfig()
hepsiemlak_config = HepsiemlakConfig()


def get_config() -> ScraperConfig:
    """Get the global scraper configuration"""
    return config


def get_emlakjet_config() -> EmlakJetConfig:
    """Get EmlakJet configuration"""
    return emlakjet_config


def get_hepsiemlak_config() -> HepsiemlakConfig:
    """Get Hepsiemlak configuration"""
    return hepsiemlak_config
