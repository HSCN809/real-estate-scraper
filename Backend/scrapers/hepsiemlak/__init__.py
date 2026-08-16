"""HepsiEmlak Scraper modülü"""

from importlib import import_module
from typing import Any

__all__ = [
    "ArsaParser",
    "DevremulkParser",
    "HepsiemlakScraper",
    "HepsiemlakScraplingScraper",
    "IsyeriParser",
    "KonutParser",
    "TuristikParser",
]

_EXPORTS = {
    "ArsaParser": (".parsers", "ArsaParser"),
    "DevremulkParser": (".parsers", "DevremulkParser"),
    "HepsiemlakScraper": (".main", "HepsiemlakScraper"),
    "HepsiemlakScraplingScraper": (".scrapling_scraper", "HepsiemlakScraplingScraper"),
    "IsyeriParser": (".parsers", "IsyeriParser"),
    "KonutParser": (".parsers", "KonutParser"),
    "TuristikParser": (".parsers", "TuristikParser"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attr)
    globals()[name] = value
    return value
