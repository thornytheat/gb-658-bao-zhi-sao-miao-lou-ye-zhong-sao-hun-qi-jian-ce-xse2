import pytest
from app.modules.m4_rescans.similarity import hamming_distance, is_candidate, same_digest
from app.modules.m4_rescans.decision import choose_scan, classify_pair

def test_hamming_distance_exact():
    assert hamming_distance("0f", "0e") == 1

def test_hash_length_mismatch_rejected():
    with pytest.raises(ValueError, match="BAD_HASH"):
        hamming_distance("0f", "f")

def test_candidate_threshold_boundary():
    assert is_candidate("0", "7", threshold=3)

def test_digest_is_stronger_than_visual_hash():
    assert same_digest({"sha256": "abc"}, {"sha256": "abc"})

def test_clearer_scan_selected():
    rows = [{"file_name": "a", "clarity": 70}, {"file_name": "b", "clarity": 91}]
    assert choose_scan(rows)["file_name"] == "b"

def test_selection_is_deterministic_on_tie():
    rows = [{"file_name": "a", "clarity": 90, "captured_at": "2"}, {"file_name": "b", "clarity": 90, "captured_at": "1"}]
    assert choose_scan(rows)["file_name"] == "a"  # TRAP-22

def test_visual_candidate_does_not_cross_issue():
    left = {"sha256": "a", "issue": "1", "page": "001"}
    right = {"sha256": "b", "issue": "2", "page": "001"}
    assert classify_pair(left, right, True) == "DISTINCT"  # naive hash-only fails

