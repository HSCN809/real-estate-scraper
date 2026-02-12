from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class ScrapeRequest(BaseModel):
    category: str = "konut"  # konut, arsa, isyeri
    listing_type: str = "satilik"  # satilik, kiralik
    subtype: Optional[str] = None  # Alt tip ID'si (örn: "tarla")
    subtype_path: Optional[str] = None  # Alt tip URL path'i (örn: "/kiralik/tarla")
    cities: Optional[List[str]] = None
    districts: Optional[Dict[str, List[str]]] = None  # İl -> [İlçeler] mapping
    max_pages: Optional[int] = None       # None = limit yok (tüm sayfalar)
    max_listings: Optional[int] = None    # None = limit yok (tüm ilanlar)

class ScrapeResponse(BaseModel):
    status: str
    message: str
    data_count: int
    output_files: List[str]
    task_id: Optional[str] = None  # Celery task ID for tracking
