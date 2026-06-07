from contextlib import asynccontextmanager
from fastapi import FastAPI
from .health import router as health_router
from .proxy import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="CCI/AVCS Frontend BFF", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(proxy_router, prefix="/api")
