# -*- coding: utf-8 -*-
"""
Failed Pages Tracker - Başarısız sayfaları takip eder ve retry mekanizması için kullanılır
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class FailedPageInfo:
    """Başarısız sayfa bilgisi"""
    url: str
    page_number: int
    city: str
    district: Optional[str] = None
    error: str = ""
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    max_pages: int = 1  # O şehir/ilçe için toplam sayfa sayısı
    listing_type: str = ""
    category: str = ""
    subtype_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "page_number": self.page_number,
            "city": self.city,
            "district": self.district,
            "error": self.error,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat(),
            "max_pages": self.max_pages,
            "listing_type": self.listing_type,
            "category": self.category,
            "subtype_path": self.subtype_path
        }


class FailedPagesTracker:
    """
    Başarısız sayfaları takip eden sınıf.
    Singleton pattern kullanır.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FailedPagesTracker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._failed_pages: Dict[str, FailedPageInfo] = {}  # url -> FailedPageInfo
        self._successful_retries: List[str] = []  # Başarılı retry'ların URL'leri
        
    def reset(self):
        """Tracker'ı sıfırla"""
        self._failed_pages.clear()
        self._successful_retries.clear()
        logger.info("FailedPagesTracker reset edildi")
    
    def add_failed_page(self, page_info: FailedPageInfo) -> None:
        """Başarısız sayfa ekle"""
        key = f"{page_info.city}_{page_info.district or 'all'}_{page_info.page_number}"
        
        if key in self._failed_pages:
            # Zaten var, retry count güncelle
            self._failed_pages[key].retry_count += 1
            self._failed_pages[key].error = page_info.error
            self._failed_pages[key].timestamp = datetime.now()
        else:
            self._failed_pages[key] = page_info
            
        logger.warning(f"⚠️ Başarısız sayfa eklendi: {page_info.city}/{page_info.district or 'tüm'} - Sayfa {page_info.page_number}")
    
    def get_all_failed(self) -> List[FailedPageInfo]:
        """Tüm başarısız sayfaları getir"""
        return list(self._failed_pages.values())
    
    def get_unretried(self, max_retry_count: int = 3) -> List[FailedPageInfo]:
        """Henüz maksimum deneme sayısına ulaşmamış sayfaları getir"""
        return [
            page for page in self._failed_pages.values()
            if page.retry_count < max_retry_count
        ]
    
    def mark_as_success(self, city: str, district: Optional[str], page_number: int) -> None:
        """Sayfayı başarılı olarak işaretle ve listeden çıkar"""
        key = f"{city}_{district or 'all'}_{page_number}"
        
        if key in self._failed_pages:
            self._successful_retries.append(key)
            del self._failed_pages[key]
            logger.info(f"✅ Başarılı retry: {city}/{district or 'tüm'} - Sayfa {page_number}")
    
    def increment_retry_count(self, city: str, district: Optional[str], page_number: int) -> None:
        """Sayfa için retry sayısını artır"""
        key = f"{city}_{district or 'all'}_{page_number}"
        
        if key in self._failed_pages:
            self._failed_pages[key].retry_count += 1
            self._failed_pages[key].timestamp = datetime.now()
    
    def has_failed_pages(self) -> bool:
        """Başarısız sayfa var mı?"""
        return len(self._failed_pages) > 0
    
    def get_failed_count(self) -> int:
        """Başarısız sayfa sayısı"""
        return len(self._failed_pages)
    
    def get_success_count(self) -> int:
        """Başarılı retry sayısı"""
        return len(self._successful_retries)
    
    def get_summary(self) -> Dict[str, Any]:
        """Özet bilgi döndür"""
        return {
            "failed_count": len(self._failed_pages),
            "successful_retries": len(self._successful_retries),
            "failed_pages": [p.to_dict() for p in self._failed_pages.values()]
        }


# Global instance
failed_pages_tracker = FailedPagesTracker()
