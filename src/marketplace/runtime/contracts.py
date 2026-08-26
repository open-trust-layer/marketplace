"""Transport-neutral contracts for the Marketplace reference runtime."""
from __future__ import annotations

from enum import Enum
from typing import Any, Protocol


class StoreDisposition(str, Enum):
    """Outcome of placing immutable evidence into a runtime repository."""

    STORED = "STORED"
    DUPLICATE = "DUPLICATE"


class RecordValidator(Protocol):
    """Validate Marketplace semantics without performing external side effects."""

    def __call__(self, record: Any) -> None: ...


class RecordIdentityProvider(Protocol):
    """Derive canonical OLP Record Identity text for a validated record."""

    def __call__(self, record: Any) -> str: ...


class RecordRepository(Protocol):
    """Minimal repository capability required by the in-process node."""

    retention_class: str

    @property
    def retention_seconds(self) -> float: ...

    def put(self, record_id: str, record: Any) -> StoreDisposition: ...

    def get(self, record_id: str) -> Any | None: ...

    def close(self) -> None: ...
