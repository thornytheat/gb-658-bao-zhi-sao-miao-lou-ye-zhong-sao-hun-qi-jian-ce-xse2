import pytest
from fastapi.testclient import TestClient
from app.errors import DomainError
import app.store as store
from app.main import app
from app.modules.m7_settle import ledger, service
from app.modules.m7_settle.billing import classify_items, plan_correction
from app.modules.m7_settle.pricing import parse_price, money_str


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATABASE_PATH", tmp_path / "settle.db")


def scans():
    return [
        {"issue": "2026-11-01", "edition": "01", "page": "001", "file_name": "a.tif", "sha256": "A" * 64, "line_no": 2},
        {"issue": "2026-11-01", "edition": "01", "page": "002", "file_name": "b.tif", "sha256": "B" * 64, "line_no": 3},
        {"issue": "2026-11-01", "edition": "01", "page": "001", "file_name": "c.tif", "sha256": "A" * 64, "line_no": 4},
        {"issue": "2026-11-01", "edition": "01", "page": "003", "file_name": "d.tif", "sha256": "D" * 64, "line_no": 5},
        {"issue": "2026-11-01", "edition": "01", "page": "004", "file_name": "e.tif", "sha256": "E" * 64, "line_no": 6},
    ]


def reviews():
    return [
        {"file_name": "a.tif", "decision": "ACCEPTED"},
        {"file_name": "b.tif", "decision": "ACCEPTED"},
        {"file_name": "c.tif", "decision": "ACCEPTED"},
        {"file_name": "d.tif", "decision": "PENDING"},
        {"file_name": "e.tif", "decision": "REJECTED"},
    ]


def payload(**over):
    base = {"station_id": "ST-01", "period": "2026-11", "unit_price": "0.45", "scans": scans(), "reviews": reviews()}
    base.update(over)
    return base


def settle_and_sign(**over):
    stmt = service.settle(payload(**over))
    service.sign(stmt["statement_id"], {})
    return stmt["statement_id"]


def test_settle_bills_unique_accepted_once():
    stmt = service.settle(payload())
    assert stmt["created"] is True and stmt["status"] == "DRAFT" and stmt["version"] == 1
    assert (stmt["accepted_qty"], stmt["duplicate_qty"], stmt["held_qty"], stmt["excluded_qty"]) == (2, 1, 1, 1)
    assert stmt["gross_amount"] == "0.90" and stmt["unit_price"] == "0.45"


def test_duplicate_scan_not_billed_twice():
    items = classify_items(service.validate_scans(payload()["scans"]), {"a.tif": "ACCEPTED", "c.tif": "ACCEPTED"})
    billed = [item["file_name"] for item in items if item["billable"] == 1]
    assert billed == ["a.tif"]
    duplicate = next(item for item in items if item["file_name"] == "c.tif")
    assert duplicate["decision"] == "DUPLICATE" and duplicate["dup_of"] == "a.tif"


def test_same_page_different_content_billed_once():
    rows = [
        {"issue": "2026-11-01", "edition": "01", "page": "001", "file_name": "x.tif", "sha256": "X" * 64, "line_no": 1},
        {"issue": "2026-11-01", "edition": "01", "page": "001", "file_name": "y.tif", "sha256": "Y" * 64, "line_no": 2},
    ]
    items = classify_items(rows, {"x.tif": "ACCEPTED", "y.tif": "ACCEPTED"})
    assert [item["decision"] for item in items] == ["ACCEPTED", "DUPLICATE"]


def test_missing_review_is_held():
    items = classify_items(service.validate_scans(payload()["scans"]), {})
    assert all(item["decision"] == "HELD" for item in items)


def test_settle_is_idempotent_on_same_input():
    first = service.settle(payload())
    second = service.settle(payload())
    assert second["statement_id"] == first["statement_id"] and second["created"] is False
    assert len(ledger.list_items(first["statement_id"])) == 5


def test_same_period_different_input_rejected():
    service.settle(payload())
    changed = payload(scans=scans()[:4], reviews=reviews()[:4])
    with pytest.raises(DomainError, match="已存在结算单") as exc:
        service.settle(changed)
    assert exc.value.code == "STATEMENT_EXISTS" and exc.value.status == 409


def test_contract_price_mismatch_and_update():
    service.settle(payload())
    with pytest.raises(DomainError) as exc:
        service.settle(payload(period="2026-12", unit_price="0.50"))
    assert exc.value.code == "PRICE_MISMATCH"
    updated = service.settle(payload(period="2026-12", unit_price="0.50", contract_update=True))
    assert updated["unit_price"] == "0.5"
    old = service.settle(payload())
    assert old["unit_price"] == "0.45"  # 旧单保留原约定单价


def test_sign_freezes_voucher_and_is_idempotent():
    stmt = service.settle(payload())
    signed = service.sign(stmt["statement_id"], {"expected_version": 1})
    assert signed["status"] == "SIGNED" and signed["signed_amount"] == "0.90" and signed["version"] == 2
    again = service.sign(stmt["statement_id"], {})
    assert again["already_signed"] is True and again["version"] == 2 and again["signed_amount"] == "0.90"


def test_sign_with_stale_version_rejected():
    stmt = service.settle(payload())
    with pytest.raises(DomainError) as exc:
        service.sign(stmt["statement_id"], {"expected_version": 9})
    assert exc.value.code == "VERSION_STALE" and exc.value.status == 409


def test_correction_requires_signed_statement():
    stmt = service.settle(payload())
    with pytest.raises(DomainError) as exc:
        service.correct(stmt["statement_id"], {"base_version": 1, "reason": "r", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    assert exc.value.code == "NOT_SIGNED" and exc.value.status == 409


def test_correction_recovers_overpayment_and_keeps_voucher():
    statement_id = settle_and_sign()
    result = service.correct(statement_id, {"base_version": 2, "reason": "复核裁定 a.tif 废件", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    adjustment = result["adjustment"]
    assert adjustment["status"] == "POSTED" and adjustment["delta_qty"] == -1 and adjustment["delta_amount"] == "-0.45"
    reconcile = result["reconcile"]
    assert reconcile["original_paid"] == "0.90" and reconcile["adjustments_amount"] == "-0.45"
    assert reconcile["current_payable"] == "0.45" == reconcile["expected_payable"] and reconcile["balanced"] is True
    statement = result["statement"]
    assert statement["gross_amount"] == "0.90" and statement["signed_amount"] == "0.90"  # 旧单不重新计算
    original = next(item for item in result["items"] if item["file_name"] == "a.tif")
    assert original["decision"] == "ACCEPTED" and original["billable"] == 1  # 原依据保留


def test_correction_with_stale_version_rejected():
    statement_id = settle_and_sign()
    with pytest.raises(DomainError) as exc:
        service.correct(statement_id, {"base_version": 1, "reason": "r", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    assert exc.value.code == "VERSION_STALE" and exc.value.status == 409
    assert service.readback(statement_id)["adjustments"] == []


def test_correction_retry_deduplicated():
    statement_id = settle_and_sign()
    request = {"base_version": 2, "reason": "复核裁定 a.tif 废件", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]}
    first = service.correct(statement_id, request)
    second = service.correct(statement_id, dict(request))
    assert first["deduplicated"] is False and second["deduplicated"] is True
    assert second["adjustment"]["adjustment_id"] == first["adjustment"]["adjustment_id"]
    assert len(second["adjustments"]) == 1 and second["reconcile"]["current_payable"] == "0.45"  # 重试不重复补扣


def test_interrupted_posting_resumes():
    statement_id = settle_and_sign()
    calls = {"n": 0}
    real = ledger.resume_pending

    def flaky(sid):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("crash after reserve")
        return real(sid)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(ledger, "resume_pending", flaky)
    with pytest.raises(RuntimeError):
        service.correct(statement_id, {"base_version": 2, "reason": "复核裁定 a.tif 废件", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    monkeypatch.undo()

    pending = ledger.list_adjustments(statement_id)
    assert len(pending) == 1 and pending[0]["status"] == "PENDING"  # 差额落账中断
    recovered = service.readback(statement_id)
    assert recovered["adjustments"][0]["status"] == "POSTED"  # 接着恢复
    assert recovered["reconcile"]["current_payable"] == "0.45" and recovered["statement"]["version"] == 3
    retry = service.correct(statement_id, {"base_version": 2, "reason": "复核裁定 a.tif 废件", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    assert retry["deduplicated"] is True and len(retry["adjustments"]) == 1
    assert retry["reconcile"]["current_payable"] == "0.45"  # 恢复后重试仍不重复补扣


def test_held_item_adjudicated_adds_payment():
    statement_id = settle_and_sign()
    result = service.correct(statement_id, {"base_version": 2, "reason": "d.tif 裁决采纳", "decisions": [{"file_name": "d.tif", "decision": "ACCEPTED"}]})
    assert result["adjustment"]["delta_amount"] == "0.45"
    assert result["reconcile"]["current_payable"] == "1.35" and result["reconcile"]["balanced"] is True


def test_correction_cannot_double_bill_same_content():
    statement_id = settle_and_sign()
    with pytest.raises(DomainError) as exc:
        service.correct(statement_id, {"base_version": 2, "reason": "r", "decisions": [{"file_name": "c.tif", "decision": "ACCEPTED"}]})
    assert exc.value.code == "DUPLICATE_BILLING"
    service.correct(statement_id, {"base_version": 2, "reason": "a.tif 废件", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    promoted = service.correct(statement_id, {"base_version": 3, "reason": "c.tif 实为有效件", "decisions": [{"file_name": "c.tif", "decision": "ACCEPTED"}]})
    assert promoted["reconcile"]["current_payable"] == "0.90" and promoted["reconcile"]["balanced"] is True


def test_correction_no_change_rejected():
    statement_id = settle_and_sign()
    with pytest.raises(DomainError) as exc:
        service.correct(statement_id, {"base_version": 2, "reason": "r", "decisions": [{"file_name": "a.tif", "decision": "ACCEPTED"}]})
    assert exc.value.code == "NO_CHANGE"


def test_correction_unknown_item_rejected():
    statement_id = settle_and_sign()
    with pytest.raises(DomainError) as exc:
        service.correct(statement_id, {"base_version": 2, "reason": "r", "decisions": [{"file_name": "ghost.tif", "decision": "REJECTED"}]})
    assert exc.value.code == "UNKNOWN_REFERENCE"


def test_repeated_correction_with_new_version_applies_again():
    statement_id = settle_and_sign()
    service.correct(statement_id, {"base_version": 2, "reason": "复核改判", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    service.correct(statement_id, {"base_version": 3, "reason": "复核改判", "decisions": [{"file_name": "a.tif", "decision": "ACCEPTED"}]})
    third = service.correct(statement_id, {"base_version": 4, "reason": "复核改判", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    assert third["deduplicated"] is False and len(third["adjustments"]) == 3
    assert third["reconcile"]["current_payable"] == "0.45" and third["statement"]["version"] == 5


def test_plan_correction_guard_blocks_billing_twice():
    items = classify_items(service.validate_scans(payload()["scans"]), {"a.tif": "ACCEPTED", "c.tif": "ACCEPTED"})
    effective = {item["file_name"]: item["decision"] for item in items}
    with pytest.raises(DomainError, match="同一页只能计费一次"):
        plan_correction(items, effective, [{"file_name": "c.tif", "decision": "ACCEPTED"}])


def test_price_validation():
    with pytest.raises(DomainError) as exc:
        parse_price(None)
    assert exc.value.code == "EMPTY_VALUE"
    with pytest.raises(DomainError) as exc:
        parse_price("abc")
    assert exc.value.code == "BAD_FORMAT"
    with pytest.raises(DomainError) as exc:
        parse_price("-0.5")
    assert exc.value.code == "BAD_FORMAT"
    assert money_str(parse_price("0.455") * 1) == "0.46"


def test_settle_validation_errors():
    with pytest.raises(DomainError) as exc:
        service.settle(payload(scans=[]))
    assert exc.value.code == "EMPTY_VALUE"
    with pytest.raises(DomainError) as exc:
        service.settle(payload(scans=scans() + [scans()[0]]))
    assert exc.value.code == "DUPLICATE_KEY"
    with pytest.raises(DomainError) as exc:
        service.settle(payload(reviews=reviews() + [{"file_name": "ghost.tif", "decision": "ACCEPTED"}]))
    assert exc.value.code == "UNKNOWN_REFERENCE"
    with pytest.raises(DomainError) as exc:
        service.settle(payload(reviews=[{"file_name": "a.tif", "decision": "MAYBE"}]))
    assert exc.value.code == "BAD_FORMAT"


def test_readback_unknown_statement_404():
    with pytest.raises(DomainError) as exc:
        service.readback("ST-NONE")
    assert exc.value.status == 404


def test_demo_flow_reconciles_and_is_repeatable():
    first = service.demo()
    assert first["reconcile"]["balanced"] is True
    assert first["reconcile"]["original_paid"] == "0.90" and first["reconcile"]["current_payable"] == "0.90"
    assert first["reconcile"]["adjustments_count"] == 2 and first["reconcile"]["pending_adjustments"] == 0
    second = service.demo()
    assert second["settle"]["created"] is False and second["sign"]["already_signed"] is True
    assert all(step["deduplicated"] is True for step in second["corrections"])
    assert second["reconcile"] == first["reconcile"]


def test_api_settle_sign_correct_readback():
    client = TestClient(app)
    created = client.post("/api/settle/statements", json=payload()).json()
    statement_id = created["statement_id"]
    signed = client.post(f"/api/settle/statements/{statement_id}/sign", json={}).json()
    assert signed["status"] == "SIGNED"
    stale = client.post(f"/api/settle/statements/{statement_id}/corrections", json={"base_version": 1, "reason": "r", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]})
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "VERSION_STALE"
    corrected = client.post(f"/api/settle/statements/{statement_id}/corrections", json={"base_version": 2, "reason": "复核裁定 a.tif 废件", "decisions": [{"file_name": "a.tif", "decision": "REJECTED"}]}).json()
    assert corrected["reconcile"]["current_payable"] == "0.45"
    read = client.get(f"/api/settle/statements/{statement_id}").json()
    assert read["reconcile"]["balanced"] is True and len(read["items"]) == 5
    missing = client.get("/api/settle/statements/ST-NONE")
    assert missing.status_code == 404


def test_settle_page_accessible():
    client = TestClient(app)
    response = client.get("/settle")
    assert response.status_code == 200 and "panel" in response.text
