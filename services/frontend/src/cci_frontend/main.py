import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .health import router as health_router
from .proxy import router as proxy_router

DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", "/app/dist"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CCI/AVCS Frontend BFF", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(proxy_router, prefix="/api")

# Static assets (JS/CSS/images) — mount ONLY if dist dir exists (skip in dev)
if DIST_DIR.exists():
    _assets = DIST_DIR / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(str(DIST_DIR / "index.html"))
