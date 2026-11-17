from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from .service import demo

router = APIRouter()
ROWS = [{"key":"2026-11-01|01","status":"采纳","value":"28"},{"key":"2026-11-01|04","status":"隔离","value":"1"},{"key":"2026-11-02|02","status":"采纳","value":"26"}]

@router.get("/intake", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m1.html", "清单采信", "/api/scans/import", ROWS)

@router.post("/api/scans/import")
def execute():
    return demo()

