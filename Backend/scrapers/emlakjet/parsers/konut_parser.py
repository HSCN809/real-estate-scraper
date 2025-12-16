# -*- coding: utf-8 -*-
"""
Konut (Housing) parser for EmlakJet
"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class KonutParser(BaseEmlakJetParser):
    """Parser for Konut (housing) listings on EmlakJet"""
    
    def __init__(self):
        super().__init__("konut")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """
        Parse konut-specific details from quick info.
        
        Expected format: "Daire | 2+1 | Bahçe katı | 100 m²"
        
        Args:
            quick_info: Quick info text
            title: Listing title
            
        Returns:
            Dictionary with konut fields
        """
        details = {
            'tip': '',
            'oda_sayisi': '',
            'kat': '',
            'metrekare': ''
        }
        
        if not quick_info:
            return details
        
        try:
            parts = [part.strip() for part in quick_info.split('|')]
            
            for part in parts:
                part_lower = part.lower()
                
                # Property type
                if any(t in part_lower for t in ['daire', 'residence', 'villa', 'müstakil', 'tripleks', 'dubleks']):
                    details['tip'] = part
                
                # Room count (e.g., 1+1, 2+1, 3+1)
                elif '+' in part:
                    details['oda_sayisi'] = part
                
                # Floor info
                elif 'kat' in part_lower:
                    details['kat'] = part
                
                # Square meters
                elif 'm²' in part or 'm2' in part_lower:
                    details['metrekare'] = part
        
        except Exception:
            pass
        
        return details
