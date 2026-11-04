import os, secrets, threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from .store import Store
from .fixtures import CASES
from .workflow import new_run, execute, draft
from .policy import read_local

ROOT = Path(__file__).resolve().parent.parent
store = Store()
pool = ThreadPoolExecutor(max_workers=1)
slot = threading.BoundedSemaphore(1)
TOKEN = secrets.token_urlsafe(32)


@asynccontextmanager
async def lifespan(app):
    store.recover()
    yield
    pool.shutdown(wait=False, cancel_futures=True)


app = FastAPI(
    title="ForgeAgent",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
)
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


class RunRequest(BaseModel):
    mode: Literal["demo", "ollama"] = "demo"
    case: Literal["average", "discount", "unique"] = "average"
    issue: str = Field(default="", max_length=12000)


@app.middleware("http")
async def guard(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("X-Forge-Token") != TOKEN:
            return PlainTextResponse(
                "Reload the dashboard to obtain a session token.", status_code=403
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/")
def index():
    return FileResponse(ROOT / "web/index.html")


@app.get("/api/config")
def config():
    return {
        "token": TOKEN,
        "cases": [
            {"id": k, "title": v["title"], "issue": v["issue"]}
            for k, v in CASES.items()
        ],
        "real_enabled": bool(os.environ.get("FORGE_REPO_PATH")),
        "model": os.environ.get("OLLAMA_MODEL", "Not configured"),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/runs")
def runs():
    return [
        {
            k: r.get(k)
            for k in ("id", "mode", "case", "status", "created", "elapsed", "issue")
        }
        for r in store.list()
    ]


@app.get("/api/runs/{id}")
def get_run(id: str):
    r = store.get(id)
    if not r:
        raise HTTPException(404, "Run not found")
    return r


@app.post("/api/runs", status_code=202)
def create(req: RunRequest):
    if not slot.acquire(blocking=False):
        raise HTTPException(409, "A run is in progress. Wait for it to finish.")
    try:
        files = None
        if req.mode == "ollama":
            path = os.environ.get("FORGE_REPO_PATH")
            if not path:
                raise ValueError(
                    "Configure FORGE_REPO_PATH before starting a real run."
                )
            files = read_local(path)
        r = new_run(req.mode, req.case, req.issue, files)
        store.save(r)

        def task():
            try:
                execute(r, store)
            finally:
                slot.release()

        pool.submit(task)
        return {"id": r["id"]}
    except Exception as e:
        slot.release()
        raise HTTPException(400, str(e)) from None


@app.get("/api/runs/{id}/patch", response_class=PlainTextResponse)
def patch(id: str):
    return PlainTextResponse(
        get_run(id).get("diff", ""),
        headers={"Content-Disposition": 'attachment; filename="changes.patch"'},
    )


@app.get("/api/runs/{id}/draft", response_class=PlainTextResponse)
def report(id: str):
    return PlainTextResponse(
        draft(get_run(id)),
        headers={"Content-Disposition": 'attachment; filename="PULL_REQUEST.md"'},
    )


@app.get("/docs", response_class=HTMLResponse)
def docs():
    return """<!doctype html><html lang="en"><meta charset="utf-8"><title>ForgeAgent API</title>
 <link rel="stylesheet" href="/static/style.css"><body><main><h1>ForgeAgent API</h1>
 <p>Local API. Bind to 127.0.0.1. <a href="/">Return to dashboard</a>.</p>
 <p><a href="/openapi.json">Download OpenAPI schema</a></p>
 <ul><li>GET /api/health — service health</li><li>GET /api/config — cases and session token</li>
 <li>POST /api/runs — start a run; X-Forge-Token header required</li>
 <li>GET /api/runs — latest 100 runs</li><li>GET /api/runs/{id} — full evidence</li>
 <li>GET /api/runs/{id}/patch — unified diff</li><li>GET /api/runs/{id}/draft — review report</li></ul>
 <p>POST body example:</p><pre>{"mode":"demo","case":"average"}</pre>
 <p>Read the token from /api/config, then send it in the X-Forge-Token header. No GitHub publication endpoint is exposed.</p>
 </main></body></html>"""
