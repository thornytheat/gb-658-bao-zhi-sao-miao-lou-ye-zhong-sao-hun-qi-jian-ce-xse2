from .rules import normalize_issue, normalize_edition, normalize_page
from .catalog import business_key

def run(payload: dict | None = None) -> dict:
    payload = payload or {"issue": "2026/11/01", "edition": "1", "page": "001"}
    item = {"issue": normalize_issue(payload["issue"]), "edition": normalize_edition(payload["edition"]), "page": normalize_page(payload["page"])}
    item["business_key"] = business_key(item)
    return item

def demo():
    return run()

