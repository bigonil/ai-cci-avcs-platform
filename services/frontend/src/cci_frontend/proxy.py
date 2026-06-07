import os
import httpx
from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter()

COHERENCE_URL = os.getenv("COHERENCE_SERVICE_URL", "http://coherence:8003")
GOVERNANCE_URL = os.getenv("GOVERNANCE_SERVICE_URL", "http://governance:8005")

@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def proxy(path: str, request: Request) -> Response:
    # Re-read env vars so they can be changed in tests via monkeypatch
    route_map = {
        "incoherences": os.getenv("COHERENCE_SERVICE_URL", "http://coherence:8003"),
        "hitl": os.getenv("GOVERNANCE_SERVICE_URL", "http://governance:8005"),
        "audit": os.getenv("GOVERNANCE_SERVICE_URL", "http://governance:8005"),
    }
    prefix = path.split("/")[0]
    base = route_map.get(prefix)
    if base is None:
        raise HTTPException(status_code=404, detail=f"No upstream for path: {path}")

    qs = f"?{request.url.query}" if request.url.query else ""
    url = f"{base}/{path}{qs}"
    body = await request.body()
    skip_headers = {"host", "content-length", "transfer-encoding"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in skip_headers}

    client: httpx.AsyncClient = request.app.state.http_client
    try:
        upstream_resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {type(exc).__name__}")

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers={k: v for k, v in upstream_resp.headers.items() if k.lower() != "transfer-encoding"},
        media_type=upstream_resp.headers.get("content-type"),
    )
