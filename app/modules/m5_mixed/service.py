from .evidence import header_match, evidence_score
from .conflicts import classify_mixed

def run(payload: dict | None = None) -> dict:
    payload = payload or {"manifest_issue": "2026-11-01", "header_issue": "2026-11-02", "phash_distance": 1, "page_match": True}
    return {"header_match": header_match(payload["manifest_issue"], payload["header_issue"]), "score": evidence_score(payload), "decision": classify_mixed(payload)}

def demo():
    return run()

