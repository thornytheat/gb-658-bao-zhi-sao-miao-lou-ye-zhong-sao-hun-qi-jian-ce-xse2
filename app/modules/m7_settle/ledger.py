import sqlite3
from datetime import datetime, timedelta, timezone
from app.errors import DomainError
from app.store import connect

OFFSET = timezone(timedelta(hours=8), name="CST")  # Asia/Shanghai 固定 +08:00，不依赖 tzdata

SCHEMA = """
CREATE TABLE IF NOT EXISTS settle_contracts (
  station_id TEXT PRIMARY KEY,
  unit_price TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settle_statements (
  statement_id TEXT PRIMARY KEY,
  station_id TEXT NOT NULL,
  period TEXT NOT NULL,
  unit_price TEXT NOT NULL,
  input_sha256 TEXT NOT NULL,
  accepted_qty INTEGER NOT NULL,
  held_qty INTEGER NOT NULL,
  duplicate_qty INTEGER NOT NULL,
  excluded_qty INTEGER NOT NULL,
  gross_amount TEXT NOT NULL,
  signed_amount TEXT,
  status TEXT NOT NULL,
  version INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  signed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_settle_statements_period ON settle_statements (station_id, period);
CREATE TABLE IF NOT EXISTS settle_items (
  statement_id TEXT NOT NULL,
  file_name TEXT NOT NULL,
  business_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  line_no INTEGER NOT NULL,
  decision TEXT NOT NULL,
  billable INTEGER NOT NULL,
  dup_of TEXT,
  PRIMARY KEY (statement_id, file_name)
);
CREATE TABLE IF NOT EXISTS settle_adjustments (
  adjustment_id TEXT PRIMARY KEY,
  statement_id TEXT NOT NULL,
  base_version INTEGER NOT NULL,
  reason TEXT NOT NULL,
  changes_json TEXT NOT NULL,
  delta_qty INTEGER NOT NULL,
  delta_amount TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  posted_at TEXT
);
"""

def now_iso() -> str:
    return datetime.now(OFFSET).isoformat(timespec="seconds")

def init_ledger() -> None:
    with connect() as db:
        db.executescript(SCHEMA)

def _tx():
    init_ledger()
    db = connect()
    db.row_factory = sqlite3.Row
    db.execute("BEGIN IMMEDIATE")
    return db

def _read(sql: str, args: tuple = (), one: bool = False):
    init_ledger()
    db = connect()
    db.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in db.execute(sql, args).fetchall()]
        return (rows[0] if rows else None) if one else rows
    finally:
        db.close()

def get_statement(statement_id: str) -> dict | None:
    return _read("SELECT * FROM settle_statements WHERE statement_id=?", (statement_id,), one=True)

def get_adjustment(adjustment_id: str) -> dict | None:
    return _read("SELECT * FROM settle_adjustments WHERE adjustment_id=?", (adjustment_id,), one=True)

def list_items(statement_id: str) -> list[dict]:
    return _read("SELECT * FROM settle_items WHERE statement_id=? ORDER BY line_no", (statement_id,))

def list_adjustments(statement_id: str) -> list[dict]:
    return _read("SELECT * FROM settle_adjustments WHERE statement_id=? ORDER BY rowid", (statement_id,))

def create_statement(stmt: dict, items: list[dict], contract_update: bool) -> bool:
    """登记站点约定单价并写入结算单与明细；同账期已有结算单时拒绝重算。"""
    db = _tx()
    try:
        contract = db.execute("SELECT unit_price FROM settle_contracts WHERE station_id=?", (stmt["station_id"],)).fetchone()
        if contract is None:
            db.execute("INSERT INTO settle_contracts VALUES (?,?,?)", (stmt["station_id"], stmt["unit_price"], now_iso()))
        elif contract["unit_price"] != stmt["unit_price"]:
            if not contract_update:
                raise DomainError("PRICE_MISMATCH", f"站点 {stmt['station_id']} 的约定单价为 {contract['unit_price']}，与本次 {stmt['unit_price']} 不一致", 409)
            db.execute("UPDATE settle_contracts SET unit_price=?, updated_at=? WHERE station_id=?", (stmt["unit_price"], now_iso(), stmt["station_id"]))
        try:
            db.execute("INSERT INTO settle_statements VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (stmt["statement_id"], stmt["station_id"], stmt["period"], stmt["unit_price"], stmt["input_sha256"], stmt["accepted_qty"], stmt["held_qty"], stmt["duplicate_qty"], stmt["excluded_qty"], stmt["gross_amount"], stmt["signed_amount"], stmt["status"], stmt["version"], stmt["created_at"], stmt["signed_at"]))
        except sqlite3.IntegrityError:
            db.rollback()
            if get_statement(stmt["statement_id"]) is not None:
                return False
            raise DomainError("STATEMENT_EXISTS", f"站点 {stmt['station_id']} 账期 {stmt['period']} 已存在结算单，签收后的变更请走更正补扣", 409)
        for item in items:
            db.execute("INSERT INTO settle_items VALUES (?,?,?,?,?,?,?,?)", (stmt["statement_id"], item["file_name"], item["business_key"], item["sha256"], item["line_no"], item["decision"], item["billable"], item["dup_of"]))
        db.commit()
        return True
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

def sign_statement(statement_id: str, expected_version: int | None) -> dict:
    """签收即冻结应付金额；重复签收幂等返回，版本过期拒绝。"""
    db = _tx()
    try:
        row = db.execute("SELECT * FROM settle_statements WHERE statement_id=?", (statement_id,)).fetchone()
        stmt = dict(row) if row is not None else None
        if stmt is None:
            raise DomainError("STATEMENT_NOT_FOUND", f"结算单 {statement_id} 不存在", 404)
        if stmt["status"] == "SIGNED":
            db.commit()
            return {**stmt, "already_signed": True}
        if expected_version is not None and expected_version != stmt["version"]:
            raise DomainError("VERSION_STALE", f"结算单当前版本为 {stmt['version']}，签收依据的版本 {expected_version} 已过期", 409)
        db.execute("UPDATE settle_statements SET status='SIGNED', version=version+1, signed_amount=gross_amount, signed_at=? WHERE statement_id=?", (now_iso(), statement_id))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return {**get_statement(statement_id), "already_signed": False}

def reserve_adjustment(statement_id: str, base_version: int, adjustment_id: str, reason: str, changes_json: str, delta_qty: int, delta_amount: str) -> None:
    """在同一事务内校验版本、登记 PENDING 差额并递增版本，过期版本在此被拒绝。"""
    db = _tx()
    try:
        row = db.execute("SELECT version, status FROM settle_statements WHERE statement_id=?", (statement_id,)).fetchone()
        if row is None:
            raise DomainError("STATEMENT_NOT_FOUND", f"结算单 {statement_id} 不存在", 404)
        if row["status"] != "SIGNED":
            raise DomainError("NOT_SIGNED", "结算单未签收，不能登记更正", 409)
        if row["version"] != base_version:
            raise DomainError("VERSION_STALE", f"结算单当前版本为 {row['version']}，基于版本 {base_version} 的更正已过期", 409)
        db.execute("INSERT INTO settle_adjustments VALUES (?,?,?,?,?,?,?,?,?,NULL)", (adjustment_id, statement_id, base_version, reason, changes_json, delta_qty, delta_amount, "PENDING", now_iso()))
        db.execute("UPDATE settle_statements SET version=version+1 WHERE statement_id=?", (statement_id,))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

def resume_pending(statement_id: str) -> int:
    """把中断时残留的 PENDING 差额逐条落账；按状态翻转，重试不会重复补扣。"""
    init_ledger()
    with connect() as db:
        ids = [row[0] for row in db.execute("SELECT adjustment_id FROM settle_adjustments WHERE statement_id=? AND status='PENDING' ORDER BY rowid", (statement_id,))]
    posted = 0
    for adjustment_id in ids:
        with connect() as db:
            cursor = db.execute("UPDATE settle_adjustments SET status='POSTED', posted_at=? WHERE adjustment_id=? AND status='PENDING'", (now_iso(), adjustment_id))
            posted += cursor.rowcount
    return posted
