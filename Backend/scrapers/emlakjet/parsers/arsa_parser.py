# -*- coding: utf-8 -*-
"""
Arsa (Land) parser for EmlakJet
"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class ArsaParser(BaseEmlakJetParser):
    """Parser for Arsa (land) listings on EmlakJet"""
    
    def __init__(self):
        super().__init__("arsa")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """
        Parse arsa-specific details from quick info and title.
        
        Expected format: "Tarla | 2.821 m²"
        
        Args:
            quick_info: Quick info text
            title: Listing title
            
        Returns:
            Dictionary with arsa fields
        """
        details = {
            'arsa_tipi': '',
            'metrekare': '',
            'imar_durumu': ''
        }
        
        # Parse quick info
        if quick_info:
            try:
                parts = [part.strip() for part in quick_info.split('|')]
                
                for part in parts:
                    part_lower = part.lower()
                    
                    # Land type
                    if any(t in part_lower for t in ['tarla', 'arsa', 'arazi', 'bahçe', 'zeytinlik', 'bağ']):
                        details['arsa_tipi'] = part
                    
                    # Square meters
                    elif 'm²' in part or 'm2' in part_lower:
                        details['metrekare'] = part
            
            except Exception:
                pass
        
        # Parse title for imar (zoning) status
        if title:
            title_lower = title.lower()
            
            if 'imar' in title_lower:
                if 'imarı yok' in title_lower or 'imarsız' in title_lower:
                    details['imar_durumu'] = 'İmarsız'
                elif 'imarı var' in title_lower or 'imarlı' in title_lower:
                    details['imar_durumu'] = 'İmarlı'
            elif 'tapulu' in title_lower:
                details['imar_durumu'] = 'Tapulu'
            
            # Check for kat karşılığı
            if 'kat' in title_lower and 'karşılığı' in title_lower:
                details['arsa_tipi'] = 'Kat Karşılığı Arsa'
        
        return details
