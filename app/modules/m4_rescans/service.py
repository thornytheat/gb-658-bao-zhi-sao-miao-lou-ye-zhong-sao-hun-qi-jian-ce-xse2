from .similarity import hamming_distance, is_candidate
from .decision import choose_scan

def run(rows: list[dict] | None = None) -> dict:
    rows = rows or [{"file_name": "old.tif", "phash": "0f0f", "clarity": 72, "captured_at": "2026-01-01"}, {"file_name": "new.tif", "phash": "0f0e", "clarity": 91, "captured_at": "2026-02-01"}]
    distance = hamming_distance(rows[0]["phash"], rows[1]["phash"])
    return {"distance": distance, "candidate": is_candidate(rows[0]["phash"], rows[1]["phash"]), "selected": choose_scan(rows)["file_name"], "superseded": len(rows) - 1}

def demo():
    return run()

