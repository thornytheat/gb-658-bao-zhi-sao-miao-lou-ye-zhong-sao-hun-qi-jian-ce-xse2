import json
import sqlite3
from decimal import Decimal
from hashlib import sha256
from app.errors import DomainError
from . import ledger
from .billing import SCAN_FIELDS, validate_scans, validate_reviews, validate_correction_requests, classify_items, plan_correction
from .pricing import parse_price, price_str, money_str, amount_str

def _require_str(payload: dict, field: str) -> str:
    value = payload.get(field)
    if value is None or not str(value).strip():
        raise DomainError("EMPTY_VALUE", f"缺少字段 {field}")
    return str(value).strip()

def _require_version(payload: dict) -> int:
    value = payload.get("base_version")
    if value is None:
        raise DomainError("EMPTY_VALUE", "缺少基准版本 base_version")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DomainError("BAD_FORMAT", "base_version 必须是正整数")
    return value

def _input_digest(station_id: str, period: str, unit_price: str, scans: list[dict], reviews: dict) -> str:
    canonical = {"station_id": station_id, "period": period, "unit_price": unit_price,
                 "scans": [{**{field: scan[field] for field in SCAN_FIELDS}, "line_no": scan["line_no"]} for scan in sorted(scans, key=lambda row: row["line_no"])],
                 "reviews": sorted(reviews.items())}
    return sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()

def _adjustment_id(statement_id: str, base_version: int, reason: str, requests: list[dict]) -> str:
    canonical = json.dumps({"statement_id": statement_id, "base_version": base_version, "reason": reason,
                            "decisions": sorted(requests, key=lambda row: row["file_name"])},
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"ADJ-{sha256(canonical.encode('utf-8')).hexdigest()[:12]}"

def statement_view(stmt: dict, **flags) -> dict:
    keys = ("statement_id", "station_id", "period", "unit_price", "status", "version", "accepted_qty", "held_qty", "duplicate_qty", "excluded_qty", "gross_amount", "signed_amount", "created_at", "signed_at")
    return {**{key: stmt[key] for key in keys}, **flags}

def item_view(item: dict) -> dict:
    return {key: item[key] for key in ("file_name", "business_key", "sha256", "line_no", "decision", "billable", "dup_of")}

def adjustment_view(adjustment: dict) -> dict:
    return {"adjustment_id": adjustment["adjustment_id"], "statement_id": adjustment["statement_id"], "base_version": adjustment["base_version"], "reason": adjustment["reason"], "changes": json.loads(adjustment["changes_json"]), "delta_qty": adjustment["delta_qty"], "delta_amount": adjustment["delta_amount"], "status": adjustment["status"], "created_at": adjustment["created_at"], "posted_at": adjustment["posted_at"]}

def reconcile_view(stmt: dict, adjustments: list[dict]) -> dict:
    posted = [row for row in adjustments if row["status"] == "POSTED"]
    delta_qty = sum(row["delta_qty"] for row in posted)
    delta_amount = sum((Decimal(row["delta_amount"]) for row in posted), Decimal("0"))
    effective_qty = stmt["accepted_qty"] + delta_qty
    expected = amount_str(Decimal(stmt["unit_price"]), effective_qty)
    signed = stmt["status"] == "SIGNED"
    current = money_str(Decimal(stmt["signed_amount"]) + delta_amount) if signed else stmt["gross_amount"]
    return {"original_paid": stmt["signed_amount"] if signed else None, "adjustments_count": len(posted), "adjustments_qty": delta_qty, "adjustments_amount": money_str(delta_amount), "pending_adjustments": len(adjustments) - len(posted), "effective_qty": effective_qty, "current_payable": current, "expected_payable": expected, "balanced": current == expected}

def settle(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise DomainError("BAD_FORMAT", "请求体必须是对象")
    station_id = _require_str(payload, "station_id")
    period = _require_str(payload, "period")
    price = parse_price(payload.get("unit_price"))
    scans = validate_scans(payload.get("scans"))
    reviews = validate_reviews(payload.get("reviews"), {scan["file_name"] for scan in scans})
    items = classify_items(scans, reviews)
    unit_price = price_str(price)
    digest = _input_digest(station_id, period, unit_price, scans, reviews)
    statement_id = f"ST-{station_id}-{period}-{digest[:8]}"
    existing = ledger.get_statement(statement_id)
    if existing is not None:
        return statement_view(existing, created=False)
    stmt = {"statement_id": statement_id, "station_id": station_id, "period": period, "unit_price": unit_price, "input_sha256": digest,
            "accepted_qty": sum(1 for item in items if item["decision"] == "ACCEPTED"),
            "held_qty": sum(1 for item in items if item["decision"] == "HELD"),
            "duplicate_qty": sum(1 for item in items if item["decision"] == "DUPLICATE"),
            "excluded_qty": sum(1 for item in items if item["decision"] in ("REJECTED", "SUPERSEDED")),
            "gross_amount": amount_str(price, sum(1 for item in items if item["decision"] == "ACCEPTED")),
            "signed_amount": None, "status": "DRAFT", "version": 1, "created_at": ledger.now_iso(), "signed_at": None}
    created = ledger.create_statement(stmt, items, bool(payload.get("contract_update")))
    return statement_view(ledger.get_statement(statement_id), created=created)

def sign(statement_id: str, payload: dict) -> dict:
    expected = payload.get("expected_version")
    if expected is not None and (isinstance(expected, bool) or not isinstance(expected, int) or expected < 1):
        raise DomainError("BAD_FORMAT", "expected_version 必须是正整数")
    result = ledger.sign_statement(statement_id, expected)
    already_signed = result.pop("already_signed")
    return statement_view(result, already_signed=already_signed)

def correct(statement_id: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise DomainError("BAD_FORMAT", "请求体必须是对象")
    ledger.resume_pending(statement_id)
    stmt = ledger.get_statement(statement_id)
    if stmt is None:
        raise DomainError("STATEMENT_NOT_FOUND", f"结算单 {statement_id} 不存在", 404)
    if stmt["status"] != "SIGNED":
        raise DomainError("NOT_SIGNED", "结算单未签收，不能登记更正", 409)
    base_version = _require_version(payload)
    reason = _require_str(payload, "reason")
    items = ledger.list_items(statement_id)
    requests = validate_correction_requests(payload.get("decisions"), {item["file_name"] for item in items})
    adjustment_id = _adjustment_id(statement_id, base_version, reason, requests)
    if ledger.get_adjustment(adjustment_id) is not None:
        ledger.resume_pending(statement_id)
        return {**readback(statement_id), "adjustment": adjustment_view(ledger.get_adjustment(adjustment_id)), "deduplicated": True}
    effective = {item["file_name"]: item["decision"] for item in items}
    for adjustment in ledger.list_adjustments(statement_id):
        if adjustment["status"] != "POSTED":
            continue
        for change in json.loads(adjustment["changes_json"]):
            effective[change["file_name"]] = change["to"]
    changes, delta_qty = plan_correction(items, effective, requests)
    delta_amount = amount_str(Decimal(stmt["unit_price"]), delta_qty)
    changes_json = json.dumps(changes, ensure_ascii=False, sort_keys=True)
    try:
        ledger.reserve_adjustment(statement_id, base_version, adjustment_id, reason, changes_json, delta_qty, delta_amount)
    except sqlite3.IntegrityError:
        ledger.resume_pending(statement_id)
        return {**readback(statement_id), "adjustment": adjustment_view(ledger.get_adjustment(adjustment_id)), "deduplicated": True}
    ledger.resume_pending(statement_id)
    return {**readback(statement_id), "adjustment": adjustment_view(ledger.get_adjustment(adjustment_id)), "deduplicated": False}

def readback(statement_id: str) -> dict:
    ledger.resume_pending(statement_id)
    stmt = ledger.get_statement(statement_id)
    if stmt is None:
        raise DomainError("STATEMENT_NOT_FOUND", f"结算单 {statement_id} 不存在", 404)
    items = ledger.list_items(statement_id)
    adjustments = ledger.list_adjustments(statement_id)
    return {"statement": statement_view(stmt), "items": [item_view(item) for item in items], "adjustments": [adjustment_view(row) for row in adjustments], "reconcile": reconcile_view(stmt, adjustments)}

SAMPLE_SCANS = [
    {"issue": "2026-11-01", "edition": "01", "page": "001", "file_name": "a.tif", "sha256": "aa" * 32, "line_no": 2},
    {"issue": "2026-11-01", "edition": "01", "page": "002", "file_name": "b.tif", "sha256": "bb" * 32, "line_no": 3},
    {"issue": "2026-11-01", "edition": "01", "page": "001", "file_name": "c.tif", "sha256": "aa" * 32, "line_no": 4},
    {"issue": "2026-11-01", "edition": "01", "page": "003", "file_name": "d.tif", "sha256": "dd" * 32, "line_no": 5},
    {"issue": "2026-11-01", "edition": "01", "page": "004", "file_name": "e.tif", "sha256": "ee" * 32, "line_no": 6},
]
SAMPLE_REVIEWS = [
    {"file_name": "a.tif", "decision": "ACCEPTED"},
    {"file_name": "b.tif", "decision": "ACCEPTED"},
    {"file_name": "c.tif", "decision": "ACCEPTED"},
    {"file_name": "d.tif", "decision": "PENDING"},
    {"file_name": "e.tif", "decision": "REJECTED"},
]

def demo() -> dict:
    created = settle({"station_id": "ST-DEMO", "period": "2026-11", "unit_price": "0.45", "scans": SAMPLE_SCANS, "reviews": SAMPLE_REVIEWS})
    statement_id = created["statement_id"]
    signed = sign(statement_id, {})
    recovered = correct(statement_id, {"base_version": 2, "reason": "复核裁定 a.tif 为废件，追回错付", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    released = correct(statement_id, {"base_version": 3, "reason": "暂挂件 d.tif 裁决采纳，补计一页", "decisions": [{"file_name": "d.tif", "decision": "ACCEPTED"}]})
    final = readback(statement_id)
    return {"statement_id": statement_id, "settle": created, "sign": signed,
            "corrections": [{"adjustment": recovered["adjustment"], "deduplicated": recovered["deduplicated"]}, {"adjustment": released["adjustment"], "deduplicated": released["deduplicated"]}],
            "reconcile": final["reconcile"]}
