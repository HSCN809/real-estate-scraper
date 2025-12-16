# -*- coding: utf-8 -*-
"""
İşyeri (Commercial) parser for EmlakJet
"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class IsyeriParser(BaseEmlakJetParser):
    """Parser for İşyeri (commercial) listings on EmlakJet"""
    
    def __init__(self):
        super().__init__("isyeri")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """
        Parse isyeri-specific details from quick info.
        
        Expected format: "Dükkan | 150 m²"
        
        Args:
            quick_info: Quick info text
            title: Listing title
            
        Returns:
            Dictionary with isyeri fields
        """
        details = {
            'isyeri_tipi': '',
            'metrekare': '',
            'kat': ''
        }
        
        if not quick_info:
            return details
        
        try:
            parts = [part.strip() for part in quick_info.split('|')]
            
            for part in parts:
                part_lower = part.lower()
                
                # Commercial type
                if any(t in part_lower for t in [
                    'dükkan', 'mağaza', 'ofis', 'büro', 'depo', 'atölye',
                    'fabrika', 'plaza', 'iş hanı', 'çarşı', 'showroom'
                ]):
                    details['isyeri_tipi'] = part
                
                # Floor info
                elif 'kat' in part_lower:
                    details['kat'] = part
                
                # Square meters
                elif 'm²' in part or 'm2' in part_lower:
                    details['metrekare'] = part
        
        except Exception:
            pass
        
        return details
