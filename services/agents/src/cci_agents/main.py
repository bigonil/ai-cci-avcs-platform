"""Entry point for the CCI Agents service."""
import uvicorn

from cci_agents.api import app
from cci_agents.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()
