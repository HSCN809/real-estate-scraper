from scrapers.hepsiemlak.subtype_fetcher import fetch_subtypes


def test_hepsiemlak_subtypes_load_without_selenium():
    subtypes = fetch_subtypes("satilik", "konut")
    assert isinstance(subtypes, list)
