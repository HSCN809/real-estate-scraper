from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

HepsiemlakScrapingMethod = Literal[
    "selenium",
    "scrapling_stealth_session",
    "scrapling_fetcher_session",
    "scrapling_dynamic_session",
    "scrapling_spider_fetcher_session",
    "scrapling_spider_dynamic_session",
    "scrapling_spider_stealth_session",
]


class ScrapeRequest(BaseModel):
    category: str = "konut"
    listing_type: str = "satilik"
    subtype: Optional[str] = None
    subtype_path: Optional[str] = None
    cities: Optional[List[str]] = None
    districts: Optional[Dict[str, List[str]]] = None
    max_pages: Optional[int] = None
    max_listings: Optional[int] = None
    scraping_method: HepsiemlakScrapingMethod = "selenium"


class ScrapeResponse(BaseModel):
    status: str
    message: str
    data_count: int
    output_files: List[str]
    task_id: Optional[str] = None
