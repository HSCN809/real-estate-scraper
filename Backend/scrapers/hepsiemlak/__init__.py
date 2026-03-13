# -*- coding: utf-8 -*-
"""HepsiEmlak Scraper modülü"""

from .main import HepsiemlakScraper
from .scrapling_scraper import HepsiemlakScraplingScraper
from .parsers import (
    KonutParser,
    ArsaParser,
    IsyeriParser,
    DevremulkParser,
    TuristikParser
)

__all__ = [
    'HepsiemlakScraper',
    'HepsiemlakScraplingScraper',
    'KonutParser',
    'ArsaParser',
    'IsyeriParser',
    'DevremulkParser',
    'TuristikParser'
]
