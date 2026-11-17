from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from .service import demo

router = APIRouter()
ROWS = [{"key":"RUN-658-A","status":"守恒","value":"28"},{"key":"RUN-658-B","status":"复用","value":"28"},{"key":"RUN-658-C","status":"隔离","value":"3"}]

@router.get("/batches", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m6.html", "批次对账", "/api/reconcile", ROWS)

@router.post("/api/reconcile")
def execute():
    return demo()

@router.get("/api/export/evidence.csv")
def export_evidence():
    from fastapi.responses import PlainTextResponse
    from .exporter import evidence_csv
    body = evidence_csv([{"business_key": "2026-11-01|01|004", "line_no": 5, "reason_code": "MISSING_PAGE", "raw_value": "004"}])
    return PlainTextResponse(body, media_type="text/csv", headers={"content-disposition": "attachment; filename=evidence.csv"})
