# -*- coding: utf-8 -*-
"""
Data validation utilities for scraped listings
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from .logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """
    Validates and normalizes scraped listing data.
    """
    
    # Required fields for each category
    REQUIRED_FIELDS = {
        "default": ["baslik", "fiyat", "lokasyon"],
        "konut": ["baslik", "fiyat", "lokasyon"],
        "arsa": ["baslik", "fiyat", "lokasyon"],
        "isyeri": ["baslik", "fiyat", "lokasyon"],
    }
    
    def __init__(self, category: str = "default"):
        """
        Initialize validator.
        
        Args:
            category: Category name for field requirements
        """
        self.category = category
        self.required_fields = self.REQUIRED_FIELDS.get(
            category, 
            self.REQUIRED_FIELDS["default"]
        )
    
    def validate_listing(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single listing.
        
        Args:
            data: Listing data dictionary
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        return len(errors) == 0, errors
    
    def validate_listings(
        self, 
        listings: List[Dict[str, Any]]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate a list of listings.
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            Tuple of (valid_listings, invalid_listings)
        """
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
        """Quick check if listing is valid"""
        is_valid, _ = self.validate_listing(data)
        return is_valid


class DataNormalizer:
    """
    Normalizes scraped data values.
    """
    
    @staticmethod
    def normalize_price(price_str: str) -> Optional[float]:
        """
        Normalize price string to float.
        
        Args:
            price_str: Price string (e.g., "1.500.000 TL", "2,5 milyon")
            
        Returns:
            Normalized price as float or None
        """
        if not price_str:
            return None
        
        try:
            # Remove currency symbols and whitespace
            cleaned = price_str.strip()
            cleaned = re.sub(r'[TL₺$€]', '', cleaned)
            cleaned = cleaned.strip()
            
            # Handle "milyon" (million)
            if 'milyon' in cleaned.lower():
                cleaned = re.sub(r'milyon', '', cleaned, flags=re.IGNORECASE)
                cleaned = cleaned.replace(',', '.')
                cleaned = re.sub(r'[^\d.]', '', cleaned)
                return float(cleaned) * 1_000_000
            
            # Handle "bin" (thousand)
            if 'bin' in cleaned.lower():
                cleaned = re.sub(r'bin', '', cleaned, flags=re.IGNORECASE)
                cleaned = cleaned.replace(',', '.')
                cleaned = re.sub(r'[^\d.]', '', cleaned)
                return float(cleaned) * 1_000
            
            # Standard format: 1.500.000 or 1,500,000
            # Remove thousand separators (dots or commas followed by 3 digits)
            cleaned = re.sub(r'\.(?=\d{3})', '', cleaned)
            cleaned = re.sub(r',(?=\d{3})', '', cleaned)
            
            # Replace remaining comma with dot for decimal
            cleaned = cleaned.replace(',', '.')
            
            # Extract only numbers and decimal point
            cleaned = re.sub(r'[^\d.]', '', cleaned)
            
            if cleaned:
                return float(cleaned)
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    @staticmethod
    def normalize_area(area_str: str) -> Optional[float]:
        """
        Normalize area/metrekare string to float.
        
        Args:
            area_str: Area string (e.g., "150 m²", "2.821 m2")
            
        Returns:
            Normalized area as float or None
        """
        if not area_str:
            return None
        
        try:
            # Remove unit indicators
            cleaned = area_str.strip()
            cleaned = re.sub(r'm[²2]', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            
            # Remove thousand separators
            cleaned = re.sub(r'\.(?=\d{3})', '', cleaned)
            cleaned = cleaned.replace(',', '.')
            
            # Extract number
            match = re.search(r'[\d.]+', cleaned)
            if match:
                return float(match.group())
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    @staticmethod
    def normalize_room_count(room_str: str) -> Optional[str]:
        """
        Normalize room count string.
        
        Args:
            room_str: Room string (e.g., "3+1", "2 + 1", "Stüdyo")
            
        Returns:
            Normalized room string or None
        """
        if not room_str:
            return None
        
        cleaned = room_str.strip()
        
        # Standardize format: remove spaces around +
        cleaned = re.sub(r'\s*\+\s*', '+', cleaned)
        
        # Handle special cases
        if 'stüdyo' in cleaned.lower() or 'studio' in cleaned.lower():
            return "Studio"
        
        return cleaned if cleaned else None
    
    @staticmethod
    def normalize_location(location_str: str) -> Dict[str, str]:
        """
        Parse location string into components.
        
        Args:
            location_str: Location string (e.g., "İstanbul / Kadıköy / Moda")
            
        Returns:
            Dictionary with il, ilce, mahalle keys
        """
        result = {
            'il': '',
            'ilce': '',
            'mahalle': ''
        }
        
        if not location_str:
            return result
        
        # Split by common separators
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
        """
        Clean text by removing extra whitespace.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()


def validate_listing(data: Dict[str, Any], category: str = "default") -> bool:
    """Convenience function to validate a listing"""
    validator = DataValidator(category)
    return validator.is_valid(data)


def normalize_price(price_str: str) -> Optional[float]:
    """Convenience function to normalize price"""
    return DataNormalizer.normalize_price(price_str)


def normalize_area(area_str: str) -> Optional[float]:
    """Convenience function to normalize area"""
    return DataNormalizer.normalize_area(area_str)
