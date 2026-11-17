import csv
import io

REQUIRED = ("issue", "edition", "page", "file_name", "sha256", "phash", "clarity", "header_issue")

def parse_manifest(text: str) -> tuple[list[dict], list[dict]]:
    if not text:
        return [], [{"line_no": 0, "reason_code": "EMPTY_FILE", "raw": ""}]
    stream = io.StringIO(text, newline="")
    reader = csv.DictReader(stream)
    if reader.fieldnames:
        reader.fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
    if not reader.fieldnames or any(name not in reader.fieldnames for name in REQUIRED):
        return [], [{"line_no": 1, "reason_code": "MISSING_COLUMN", "raw": ",".join(reader.fieldnames or [])}]
    accepted, bad = [], []
    for line_no, row in enumerate(reader, 2):
        if row.get("issue") == "issue":
            continue
        if None in row or any(row.get(key) is None for key in REQUIRED):
            bad.append({"line_no": line_no, "reason_code": "COLUMN_COUNT", "raw": str(row)})
            continue
        if not row["issue"].strip() or not row["page"].strip():
            bad.append({"line_no": line_no, "reason_code": "EMPTY_VALUE", "raw": str(row)})
            continue
        row["line_no"] = line_no
        accepted.append(row)
    return accepted, bad

