import pytest
from app.modules.m2_issue.rules import normalize_issue, normalize_edition, normalize_page, expected_pages
from app.modules.m2_issue.catalog import business_key, is_supplement, split_key

def test_issue_date_slashes_normalize():
    assert normalize_issue("2026/11/01") == "2026-11-01"

def test_edition_keeps_supplement():
    assert normalize_edition("s1") == "S1"

def test_numeric_edition_zero_pads():
    assert normalize_edition("1") == "01"

def test_page_zero_pads_without_numeric_roundtrip():
    assert normalize_page("001") == "001"  # TRAP-08

def test_bad_page_rejected():
    with pytest.raises(ValueError, match="BAD_PAGE"):
        normalize_page("A1")

def test_expected_pages_is_inclusive():
    assert expected_pages(3) == ["001", "002", "003"]

def test_business_key_roundtrip():
    item = {"issue": "2026-11-01", "edition": "S1", "page": "003"}
    assert split_key(business_key(item)) == ("2026-11-01", "S1", "003") and is_supplement("S1")

