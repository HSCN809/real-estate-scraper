from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
    subtype: str | None = None
    subtype_path: str | None = None
    cities: list[str] | None = None
    districts: dict[str, list[str]] | None = None
    max_pages: int | None = None
    max_listings: int | None = None
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


class TaskLogEntry(BaseModel):
    text: str
    level: str = "info"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    message: str
    progress: int
    total: int
    current: int
    details: str
    unit: str = ""
    error: str | None = None
    platform: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    logs: list[TaskLogEntry] = Field(default_factory=list)


class ActiveTasksResponse(BaseModel):
    active_tasks: list[TaskStatusResponse]
    count: int
