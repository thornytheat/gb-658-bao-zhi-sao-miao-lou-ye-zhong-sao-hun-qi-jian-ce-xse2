from fastapi.testclient import TestClient
from app.main import app


def test_all_module_pages_accessible():
    client = TestClient(app)
    for path in ("/intake", "/issues", "/pages", "/rescans", "/mixed", "/batches", "/settle"):
        response = client.get(path)
        assert response.status_code == 200 and "panel" in response.text

def test_full_sample_flow_has_business_results():
    client = TestClient(app)
    endpoints = ("/api/scans/import", "/api/issues/normalize", "/api/pages/check", "/api/rescans/evaluate", "/api/mixed/evaluate", "/api/reconcile")
    results = [client.post(path).json() for path in endpoints]
    assert results[0]["accepted"] == 2 and results[2]["missing"] == [3] and results[4]["decision"] == "MIXED_ISSUE"

def test_export_matches_page_evidence():
    client = TestClient(app)
    response = client.get("/api/export/evidence.csv")
    assert response.status_code == 200 and "MISSING_PAGE" in response.text

