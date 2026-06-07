from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/startup")
async def startup() -> dict[str, str]:
    return {"status": "ok"}
