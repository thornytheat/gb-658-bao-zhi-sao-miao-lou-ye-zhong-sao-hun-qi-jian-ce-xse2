def header_match(manifest_issue: str, header_issue: str | None) -> bool | None:
    if not header_issue:
        return None
    return manifest_issue == header_issue

def evidence_score(item: dict) -> int:
    score = 0
    if item.get("header_issue"):
        score += 3 if item["header_issue"] == item.get("manifest_issue") else -5
    if item.get("page_match"):
        score += 2
    if item.get("phash_distance", 99) <= 3:
        score += 1
    return score

