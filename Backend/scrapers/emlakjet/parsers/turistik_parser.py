# -*- coding: utf-8 -*-
"""
Turistik Tesis (Touristic Facility) parser for EmlakJet
"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class TuristikTesisParser(BaseEmlakJetParser):
    """Parser for Turistik Tesis listings on EmlakJet"""
    
    def __init__(self):
        super().__init__("turistik_tesis")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """
        Parse turistik tesis-specific details from quick info.
        
        Args:
            quick_info: Quick info text
            title: Listing title
            
        Returns:
            Dictionary with turistik tesis fields
        """
        details = {
            'tesis_tipi': '',
            'oda_sayisi': '',
            'yatak_sayisi': ''
        }
        
        if not quick_info:
            return details
        
        try:
            parts = [part.strip() for part in quick_info.split('|')]
            
            for part in parts:
                part_lower = part.lower()
                
                # Facility type
                if any(t in part_lower for t in [
                    'otel', 'motel', 'pansiyon', 'apart', 'tatil köyü',
                    'kamp', 'hostel', 'butik otel', 'resort'
                ]):
                    details['tesis_tipi'] = part
                
                # Room count
                elif 'oda' in part_lower:
                    details['oda_sayisi'] = part
                
                # Bed count
                elif 'yatak' in part_lower:
                    details['yatak_sayisi'] = part
        
        except Exception:
            pass
        
        # Try to extract from title if not found
        if not details['tesis_tipi'] and title:
            title_lower = title.lower()
            for tesis_type in ['otel', 'pansiyon', 'apart', 'motel']:
                if tesis_type in title_lower:
                    details['tesis_tipi'] = tesis_type.capitalize()
                    break
        
        return details
