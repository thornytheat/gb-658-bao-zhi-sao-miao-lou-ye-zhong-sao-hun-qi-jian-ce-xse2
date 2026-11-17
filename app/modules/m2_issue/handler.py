from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from .service import demo

router = APIRouter()
ROWS = [{"key":"2026-11-01|01|001","status":"标准版","value":"1"},{"key":"2026-11-01|S1|001","status":"增刊","value":"1"},{"key":"2026-11-02|02|004","status":"标准版","value":"4"}]

@router.get("/issues", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m2.html", "期版契约", "/api/issues/normalize", ROWS)

@router.post("/api/issues/normalize")
def execute():
    return demo()

