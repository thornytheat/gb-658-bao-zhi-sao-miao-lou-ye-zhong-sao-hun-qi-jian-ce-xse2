from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from .service import demo

router = APIRouter()
ROWS = [{"key":"2026-11-01|01","status":"缺页","value":"004"},{"key":"2026-11-02|02","status":"完整","value":"008"},{"key":"2026-11-03|01","status":"重页","value":"003"}]

@router.get("/pages", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m3.html", "页码序列", "/api/pages/check", ROWS)

@router.post("/api/pages/check")
def execute():
    return demo()

