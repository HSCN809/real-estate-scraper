from pydantic import BaseModel
from typing import List, Optional, Any

class ScrapeRequest(BaseModel):
    category: str = "konut"  # konut, arsa, isyeri
    listing_type: str = "satilik"  # satilik, kiralik
    cities: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    max_pages: int = 1

class ScrapeResponse(BaseModel):
    status: str
    message: str
    data_count: int
    output_files: List[str]
