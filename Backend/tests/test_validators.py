# -*- coding: utf-8 -*-
"""utils/validators.py birim testleri"""

import sys
import os
import pytest

# Üst dizini import yoluna ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.validators import (
    DataValidator,
    DataNormalizer,
    validate_listing,
    normalize_price,
    normalize_area
)


class TestDataValidator:
    """DataValidator testleri"""

    def test_valid_listing(self):
        """Geçerli ilan doğrulamasını test et"""
        validator = DataValidator("konut")

        data = {
            "baslik": "3+1 Daire",
            "fiyat": "1.500.000 TL",
            "lokasyon": "İstanbul / Kadıköy"
        }

        is_valid, errors = validator.validate_listing(data)
        assert is_valid == True
        assert len(errors) == 0

    def test_invalid_listing_missing_fields(self):
        """Eksik alanlarla geçersiz ilan doğrulamasını test et"""
        validator = DataValidator("konut")

        data = {
            "baslik": "3+1 Daire",
            # fiyat ve lokasyon eksik
        }

        is_valid, errors = validator.validate_listing(data)
        assert is_valid == False
        assert len(errors) >= 1

    def test_is_valid_shortcut(self):
        """is_valid kısayol metodunu test et"""
        validator = DataValidator()

        valid_data = {"baslik": "Test", "fiyat": "100 TL", "lokasyon": "İstanbul"}
        invalid_data = {"baslik": "Test"}

        assert validator.is_valid(valid_data) == True
        assert validator.is_valid(invalid_data) == False


class TestDataNormalizer:
    """DataNormalizer testleri"""

    def test_normalize_price_basic(self):
        """Temel fiyat normalizasyonunu test et"""
        assert DataNormalizer.normalize_price("1.500.000 TL") == 1500000.0
        assert DataNormalizer.normalize_price("500.000 TL") == 500000.0

    def test_normalize_price_with_milyon(self):
        """'milyon' ifadeli fiyat normalizasyonunu test et"""
        assert DataNormalizer.normalize_price("2,5 milyon") == 2500000.0
        assert DataNormalizer.normalize_price("1 milyon TL") == 1000000.0

    def test_normalize_price_with_bin(self):
        """'bin' ifadeli fiyat normalizasyonunu test et"""
        assert DataNormalizer.normalize_price("500 bin TL") == 500000.0

    def test_normalize_price_empty(self):
        """Boş girdi ile fiyat normalizasyonunu test et"""
        assert DataNormalizer.normalize_price("") is None
        assert DataNormalizer.normalize_price(None) is None

    def test_normalize_area_basic(self):
        """Temel alan normalizasyonunu test et"""
        assert DataNormalizer.normalize_area("150 m²") == 150.0
        assert DataNormalizer.normalize_area("2.821 m²") == 2821.0

    def test_normalize_area_m2(self):
        """m2 ifadeli alan normalizasyonunu test et"""
        assert DataNormalizer.normalize_area("100 m2") == 100.0

    def test_normalize_area_empty(self):
        """Boş girdi ile alan normalizasyonunu test et"""
        assert DataNormalizer.normalize_area("") is None
        assert DataNormalizer.normalize_area(None) is None

    def test_normalize_room_count(self):
        """Oda sayısı normalizasyonunu test et"""
        assert DataNormalizer.normalize_room_count("3+1") == "3+1"
        assert DataNormalizer.normalize_room_count("2 + 1") == "2+1"
        assert DataNormalizer.normalize_room_count("Stüdyo") == "Studio"

    def test_normalize_location(self):
        """Lokasyon ayrıştırmasını test et"""
        result = DataNormalizer.normalize_location("İstanbul / Kadıköy / Moda")

        assert result["il"] == "İstanbul"
        assert result["ilce"] == "Kadıköy"
        assert result["mahalle"] == "Moda"

    def test_clean_text(self):
        """Metin temizlemeyi test et"""
        assert DataNormalizer.clean_text("  Hello   World  ") == "Hello World"
        assert DataNormalizer.clean_text("Multiple    spaces") == "Multiple spaces"


class TestConvenienceFunctions:
    """Yardımcı fonksiyon testleri"""

    def test_validate_listing(self):
        """validate_listing fonksiyonunu test et"""
        valid = {"baslik": "Test", "fiyat": "100", "lokasyon": "İstanbul"}
        invalid = {"baslik": "Test"}

        assert validate_listing(valid) == True
        assert validate_listing(invalid) == False

    def test_normalize_price_function(self):
        """normalize_price fonksiyonunu test et"""
        assert normalize_price("1.000 TL") == 1000.0

    def test_normalize_area_function(self):
        """normalize_area fonksiyonunu test et"""
        assert normalize_area("100 m²") == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
