"""EmlakJet Scraper modülü"""

from importlib import import_module
from typing import Any

__all__ = [
    "ArsaParser",
    "EmlakJetScraper",
    "EmlakJetScraplingScraper",
    "IsyeriParser",
    "KonutParser",
    "TuristikTesisParser",
]

_EXPORTS = {
    "ArsaParser": (".parsers", "ArsaParser"),
    "EmlakJetScraper": (".main", "EmlakJetScraper"),
    "EmlakJetScraplingScraper": (".scrapling_scraper", "EmlakJetScraplingScraper"),
    "IsyeriParser": (".parsers", "IsyeriParser"),
    "KonutParser": (".parsers", "KonutParser"),
    "TuristikTesisParser": (".parsers", "TuristikTesisParser"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attr)
    globals()[name] = value
    return value
