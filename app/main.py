from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import APP_VERSION
from app.store import init_db
from app.modules.m1_intake.handler import router as m1_intake_router
from app.modules.m2_issue.handler import router as m2_issue_router
from app.modules.m3_pages.handler import router as m3_pages_router
from app.modules.m4_rescans.handler import router as m4_rescans_router
from app.modules.m5_mixed.handler import router as m5_mixed_router
from app.modules.m6_batches.handler import router as m6_batches_router

app = FastAPI(title="扫描期版质检台", version=APP_VERSION)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")
app.state.version = APP_VERSION
app.include_router(m1_intake_router)
app.include_router(m2_issue_router)
app.include_router(m3_pages_router)
app.include_router(m4_rescans_router)
app.include_router(m5_mixed_router)
app.include_router(m6_batches_router)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/intake")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": APP_VERSION}

