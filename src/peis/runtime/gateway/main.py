from __future__ import annotations

import importlib

import uvicorn

from peis.runtime.gateway.config import (
    GatewayConfigError,
    build_gateway_startup_error_message,
    load_gateway_config,
)


def run() -> None:
    """
    Canonical gateway service entrypoint.

    This is the only runtime launcher for the PEIS gateway.
    It loads authoritative config and starts the FastAPI app.
    """
    try:
        config = load_gateway_config()
    except GatewayConfigError as exc:
        raise SystemExit(build_gateway_startup_error_message(exc)) from exc

    try:
        api_module = importlib.import_module("peis.runtime.gateway.api")
        app = getattr(api_module, "app")
    except Exception as exc:
        raise SystemExit(f"PEIS gateway startup failed.\n\nApplication import error: {exc}") from exc

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        raise SystemExit(130)