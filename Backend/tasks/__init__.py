# -*- coding: utf-8 -*-
"""
Celery tasks module
"""

from .scraping_tasks import scrape_hepsiemlak_task, scrape_emlakjet_task

__all__ = ["scrape_hepsiemlak_task", "scrape_emlakjet_task"]
