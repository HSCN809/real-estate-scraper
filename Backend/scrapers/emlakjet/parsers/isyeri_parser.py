"""EmlakJet İşyeri parser'ı"""

import re
from typing import Any

from .base_parser import BaseEmlakJetParser


class IsyeriParser(BaseEmlakJetParser):
    """EmlakJet işyeri ilanları parser'ı"""

    def __init__(self):
        super().__init__("isyeri")

    def parse_category_details(self, quick_info: str, title: str) -> dict[str, Any]:
        """İşyeri detaylarını quick info'dan parse et"""
        details = {"isyeri_tipi": "", "metrekare": "", "kat": ""}

        if not quick_info:
            return details

        try:
            parts = [part.strip() for part in re.split(r"[|·]", quick_info)]

            for part in parts:
                part_lower = part.lower()

                # İşyeri tipi
                if any(
                    t in part_lower
                    for t in [
                        "dükkan",
                        "mağaza",
                        "ofis",
                        "büro",
                        "depo",
                        "atölye",
                        "fabrika",
                        "plaza",
                        "iş hanı",
                        "çarşı",
                        "showroom",
                    ]
                ):
                    details["isyeri_tipi"] = part

                # Kat bilgisi (örn: "1. Kat", "Düz Giriş (Zemin)")
                elif (
                    "kat" in part_lower
                    or "giriş" in part_lower
                    or "zemin" in part_lower
                ):
                    details["kat"] = part

                # Metrekare
                elif "m²" in part or "m2" in part_lower:
                    details["metrekare"] = part

        except Exception:  # nosec
            pass

        return details
