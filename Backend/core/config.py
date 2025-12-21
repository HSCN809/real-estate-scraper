# -*- coding: utf-8 -*-
"""
Configuration management for Real Estate Scraper
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScraperConfig:
    """Main configuration class for scraper settings - STEALTH OPTIMIZED"""
    
    # Timeouts
    page_load_timeout: int = 30
    element_wait_timeout: int = 10  # Düşürüldü (20 -> 10)
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 2.0
    retry_multiplier: float = 2.0  # Exponential backoff
    
    # Rate limiting - OPTIMIZED for speed while avoiding detection
    # Rastgele bekleme aralıkları (saniye) - insan davranışını simüle eder
    wait_between_pages: float = 1.5  # Düşürüldü: 2.0 -> 1.5
    wait_between_requests: float = 0.3  # Düşürüldü: 0.5 -> 0.3
    
    # Rastgele bekleme aralıkları (min, max)
    random_wait_short: tuple = (1.0, 2.0)   # Alt limit artırıldı (0.5 -> 1.0)
    random_wait_medium: tuple = (1.5, 3.5)  # Alt limit artırıldı (1.0 -> 1.5)
    random_wait_long: tuple = (3.0, 6.0)    # Alt limit artırıldı (2.0 -> 3.0)
    
    # Scraping limits
    max_pages_per_location: int = 100  # Artırıldı: 50 -> 100
    default_pages: int = 10  # Artırıldı: 5 -> 10
    
    # Browser settings - STEALTH MODE
    headless: bool = False  # Headless KAPALI - bot tespitinden kaçınmak için
    disable_images: bool = True  # Resimler KAPALI - hız için
    
    # User agent (artık driver_manager.py'de rastgele seçiliyor)
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Output settings
    output_dir: str = "outputs"
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file: str = "logs/scraper.log"


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
