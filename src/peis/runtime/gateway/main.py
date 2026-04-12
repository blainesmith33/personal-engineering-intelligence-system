from __future__ import annotations

import uvicorn

from peis.runtime.gateway.api import app
from peis.runtime.gateway.config import load_gateway_config


def run() -> None:
    """
    Canonical gateway service entrypoint.

    This is the only runtime launcher for the PEIS gateway.
    It loads authoritative config and starts the FastAPI app.
    """
    config = load_gateway_config()

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )


if __name__ == "__main__":
    run()