def classify_mixed(item: dict) -> str:
    header = item.get("header_issue")
    manifest = item.get("manifest_issue")
    if header and header != manifest:
        return "MIXED_ISSUE"
    if not header and item.get("phash_distance", 99) <= 3:
        return "REVIEW_REQUIRED"
    if item.get("page_match") is False:
        return "PAGE_CONFLICT"
    return "CONSISTENT"

def conflict_evidence(item: dict) -> dict:
    return {"manifest_issue": item.get("manifest_issue"), "header_issue": item.get("header_issue"), "page_match": item.get("page_match"), "reason_code": classify_mixed(item)}

