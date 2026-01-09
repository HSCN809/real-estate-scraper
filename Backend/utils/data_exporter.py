# -*- coding: utf-8 -*-
"""
Data export utilities for JSON, CSV, and Excel formats
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from .logger import get_logger

logger = get_logger(__name__)


class DataExporter:
    """
    Export scraped data to various formats (JSON, CSV, Excel).
    """

    def __init__(
        self,
        output_dir: str = "outputs",
        listing_type: Optional[str] = None,  # satilik/kiralik
        category: Optional[str] = None,      # konut/arsa/isyeri vb.
        subtype: Optional[str] = None        # daire/villa vb.
    ):
        """
        Initialize the exporter with hierarchical folder structure.

        Args:
            output_dir: Base directory for output files
            listing_type: Type of listing (satilik/kiralik)
            category: Category (konut/arsa/isyeri etc.)
            subtype: Subcategory (daire/villa etc.)
        """
        self.base_output_dir = output_dir
        self.listing_type = listing_type
        self.category = category
        self.subtype = subtype

        # Build hierarchical path: base/listing_type/category/subtype
        path_parts = [output_dir]
        if listing_type:
            path_parts.append(listing_type)
        if category:
            path_parts.append(category)
        if subtype:
            path_parts.append(subtype)

        self.output_dir = os.path.join(*path_parts)
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Created output directory: {self.output_dir}")
    
    def _generate_filename(
        self,
        prefix: str,
        extension: str,
        timestamp: bool = True,
        subfolder: Optional[str] = None
    ) -> str:
        """
        Generate a filename with optional timestamp.
        
        Args:
            prefix: File prefix (e.g., 'konut_ilanlari')
            extension: File extension (e.g., 'json')
            timestamp: Whether to include timestamp
            subfolder: Optional subfolder name
            
        Returns:
            Full file path
        """
        if timestamp:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{ts}.{extension}"
        else:
            filename = f"{prefix}.{extension}"
        
        if subfolder:
            folder = os.path.join(self.output_dir, subfolder)
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            return os.path.join(folder, filename)
        
        return os.path.join(self.output_dir, filename)
    
    def save_excel(
        self,
        data: List[Dict[str, Any]],
        prefix: str = "data",
        timestamp: bool = True,
        subfolder: Optional[str] = None,
        sheet_name: str = "Data"
    ) -> str:
        """
        Save data to Excel file.
        
        Args:
            data: List of dictionaries to save
            prefix: File name prefix
            timestamp: Whether to include timestamp in filename
            subfolder: Optional subfolder
            sheet_name: Excel sheet name
            
        Returns:
            Path to saved file
        """
        if not HAS_PANDAS:
            logger.error("pandas not installed, cannot save Excel")
            raise ImportError("pandas is required for Excel export")
        
        if not data:
            logger.warning("No data to save to Excel")
            return ""
        
        filepath = self._generate_filename(prefix, "xlsx", timestamp, subfolder)
        
        try:
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, sheet_name=sheet_name, engine='openpyxl')
            
            logger.info(f"✅ Excel saved: {filepath} ({len(data)} records)")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save Excel: {e}")
            raise
    
    
    def save_by_city(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        prefix: str = "data",
        format: str = "excel",
        city_district_map: Optional[Dict[str, List[str]]] = None  # Şehir -> İlçeler mapping
    ) -> Dict[str, str]:
        """
        Save data grouped by city to separate files with hierarchical folder structure.

        Args:
            data: Dictionary of city -> list of listings
            prefix: File name prefix
            format: Output format ('json', 'csv', 'excel')
            city_district_map: Optional mapping of city -> districts for folder structure

        Returns:
            Dictionary of city -> filepath
        """
        results = {}

        for city, listings in data.items():
            if not listings:
                continue

            # Şehir klasörü oluştur
            city_slug = city.lower().replace(' ', '_').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')

            # İlçe bilgisi var mı kontrol et
            if city_district_map and city in city_district_map:
                districts = city_district_map[city]
                # Eğer ilçe varsa, her ilçe için ayrı klasör
                # Ama listings içindeki ilanların hangi ilçeye ait olduğunu bilmiyoruz
                # Bu yüzden tek dosyaya kaydedip şehir klasörüne koyalım
                subfolder = city_slug
                city_prefix = f"{prefix}_{city_slug}_{'_'.join([d.lower().replace(' ', '_') for d in districts[:3]])}"  # İlk 3 ilçeyi prefix'e ekle
            else:
                # İlçe yoksa sadece şehir klasörü
                subfolder = city_slug
                city_prefix = f"{prefix}_{city_slug}"

            try:
                # Excel'i şehir klasörüne kaydet
                results[city] = self.save_excel(listings, city_prefix, True, subfolder=subfolder)
            except Exception as e:
                logger.error(f"Failed to save data for {city}: {e}")

        return results


# Create default exporter instance
default_exporter = DataExporter()


def save_excel(data: List[Dict], prefix: str = "data", **kwargs) -> str:
    """Convenience function to save Excel"""
    return default_exporter.save_excel(data, prefix, **kwargs)
