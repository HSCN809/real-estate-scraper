# -*- coding: utf-8 -*-
"""EmlakJet Konut parser'ı"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class KonutParser(BaseEmlakJetParser):
    """EmlakJet konut ilanları parser'ı"""
    
    def __init__(self):
        super().__init__("konut")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Konut detaylarını quick info'dan parse et"""
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
                
                # Mülk tipi
                if any(t in part_lower for t in ['daire', 'residence', 'villa', 'müstakil', 'tripleks', 'dubleks']):
                    details['tip'] = part
                
                # Oda sayısı (örn: 1+1, 2+1, 3+1)
                elif '+' in part:
                    details['oda_sayisi'] = part
                
                # Kat bilgisi
                elif 'kat' in part_lower:
                    details['kat'] = part
                
                # Metrekare
                elif 'm²' in part or 'm2' in part_lower:
                    details['metrekare'] = part
        
        except Exception:
            pass
        
        return details
