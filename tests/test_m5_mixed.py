from app.modules.m5_mixed.evidence import header_match, evidence_score
from app.modules.m5_mixed.conflicts import classify_mixed, conflict_evidence

def test_matching_header_is_true():
    assert header_match("2026-11-01", "2026-11-01") is True

def test_missing_header_is_unknown():
    assert header_match("2026-11-01", None) is None  # TRAP-07

def test_conflicting_header_dominates_score():
    item = {"manifest_issue": "1", "header_issue": "2", "page_match": True, "phash_distance": 0}
    assert evidence_score(item) == -2

def test_header_conflict_is_mixed_issue():
    item = {"manifest_issue": "1", "header_issue": "2", "page_match": True, "phash_distance": 0}
    assert classify_mixed(item) == "MIXED_ISSUE"

def test_hash_candidate_without_header_needs_review():
    item = {"manifest_issue": "1", "header_issue": None, "page_match": True, "phash_distance": 1}
    assert classify_mixed(item) == "REVIEW_REQUIRED"  # TRAP-09

def test_page_conflict_is_separate_reason():
    assert classify_mixed({"manifest_issue": "1", "header_issue": "1", "page_match": False}) == "PAGE_CONFLICT"

def test_conflict_evidence_keeps_original_fields():
    item = {"manifest_issue": "1", "header_issue": "2", "page_match": True}
    evidence = conflict_evidence(item)
    assert evidence["manifest_issue"] == "1" and evidence["reason_code"] == "MIXED_ISSUE"

