"""Transport-neutral contracts for the Marketplace reference runtime."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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


class ExactRecordSource(Protocol):
    """Resolve one exact locally available record identity, with no fallback."""

    def get(self, record_id: str) -> Any | None: ...


class BoundedRecordSource(Protocol):
    """Read a finite local evidence snapshot without implying global completeness."""

    def snapshot(self, limit: int) -> tuple[Any, ...]: ...


class DiscoveryEvaluator(Protocol):
    """Evaluate an existing Marketplace discovery method over supplied records."""

    def __call__(
        self,
        records: Iterable[Any],
        query: Mapping[str, Any],
        *,
        source: str,
        completeness: str,
        freshness: str,
        max_records: int,
    ) -> Mapping[str, Any]: ...


class MatchEvaluator(Protocol):
    """Evaluate an existing Marketplace matching method over two supplied records."""

    def __call__(
        self,
        left: Any,
        right: Any,
        *,
        method: str,
        base_status: str,
        observations: Sequence[Mapping[str, Any]],
        evidence_completeness: str,
        understood_critical: Iterable[str],
    ) -> Mapping[str, Any]: ...
