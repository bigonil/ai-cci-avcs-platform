"""Entry point — avvia ingestion-service con uvicorn."""
from __future__ import annotations

import uvicorn

from cci_ingestion.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "cci_ingestion.api:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        access_log=False,  # log strutturati via structlog
    )
