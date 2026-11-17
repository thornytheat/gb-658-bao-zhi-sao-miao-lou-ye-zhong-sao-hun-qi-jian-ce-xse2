from app.manifest import run_id, build_manifest
from app.modules.m6_batches.compare import reconcile, reason_distribution
from app.modules.m6_batches.exporter import evidence_csv
import app.store as store


def test_reconcile_balanced():
    result = reconcile(10, 6, 2, 1, 1)
    assert result["balanced"] and result["difference"] == 0

def test_reconcile_difference_explained():
    assert reconcile(10, 6, 1, 1, 1)["difference"] == 1

def test_reason_distribution_counts():
    rows = [{"reason_code": "MIXED"}, {"reason_code": "MIXED"}, {"reason_code": "MISSING"}]
    assert reason_distribution(rows) == {"MIXED": 2, "MISSING": 1}

def test_run_id_is_content_stable():
    assert run_id(b"same") == run_id(b"same")

def test_manifest_keeps_full_digest():
    assert len(build_manifest(b"x", 1, 0)["input_sha256"]) == 64

def test_record_run_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATABASE_PATH", tmp_path / "runs.db")
    manifest = build_manifest(b"same", 1, 0)
    assert store.record_run(manifest) is True
    assert store.record_run(manifest) is False and store.run_count() == 1

def test_csv_contains_evidence_columns():
    text = evidence_csv([{"business_key": "k", "line_no": 2, "reason_code": "MISSING", "raw_value": "x"}])
    assert "business_key,line_no,reason_code,raw_value" in text and "MISSING" in text

