# -*- coding: utf-8 -*-
"""api/schemas.py testleri."""

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas import ScrapeRequest


def test_hepsiemlak_scraping_method_defaults_to_selenium():
    request = ScrapeRequest()
    assert request.scraping_method == "selenium"


@pytest.mark.parametrize(
    "scraping_method",
    [
        "selenium",
        "scrapling_stealth_session",
        "scrapling_fetcher_session",
        "scrapling_dynamic_session",
        "scrapling_spider_fetcher_session",
        "scrapling_spider_dynamic_session",
        "scrapling_spider_stealth_session",
    ],
)
def test_hepsiemlak_scraping_method_accepts_supported_values(scraping_method: str):
    request = ScrapeRequest(scraping_method=scraping_method)
    assert request.scraping_method == scraping_method


def test_hepsiemlak_scraping_method_rejects_invalid_values():
    with pytest.raises(ValidationError):
        ScrapeRequest(scraping_method="invalid_method")
