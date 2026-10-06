"""Metadata-only Moon heartbeat for explicitly authorized local Marketplace servers."""
from __future__ import annotations

import json
import os
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol
from uuid import uuid4

MOON_VERSION = "0.1"
SERVICE_ID = "hello-world-marketplace"
DEFAULT_VERSION = "0.0.1.dev0"
DEFAULT_ENVIRONMENT = "development"
DEFAULT_INTERVAL_SECONDS = 15.0
MAX_HEARTBEAT_BYTES = 4096


class MarketplaceServerProvider(Protocol):
    def run(self, *, application: object, host: str, port: int) -> None:
        """Run one foreground server."""


class MarketplaceMoonHeartbeatLease:
    """Refresh liveness only after the admitted ASGI application receives traffic."""

    def __init__(
        self,
        *,
        state_root: Path,
        version: str = DEFAULT_VERSION,
        environment: str = DEFAULT_ENVIRONMENT,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        process_id: int | None = None,
    ) -> None:
        if not state_root.is_absolute():
            raise ValueError("Moon heartbeat state root must be absolute")
        if not 1 <= interval_seconds <= 300:
            raise ValueError("Moon heartbeat interval must be between 1 and 300 seconds")
        self._state_root = state_root
        self._version = _bounded_text(version, "version")
        self._environment = _bounded_text(environment, "environment")
        self._interval_seconds = interval_seconds
        self._process_id = os.getpid() if process_id is None else process_id
        if self._process_id <= 0:
            raise ValueError("process_id must be positive")
        self._instance_id = str(uuid4())
        self._started_at: datetime | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._closed = False

    @property
    def path(self) -> Path:
        return (
            self._state_root
            / "heartbeats"
            / SERVICE_ID
            / f"{self._instance_id}.json"
        )

    def ensure_started(self) -> None:
        with self._lock:
            if self._closed:
                return
            if self._thread is not None:
                return
            self._started_at = datetime.now(UTC)
            self._try_write()
            thread = threading.Thread(
                target=self._pulse,
                name="marketplace-moon-heartbeat",
                daemon=True,
            )
            self._thread = thread
            thread.start()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            thread = self._thread
            self._stop.set()
        if thread is not None:
            thread.join(timeout=1.0)
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass

    def _pulse(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            self._try_write()

    def _record(self) -> dict[str, object]:
        if self._started_at is None:
            raise RuntimeError("Moon heartbeat has not started")
        return {
            "moon_version": MOON_VERSION,
            "service_id": SERVICE_ID,
            "version": self._version,
            "environment": self._environment,
            "instance_id": self._instance_id,
            "process_id": self._process_id,
            "started_at": self._started_at.isoformat(),
            "observed_at": datetime.now(UTC).isoformat(),
        }

    def _try_write(self) -> None:
        try:
            _write_heartbeat(self.path, self._record())
        except OSError:
            return


class _HeartbeatAsgiApplication:
    def __init__(self, application: object, lease: MarketplaceMoonHeartbeatLease) -> None:
        if not callable(application):
            raise TypeError("application MUST be callable")
        self._application = application
        self._lease = lease

    async def __call__(self, scope, receive, send) -> None:
        if isinstance(scope, Mapping) and scope.get("type") == "http":
            self._lease.ensure_started()
        await self._application(scope, receive, send)


class MarketplaceMoonHeartbeatServerProvider:
    """Wrap a foreground provider without widening its socket or execution authority."""

    def __init__(
        self,
        delegate: MarketplaceServerProvider,
        lease: MarketplaceMoonHeartbeatLease,
    ) -> None:
        self._delegate = delegate
        self._lease = lease

    def run(self, *, application: object, host: str, port: int) -> None:
        wrapped = _HeartbeatAsgiApplication(application, self._lease)
        try:
            self._delegate.run(application=wrapped, host=host, port=port)
        finally:
            self._lease.close()


def marketplace_moon_heartbeat_from_env(
    env: Mapping[str, str] | None = None,
) -> MarketplaceMoonHeartbeatLease | None:
    values = os.environ if env is None else env
    enabled = values.get("MARKETPLACE_MOON_HEARTBEAT_ENABLED", "").strip()
    if enabled in ("", "0"):
        return None
    if enabled != "1":
        raise ValueError("MARKETPLACE_MOON_HEARTBEAT_ENABLED must be 0 or 1")

    configured_root = values.get("MARKETPLACE_MOON_STATE_ROOT", "").strip()
    state_root = (
        Path(configured_root)
        if configured_root
        else Path.home() / ".moon" / "state"
    )
    if not state_root.is_absolute():
        raise ValueError("MARKETPLACE_MOON_STATE_ROOT must be absolute")

    return MarketplaceMoonHeartbeatLease(
        state_root=state_root,
        version=values.get("MARKETPLACE_RELEASE_SHA", "").strip() or DEFAULT_VERSION,
        environment=(
            values.get("MARKETPLACE_MOON_ENVIRONMENT", "").strip()
            or DEFAULT_ENVIRONMENT
        ),
    )


def wrap_marketplace_server_provider_from_env(
    provider: MarketplaceServerProvider,
    env: Mapping[str, str] | None = None,
) -> MarketplaceServerProvider:
    lease = marketplace_moon_heartbeat_from_env(env)
    if lease is None:
        return provider
    return MarketplaceMoonHeartbeatServerProvider(provider, lease)


def _bounded_text(value: str, field: str) -> str:
    text = value.strip()
    if not text or len(text) > 64:
        raise ValueError(f"Moon heartbeat {field} must contain 1-64 characters")
    return text


def _write_heartbeat(path: Path, record: dict[str, object]) -> None:
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_HEARTBEAT_BYTES:
        raise ValueError("Moon heartbeat exceeds size bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_name = handle.name
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


__all__ = [
    "MarketplaceMoonHeartbeatLease",
    "MarketplaceMoonHeartbeatServerProvider",
    "marketplace_moon_heartbeat_from_env",
    "wrap_marketplace_server_provider_from_env",
]
