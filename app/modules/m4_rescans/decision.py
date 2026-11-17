def choose_scan(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("EMPTY_GROUP")
    return max(rows, key=lambda row: (int(row.get("clarity", 0)), str(row.get("captured_at", "")), str(row.get("file_name", ""))))

def classify_pair(left: dict, right: dict, candidate: bool) -> str:
    if left.get("sha256") == right.get("sha256"):
        return "EXACT_COPY"
    if candidate and left.get("issue") == right.get("issue") and left.get("page") == right.get("page"):
        return "RESCAN_CANDIDATE"
    return "DISTINCT"

