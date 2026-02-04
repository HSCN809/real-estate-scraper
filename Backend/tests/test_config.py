# -*- coding: utf-8 -*-
"""
Unit tests for core/config.py
"""

import sys
import os
import pytest

# Add parent directory to path
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
    """Tests for ScraperConfig"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = ScraperConfig()
        
        assert config.page_load_timeout == 15
        assert config.element_wait_timeout == 10
        assert config.max_retries == 3
        assert config.headless == False
        assert config.max_pages_per_location == 50
    
    def test_custom_values(self):
        """Test custom configuration values"""
        config = ScraperConfig(
            page_load_timeout=30,
            headless=False,
            max_retries=5
        )
        
        assert config.page_load_timeout == 30
        assert config.headless == False
        assert config.max_retries == 5


class TestEmlakJetConfig:
    """Tests for EmlakJetConfig"""
    
    def test_base_url(self):
        """Test EmlakJet base URL"""
        config = EmlakJetConfig()
        assert config.base_url == "https://www.emlakjet.com"
    
    def test_categories_exist(self):
        """Test that categories are defined"""
        config = EmlakJetConfig()
        
        assert "satilik" in config.categories
        assert "kiralik" in config.categories
        
        assert "konut" in config.categories["satilik"]
        assert "arsa" in config.categories["satilik"]
    
    def test_category_paths(self):
        """Test category URL paths"""
        config = EmlakJetConfig()
        
        assert config.categories["satilik"]["konut"] == "/satilik-konut"
        assert config.categories["satilik"]["arsa"] == "/satilik-arsa"


class TestHepsiemlakConfig:
    """Tests for HepsiemlakConfig"""
    
    def test_base_url(self):
        """Test Hepsiemlak base URL"""
        config = HepsiemlakConfig()
        assert config.base_url == "https://www.hepsiemlak.com"
    
    def test_categories_exist(self):
        """Test that categories are defined"""
        config = HepsiemlakConfig()
        
        assert "satilik" in config.categories
        assert "kiralik" in config.categories
        
        assert "konut" in config.categories["satilik"]
        assert "arsa" in config.categories["satilik"]
        assert "devremulk" in config.categories["satilik"]


class TestGlobalFunctions:
    """Tests for global config functions"""
    
    def test_get_config(self):
        """Test get_config returns ScraperConfig"""
        config = get_config()
        assert isinstance(config, ScraperConfig)
    
    def test_get_emlakjet_config(self):
        """Test get_emlakjet_config returns EmlakJetConfig"""
        config = get_emlakjet_config()
        assert isinstance(config, EmlakJetConfig)
    
    def test_get_hepsiemlak_config(self):
        """Test get_hepsiemlak_config returns HepsiemlakConfig"""
        config = get_hepsiemlak_config()
        assert isinstance(config, HepsiemlakConfig)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
