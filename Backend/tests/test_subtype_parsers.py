from scrapers.emlakjet.subtype_fetcher import candidate_node_ids, merge_subcategories
from scrapers.hepsiemlak.subtype_fetcher import parse_hepsiemlak_subtype_links


def test_hepsiemlak_keeps_real_subtypes_and_drops_filters():
    links = [
        {"name": "Daire", "href": "https://www.hepsiemlak.com/satilik/daire"},
        {"name": "Villa", "href": "/satilik/villa"},
        {"name": "Stüdyo", "href": "/satilik-studyo"},
        {"name": "1+1", "href": "/satilik-1-1"},
        {"name": "Listing", "href": "/aydin-didim-satilik/villa/119379-758"},
    ]
    parsed = parse_hepsiemlak_subtype_links(links, "satilik")
    assert [item["id"] for item in parsed] == ["daire", "villa"]
    assert parsed[0]["path"] == "/satilik/daire"


def test_emlakjet_isyeri_node_aliases():
    assert candidate_node_ids("/satilik-isyeri") == [
        "satilik-isyeri",
        "satilik-is-yeri",
    ]


def test_merge_keeps_previous_when_new_is_empty():
    old = {"satilik": {"isyeri": [{"id": "ofis", "name": "Ofis", "path": "/satilik-ofis"}]}}
    new = {"satilik": {"isyeri": [], "konut": [{"id": "daire", "name": "Daire", "path": "/satilik-daire"}]}}
    merged = merge_subcategories(new, old)
    assert merged["satilik"]["isyeri"][0]["id"] == "ofis"
    assert merged["satilik"]["konut"][0]["id"] == "daire"
