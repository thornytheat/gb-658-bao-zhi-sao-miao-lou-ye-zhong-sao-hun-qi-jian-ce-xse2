from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.web import page
from . import service

router = APIRouter()
ROWS = [{"key":"ST-DEMO|2026-11","status":"已签收","value":"0.90"},{"key":"ADJ 补扣|a.tif","status":"已落账","value":"-0.45"},{"key":"ADJ 补计|d.tif","status":"已落账","value":"+0.45"}]

@router.get("/settle", response_class=HTMLResponse)
def view(request: Request):
    return page(request, "m7.html", "结算补扣", "/api/settle/demo", ROWS)

@router.post("/api/settle/statements")
def create_statement(payload: dict):
    return service.settle(payload)

@router.post("/api/settle/statements/{statement_id}/sign")
def sign_statement(statement_id: str, payload: dict | None = None):
    return service.sign(statement_id, payload or {})

@router.post("/api/settle/statements/{statement_id}/corrections")
def correct_statement(statement_id: str, payload: dict):
    return service.correct(statement_id, payload)

@router.get("/api/settle/statements/{statement_id}")
def read_statement(statement_id: str):
    return service.readback(statement_id)

@router.post("/api/settle/demo")
def demo():
    return service.demo()
