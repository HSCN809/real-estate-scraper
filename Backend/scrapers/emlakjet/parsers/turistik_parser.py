# -*- coding: utf-8 -*-
"""EmlakJet Turistik Tesis parser'ı"""

from typing import Dict, Any
from .base_parser import BaseEmlakJetParser


class TuristikTesisParser(BaseEmlakJetParser):
    """EmlakJet turistik tesis ilanları parser'ı"""
    
    def __init__(self):
        super().__init__("turistik_tesis")
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Turistik tesis detaylarını quick info'dan parse et"""
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
                
                # Tesis tipi
                if any(t in part_lower for t in [
                    'otel', 'motel', 'pansiyon', 'apart', 'tatil köyü',
                    'kamp', 'hostel', 'butik otel', 'resort'
                ]):
                    details['tesis_tipi'] = part
                
                # Oda sayısı
                elif 'oda' in part_lower:
                    details['oda_sayisi'] = part
                
                # Yatak sayısı
                elif 'yatak' in part_lower:
                    details['yatak_sayisi'] = part
        
        except Exception:
            pass
        
        # Bulunamadıysa başlıktan çıkarmayı dene
        if not details['tesis_tipi'] and title:
            title_lower = title.lower()
            for tesis_type in ['otel', 'pansiyon', 'apart', 'motel']:
                if tesis_type in title_lower:
                    details['tesis_tipi'] = tesis_type.capitalize()
                    break
        
        return details
