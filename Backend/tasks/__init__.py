"""
Celery tasks module
"""

from .scraping_tasks import scrape_emlakjet_task, scrape_hepsiemlak_task

__all__ = ["scrape_emlakjet_task", "scrape_hepsiemlak_task"]
