from app.modules.m3_pages.sequence import inspect_pages, select_versions
from app.modules.m3_pages.reconcile import page_accounts, coverage

def test_missing_page_detected():
    assert inspect_pages(["001", "002", "004"], 4)["missing"] == [3]

def test_duplicate_page_detected():
    assert inspect_pages(["001", "002", "002"], 3)["duplicates"] == [2]  # TRAP-14

def test_unexpected_page_detected():
    assert inspect_pages(["001", "005"], 4)["unexpected"] == [5]

def test_higher_version_wins_not_later_input():
    rows = [{"page": "001", "version": 2, "clarity": 50}, {"page": "001", "version": 1, "clarity": 99}]
    assert select_versions(rows)[0]["version"] == 2  # TRAP-26

def test_selection_order_independent():
    rows = [{"page": "002", "version": 1, "clarity": 80}, {"page": "002", "version": 2, "clarity": 70}]
    assert select_versions(rows) == select_versions(list(reversed(rows)))  # TRAP-19

def test_page_accounts_conserve_input():
    selected = [{"page": "001"}, {"page": "002"}]
    result = page_accounts(3, selected, {"missing": [], "unexpected": []})
    assert result["balanced"] and result["superseded"] == 1

def test_coverage_fixed_three_decimals():
    assert coverage([{}, {}], 3) == "0.667"

