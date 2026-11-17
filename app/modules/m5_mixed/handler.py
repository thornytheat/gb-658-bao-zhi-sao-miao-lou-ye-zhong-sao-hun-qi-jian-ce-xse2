from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from .service import demo

router = APIRouter()
ROWS = [{"key":"2026-11-01|01","status":"页眉一致","value":"6"},{"key":"2026-11-02|01","status":"混期","value":"1"},{"key":"2026-11-03|S1","status":"待复核","value":"2"}]

@router.get("/mixed", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m5.html", "混期归因", "/api/mixed/evaluate", ROWS)

@router.post("/api/mixed/evaluate")
def execute():
    return demo()

