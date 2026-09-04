"""Reviewed lazy Uvicorn provider for the Marketplace loopback runtime boundary.

Importing this module performs no provider import, package installation, socket
operation, server startup, environment loading, or filesystem discovery.
"""
from __future__ import annotations

from importlib import import_module
from typing import Final

from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT

UVICORN_DISTRIBUTION: Final = "uvicorn"
UVICORN_VERSION: Final = "0.52.4"
CLICK_VERSION: Final = "8.5.0"
H11_VERSION: Final = "0.16.0"


class MarketplaceUvicornProviderError(RuntimeError):
    """Stable provider-boundary failure without third-party detail reflection."""


def _validate_invocation(*, application: object, host: str, port: int) -> None:
    if not callable(application):
        raise TypeError("application MUST be callable")
    if type(host) is not str:
        raise TypeError("host MUST be an exact string")
    if host != LOOPBACK_LAUNCH_HOST:
        raise ValueError("host MUST be exact IPv4 loopback")
    if type(port) is not int:
        raise TypeError("port MUST be an exact integer")
    if port < MIN_LAUNCH_PORT or port > MAX_LAUNCH_PORT:
        raise ValueError("port is outside the reviewed TCP range")


class UvicornLoopbackServerProvider:
    """Lazy foreground provider with a fixed, loopback-only Uvicorn surface."""

    def run(self, *, application: object, host: str, port: int) -> None:
        _validate_invocation(application=application, host=host, port=port)

        try:
            uvicorn = import_module(UVICORN_DISTRIBUTION)
            run = uvicorn.run
        except Exception:
            raise MarketplaceUvicornProviderError(
                "MARKETPLACE_UVICORN_PROVIDER_UNAVAILABLE"
            ) from None
        if not callable(run):
            raise MarketplaceUvicornProviderError(
                "MARKETPLACE_UVICORN_PROVIDER_UNAVAILABLE"
            )

        try:
            run(
                application,
                host=LOOPBACK_LAUNCH_HOST,
                port=port,
                uds=None,
                fd=None,
                loop="asyncio",
                http="h11",
                ws="none",
                lifespan="off",
                interface="asgi3",
                reload=False,
                workers=1,
                env_file=None,
                log_config=None,
                log_level="warning",
                access_log=False,
                proxy_headers=False,
                server_header=False,
                date_header=False,
                forwarded_allow_ips="",
                root_path="",
                limit_concurrency=32,
                backlog=64,
                timeout_keep_alive=5,
                timeout_graceful_shutdown=10,
                h11_max_incomplete_event_size=16384,
                ssl_keyfile=None,
                ssl_certfile=None,
                ssl_keyfile_password=None,
                ssl_ca_certs=None,
                headers=[],
                app_dir=None,
                factory=False,
            )
        except Exception:
            raise MarketplaceUvicornProviderError(
                "MARKETPLACE_UVICORN_PROVIDER_FAILED"
            ) from None


__all__ = [
    "CLICK_VERSION",
    "H11_VERSION",
    "MarketplaceUvicornProviderError",
    "UVICORN_DISTRIBUTION",
    "UVICORN_VERSION",
    "UvicornLoopbackServerProvider",
]
