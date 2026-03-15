from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, field_validator

SUPPORTED_SCRAPING_METHODS = (
    "selenium",
    "scrapling_stealth_session",
    "scrapling_fetcher_session",
    "scrapling_dynamic_session",
    "scrapling_spider_fetcher_session",
    "scrapling_spider_dynamic_session",
    "scrapling_spider_stealth_session",
)


class ScrapeRequest(BaseModel):
    category: str = "konut"
    listing_type: str = "satilik"
    subtype: Optional[str] = None
    subtype_path: Optional[str] = None
    cities: Optional[List[str]] = None
    districts: Optional[Dict[str, List[str]]] = None
    max_pages: Optional[int] = None
    max_listings: Optional[int] = None
    scraping_method: str = "selenium"
    proxy_enabled: bool = False

    @field_validator("scraping_method")
    @classmethod
    def validate_scraping_method(cls, value: str) -> str:
        if value not in SUPPORTED_SCRAPING_METHODS:
            raise ValueError(f"Unsupported scraping_method: {value}")
        return value


class ScrapeStartResponse(BaseModel):
    task_id: str
    status: Literal["queued"]
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    message: str
    progress: int
    total: int
    current: int
    details: str
    error: Optional[str] = None
    platform: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    finished_at: Optional[str] = None


class ActiveTasksResponse(BaseModel):
    active_tasks: List[TaskStatusResponse]
    count: int
