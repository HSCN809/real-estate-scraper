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
    
    def __init__(self, output_dir: str = "outputs"):
        """
        Initialize the exporter.
        
        Args:
            output_dir: Base directory for output files
        """
        self.output_dir = output_dir
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
        format: str = "excel"
    ) -> Dict[str, str]:
        """
        Save data grouped by city to separate files.
        
        Args:
            data: Dictionary of city -> list of listings
            prefix: File name prefix
            format: Output format ('json', 'csv', 'excel')
            
        Returns:
            Dictionary of city -> filepath
        """
        results = {}
        
        for city, listings in data.items():
            if not listings:
                continue
            
            city_prefix = f"{prefix}_{city.lower().replace(' ', '_')}"
            
            try:
                # Only Excel format is supported
                results[city] = self.save_excel(listings, city_prefix, True)
            except Exception as e:
                logger.error(f"Failed to save data for {city}: {e}")
        
        return results


# Create default exporter instance
default_exporter = DataExporter()


def save_excel(data: List[Dict], prefix: str = "data", **kwargs) -> str:
    """Convenience function to save Excel"""
    return default_exporter.save_excel(data, prefix, **kwargs)
