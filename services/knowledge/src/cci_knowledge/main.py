"""Entry point for the CCI Knowledge Service."""
from __future__ import annotations

import uvicorn

from cci_knowledge.api import app
from cci_knowledge.config import get_settings


def main() -> None:
    cfg = get_settings()
    uvicorn.run(
        "cci_knowledge.api:app",
        host="0.0.0.0",
        port=cfg.port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
