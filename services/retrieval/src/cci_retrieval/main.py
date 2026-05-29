"""Entry point for the CCI Retrieval Service."""
from __future__ import annotations

import uvicorn

from cci_retrieval.config import get_settings


def main() -> None:
    cfg = get_settings()
    uvicorn.run(
        "cci_retrieval.api:app",
        host="0.0.0.0",
        port=cfg.port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
