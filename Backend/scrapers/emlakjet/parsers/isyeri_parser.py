# -*- coding: utf-8 -*-
"""EmlakJet İşyeri parser'ı"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class IsyeriParser(BaseEmlakJetParser):
    """EmlakJet işyeri ilanları parser'ı"""
    
    def __init__(self):
        super().__init__("isyeri")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """İşyeri detaylarını quick info'dan parse et"""
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
                
                # İşyeri tipi
                if any(t in part_lower for t in [
                    'dükkan', 'mağaza', 'ofis', 'büro', 'depo', 'atölye',
                    'fabrika', 'plaza', 'iş hanı', 'çarşı', 'showroom'
                ]):
                    details['isyeri_tipi'] = part
                
                # Kat bilgisi
                elif 'kat' in part_lower:
                    details['kat'] = part
                
                # Metrekare
                elif 'm²' in part or 'm2' in part_lower:
                    details['metrekare'] = part
        
        except Exception:
            pass
        
        return details
