from app.errors import DomainError

REVIEW_DECISIONS = {"ACCEPTED", "REJECTED", "PENDING", "SUPERSEDED"}
CORRECTION_DECISIONS = {"ACCEPTED", "REJECTED", "HELD"}
SCAN_FIELDS = ("issue", "edition", "page", "file_name", "sha256")

def business_key(scan: dict) -> str:
    return "|".join((scan["issue"], scan["edition"], scan["page"]))

def billable_of(decision: str) -> int:
    return 1 if decision == "ACCEPTED" else 0

def validate_scans(raw) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        raise DomainError("EMPTY_VALUE", "扫描清单 scans 不能为空")
    seen, scans = set(), []
    for index, row in enumerate(raw, 1):
        if not isinstance(row, dict):
            raise DomainError("BAD_FORMAT", "扫描行必须是对象")
        item = {}
        for field in SCAN_FIELDS:
            value = row.get(field)
            if value is None or not str(value).strip():
                raise DomainError("EMPTY_VALUE", f"扫描行缺少 {field}")
            item[field] = str(value).strip()
        if item["file_name"] in seen:
            raise DomainError("DUPLICATE_KEY", f"扫描件 {item['file_name']} 在清单中重复")
        seen.add(item["file_name"])
        line_no = row.get("line_no", index)
        if isinstance(line_no, bool) or not isinstance(line_no, int) or line_no < 1:
            raise DomainError("BAD_FORMAT", "line_no 必须是正整数")
        item["line_no"] = line_no
        scans.append(item)
    return scans

def validate_reviews(raw, known_files: set) -> dict:
    if raw is None:
        return {}
    if not isinstance(raw, list):
        raise DomainError("BAD_FORMAT", "复核结果 reviews 必须是数组")
    reviews = {}
    for row in raw:
        if not isinstance(row, dict):
            raise DomainError("BAD_FORMAT", "复核行必须是对象")
        file_name = str(row.get("file_name") or "").strip()
        if not file_name:
            raise DomainError("EMPTY_VALUE", "复核行缺少 file_name")
        if file_name not in known_files:
            raise DomainError("UNKNOWN_REFERENCE", f"复核对象 {file_name} 不在扫描清单中")
        decision = row.get("decision")
        if decision not in REVIEW_DECISIONS:
            raise DomainError("BAD_FORMAT", f"复核结论 {decision!r} 非法")
        if file_name in reviews:
            raise DomainError("DUPLICATE_KEY", f"复核结果 {file_name} 重复")
        reviews[file_name] = decision
    return reviews

def validate_correction_requests(raw, known_files: set) -> list[dict]:
    if not isinstance(raw, list) or not raw:
        raise DomainError("EMPTY_VALUE", "更正决策 decisions 不能为空")
    seen, requests = set(), []
    for row in raw:
        if not isinstance(row, dict):
            raise DomainError("BAD_FORMAT", "更正行必须是对象")
        file_name = str(row.get("file_name") or "").strip()
        if not file_name:
            raise DomainError("EMPTY_VALUE", "更正行缺少 file_name")
        if file_name not in known_files:
            raise DomainError("UNKNOWN_REFERENCE", f"更正对象 {file_name} 不在结算单中")
        decision = row.get("decision")
        if decision not in CORRECTION_DECISIONS:
            raise DomainError("BAD_FORMAT", f"更正结论 {decision!r} 非法，仅支持 ACCEPTED/REJECTED/HELD")
        if file_name in seen:
            raise DomainError("DUPLICATE_KEY", f"更正对象 {file_name} 重复")
        seen.add(file_name)
        requests.append({"file_name": file_name, "decision": decision})
    return requests

def classify_items(scans: list[dict], reviews: dict) -> list[dict]:
    """按复核结论确定计费状态：未裁决暂挂，同摘要或同页键的重扫件不重复计费。"""
    items, seen_sha, seen_key = [], {}, {}
    for scan in sorted(scans, key=lambda row: row["line_no"]):
        decision = reviews.get(scan["file_name"], "PENDING")
        if decision == "PENDING":
            decision = "HELD"
        dup_of = None
        if decision == "ACCEPTED":
            key = business_key(scan)
            dup_of = seen_sha.get(scan["sha256"]) or seen_key.get(key)
            if dup_of is None:
                seen_sha[scan["sha256"]] = scan["file_name"]
                seen_key[key] = scan["file_name"]
            else:
                decision = "DUPLICATE"
        items.append({"file_name": scan["file_name"], "business_key": business_key(scan), "sha256": scan["sha256"], "line_no": scan["line_no"], "decision": decision, "billable": billable_of(decision), "dup_of": dup_of})
    return items

def plan_correction(items: list[dict], effective: dict, requests: list[dict]) -> tuple[list[dict], int]:
    """在当前有效结论上应用更正，保证同一内容或同一页不会同时计费。"""
    by_file = {item["file_name"]: item for item in items}
    changes = []
    for request in requests:
        file_name, target = request["file_name"], request["decision"]
        source = effective[file_name]
        if source == target:
            continue
        if target == "ACCEPTED":
            mine = by_file[file_name]
            for other in items:
                if other["file_name"] == file_name or effective.get(other["file_name"]) != "ACCEPTED":
                    continue
                if other["sha256"] == mine["sha256"] or other["business_key"] == mine["business_key"]:
                    raise DomainError("DUPLICATE_BILLING", f"{file_name} 与 {other['file_name']} 内容或页键相同，同一页只能计费一次")
        changes.append({"file_name": file_name, "from": source, "to": target})
        effective[file_name] = target
    if not changes:
        raise DomainError("NO_CHANGE", "更正未改变任何件的计费状态")
    delta_qty = sum(billable_of(change["to"]) - billable_of(change["from"]) for change in changes)
    return changes, delta_qty
