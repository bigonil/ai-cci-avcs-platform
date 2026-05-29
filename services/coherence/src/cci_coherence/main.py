"""Entry point for the Coherence Engine service."""
import uvicorn

from cci_coherence.api import app
from cci_coherence.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_config=None,  # structlog handles logging
    )


if __name__ == "__main__":
    main()
