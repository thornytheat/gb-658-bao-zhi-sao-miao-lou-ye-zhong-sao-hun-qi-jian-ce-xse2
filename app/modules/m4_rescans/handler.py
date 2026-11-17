from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from .service import demo

router = APIRouter()
ROWS = [{"key":"01|001","status":"保留新版","value":"92"},{"key":"01|002","status":"非重扫","value":"88"},{"key":"02|004","status":"待复核","value":"81"}]

@router.get("/rescans", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m4.html", "重扫判定", "/api/rescans/evaluate", ROWS)

@router.post("/api/rescans/evaluate")
def execute():
    return demo()

