# -*- coding: utf-8 -*-
"""Kazınan ilanlar için veri doğrulama araçları"""

import re
from typing import Dict, Any, List, Optional, Tuple
from .logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """Kazınan ilan verilerini doğrular ve normalleştirir."""
    
    # Her kategori için zorunlu alanlar
    REQUIRED_FIELDS = {
        "default": ["baslik", "fiyat", "lokasyon"],
        "konut": ["baslik", "fiyat", "lokasyon"],
        "arsa": ["baslik", "fiyat", "lokasyon"],
        "isyeri": ["baslik", "fiyat", "lokasyon"],
    }
    
    def __init__(self, category: str = "default"):
        """Doğrulayıcıyı kategori bazlı alan gereksinimleriyle başlatır."""
        self.category = category
        self.required_fields = self.REQUIRED_FIELDS.get(
            category, 
            self.REQUIRED_FIELDS["default"]
        )
    
    def validate_listing(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Tek bir ilanı doğrular, geçerlilik durumu ve hata listesi döndürür."""
        errors = []
        
        # Zorunlu alanları kontrol et
        for field in self.required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors
    
    def validate_listings(
        self, 
        listings: List[Dict[str, Any]]
    ) -> Tuple[List[Dict], List[Dict]]:
        """İlan listesini doğrular, geçerli ve geçersiz ilanları ayrı ayrı döndürür."""
        valid = []
        invalid = []
        
        for listing in listings:
            is_valid, errors = self.validate_listing(listing)
            if is_valid:
                valid.append(listing)
            else:
                listing['_validation_errors'] = errors
                invalid.append(listing)
        
        if invalid:
            logger.warning(f"Found {len(invalid)} invalid listings out of {len(listings)}")
        
        return valid, invalid
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """İlanın geçerli olup olmadığını hızlıca kontrol eder"""
        is_valid, _ = self.validate_listing(data)
        return is_valid


class DataNormalizer:
    """Kazınan veri değerlerini normalleştirir."""
    
    @staticmethod
    def normalize_price(price_str: str) -> Optional[float]:
        """Fiyat metnini float değere normalleştirir."""
        if not price_str:
            return None
        
        try:
            # Para birimi sembollerini ve boşlukları kaldır
            cleaned = price_str.strip()
            cleaned = re.sub(r'[TL₺$€]', '', cleaned)
            cleaned = cleaned.strip()
            
            # "milyon" ifadesini işle
            if 'milyon' in cleaned.lower():
                cleaned = re.sub(r'milyon', '', cleaned, flags=re.IGNORECASE)
                cleaned = cleaned.replace(',', '.')
                cleaned = re.sub(r'[^\d.]', '', cleaned)
                return float(cleaned) * 1_000_000
            
            # "bin" ifadesini işle
            if 'bin' in cleaned.lower():
                cleaned = re.sub(r'bin', '', cleaned, flags=re.IGNORECASE)
                cleaned = cleaned.replace(',', '.')
                cleaned = re.sub(r'[^\d.]', '', cleaned)
                return float(cleaned) * 1_000
            
            # Standart format: 1.500.000 veya 1,500,000 - binlik ayırıcıları kaldır
            cleaned = re.sub(r'\.(?=\d{3})', '', cleaned)
            cleaned = re.sub(r',(?=\d{3})', '', cleaned)
            
            # Kalan virgülü ondalık noktasıyla değiştir
            cleaned = cleaned.replace(',', '.')
            
            # Sadece rakamları ve ondalık noktasını çıkar
            cleaned = re.sub(r'[^\d.]', '', cleaned)
            
            if cleaned:
                return float(cleaned)
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    @staticmethod
    def normalize_area(area_str: str) -> Optional[float]:
        """Alan/metrekare metnini float değere normalleştirir."""
        if not area_str:
            return None
        
        try:
            # Birim göstergelerini kaldır
            cleaned = area_str.strip()
            cleaned = re.sub(r'm[²2]', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            
            # Binlik ayırıcıları kaldır
            cleaned = re.sub(r'\.(?=\d{3})', '', cleaned)
            cleaned = cleaned.replace(',', '.')
            
            # Sayıyı çıkar
            match = re.search(r'[\d.]+', cleaned)
            if match:
                return float(match.group())
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    @staticmethod
    def normalize_room_count(room_str: str) -> Optional[str]:
        """Oda sayısı metnini normalleştirir."""
        if not room_str:
            return None
        
        cleaned = room_str.strip()
        
        # Formatı standartlaştır: + etrafındaki boşlukları kaldır
        cleaned = re.sub(r'\s*\+\s*', '+', cleaned)
        
        # Özel durumları işle
        if 'stüdyo' in cleaned.lower() or 'studio' in cleaned.lower():
            return "Studio"
        
        return cleaned if cleaned else None
    
    @staticmethod
    def normalize_location(location_str: str) -> Dict[str, str]:
        """Lokasyon metnini il, ilce, mahalle bileşenlerine ayrıştırır."""
        result = {
            'il': '',
            'ilce': '',
            'mahalle': ''
        }
        
        if not location_str:
            return result
        
        # Yaygın ayırıcılara göre böl
        parts = re.split(r'[/,|]', location_str)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) >= 1:
            result['il'] = parts[0]
        if len(parts) >= 2:
            result['ilce'] = parts[1]
        if len(parts) >= 3:
            result['mahalle'] = parts[2]
        
        return result
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Fazla boşlukları kaldırarak metni temizler."""
        if not text:
            return ""
        
        # Birden fazla boşluğu tek boşlukla değiştir
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()


def validate_listing(data: Dict[str, Any], category: str = "default") -> bool:
    """İlan doğrulamak için kısayol fonksiyonu"""
    validator = DataValidator(category)
    return validator.is_valid(data)


def normalize_price(price_str: str) -> Optional[float]:
    """Fiyat normalleştirmek için kısayol fonksiyonu"""
    return DataNormalizer.normalize_price(price_str)


def normalize_area(area_str: str) -> Optional[float]:
    """Alan normalleştirmek için kısayol fonksiyonu"""
    return DataNormalizer.normalize_area(area_str)
