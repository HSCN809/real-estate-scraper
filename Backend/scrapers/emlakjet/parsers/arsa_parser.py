"""EmlakJet Arsa parser'ı"""

import re
from typing import Any

from .base_parser import BaseEmlakJetParser


class ArsaParser(BaseEmlakJetParser):
    """EmlakJet arsa ilanları parser'ı"""

    def __init__(self):
        super().__init__("arsa")

    def parse_category_details(self, quick_info: str, title: str) -> dict[str, Any]:
        """Arsa detaylarını quick info ve başlıktan parse et"""
        details = {"arsa_tipi": "", "metrekare": "", "imar_durumu": ""}

        # Quick info'yu parse et
        if quick_info:
            try:
                parts = [part.strip() for part in re.split(r"[|·]", quick_info)]

                for part in parts:
                    part_lower = part.lower()

                    # Arsa tipi
                    if any(
                        t in part_lower
                        for t in ["tarla", "arsa", "arazi", "bahçe", "zeytinlik", "bağ"]
                    ):
                        details["arsa_tipi"] = part

                    # Metrekare (m² fiyatı olan "/m²" parçalarını atla)
                    elif (
                        ("m²" in part or "m2" in part_lower)
                        and "/" not in part
                        and not details["metrekare"]
                    ):
                        details["metrekare"] = part

            except Exception:  # nosec
                pass

        # Başlıktan imar durumunu parse et
        if title:
            title_lower = title.lower()

            if "imar" in title_lower:
                if "imarı yok" in title_lower or "imarsız" in title_lower:
                    details["imar_durumu"] = "İmarsız"
                elif "imarı var" in title_lower or "imarlı" in title_lower:
                    details["imar_durumu"] = "İmarlı"
            elif "tapulu" in title_lower:
                details["imar_durumu"] = "Tapulu"

            # Kat karşılığı kontrolü
            if "kat" in title_lower and "karşılığı" in title_lower:
                details["arsa_tipi"] = "Kat Karşılığı Arsa"

        return details
