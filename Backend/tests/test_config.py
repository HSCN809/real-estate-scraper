# -*- coding: utf-8 -*-
"""core/config.py birim testleri"""

import sys
import os
import pytest

# Üst dizini import yoluna ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config import (
    ScraperConfig,
    EmlakJetConfig,
    HepsiemlakConfig,
    get_config,
    get_emlakjet_config,
    get_hepsiemlak_config
)


class TestScraperConfig:
    """ScraperConfig testleri"""

    def test_default_values(self):
        """Varsayılan yapılandırma değerlerini test et"""
        config = ScraperConfig()

        assert config.page_load_timeout == 15
        assert config.element_wait_timeout == 10
        assert config.max_retries == 3
        assert config.headless == False
        assert config.max_pages_per_location == 50

    def test_custom_values(self):
        """Özel yapılandırma değerlerini test et"""
        config = ScraperConfig(
            page_load_timeout=30,
            headless=False,
            max_retries=5
        )

        assert config.page_load_timeout == 30
        assert config.headless == False
        assert config.max_retries == 5


class TestEmlakJetConfig:
    """EmlakJetConfig testleri"""

    def test_base_url(self):
        """EmlakJet temel URL'ini test et"""
        config = EmlakJetConfig()
        assert config.base_url == "https://www.emlakjet.com"

    def test_categories_exist(self):
        """Kategorilerin tanımlı olduğunu test et"""
        config = EmlakJetConfig()

        assert "satilik" in config.categories
        assert "kiralik" in config.categories

        assert "konut" in config.categories["satilik"]
        assert "arsa" in config.categories["satilik"]

    def test_category_paths(self):
        """Kategori URL yollarını test et"""
        config = EmlakJetConfig()

        assert config.categories["satilik"]["konut"] == "/satilik-konut"
        assert config.categories["satilik"]["arsa"] == "/satilik-arsa"


class TestHepsiemlakConfig:
    """HepsiemlakConfig testleri"""

    def test_base_url(self):
        """Hepsiemlak temel URL'ini test et"""
        config = HepsiemlakConfig()
        assert config.base_url == "https://www.hepsiemlak.com"

    def test_categories_exist(self):
        """Kategorilerin tanımlı olduğunu test et"""
        config = HepsiemlakConfig()

        assert "satilik" in config.categories
        assert "kiralik" in config.categories

        assert "konut" in config.categories["satilik"]
        assert "arsa" in config.categories["satilik"]
        assert "devremulk" in config.categories["satilik"]


class TestGlobalFunctions:
    """Global yapılandırma fonksiyon testleri"""

    def test_get_config(self):
        """get_config'in ScraperConfig döndürdüğünü test et"""
        config = get_config()
        assert isinstance(config, ScraperConfig)

    def test_get_emlakjet_config(self):
        """get_emlakjet_config'in EmlakJetConfig döndürdüğünü test et"""
        config = get_emlakjet_config()
        assert isinstance(config, EmlakJetConfig)

    def test_get_hepsiemlak_config(self):
        """get_hepsiemlak_config'in HepsiemlakConfig döndürdüğünü test et"""
        config = get_hepsiemlak_config()
        assert isinstance(config, HepsiemlakConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
