"""Read-only local discovery composition for the Marketplace reference runtime."""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import BoundedRecordSource, DiscoveryEvaluator


class RuntimeDiscoveryError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InvalidDiscoveryLimitError(RuntimeDiscoveryError):
    def __init__(self) -> None:
        super().__init__(
            "INVALID_DISCOVERY_LIMIT",
            "max_records MUST be a positive integer",
        )


class InvalidDiscoveryEvaluatorResult(RuntimeDiscoveryError):
    def __init__(self) -> None:
        super().__init__(
            "INVALID_DISCOVERY_EVALUATOR_RESULT",
            "discovery evaluator MUST return a mapping",
        )


@dataclass(frozen=True)
class LocalDiscoveryService:
    """Compose bounded local evidence with an existing discovery evaluator.

    The service deliberately owns no matching/discovery semantics. Query
    validation, source/completeness/freshness interpretation, identity handling,
    and result meaning remain the responsibility of the injected evaluator.
    """

    record_source: BoundedRecordSource
    evaluate_discovery: DiscoveryEvaluator

    def _records(self, max_records: int) -> Iterator[Any]:
        # Snapshot acquisition is intentionally lazy. The current M5 evaluator
        # validates query/source metadata before consuming the iterable, so an
        # invalid request does not refresh EPHEMERAL record retention merely by
        # constructing the runtime request.
        yield from self.record_source.snapshot(max_records)

    def discover(
        self,
        query: Mapping[str, Any],
        *,
        source: str,
        completeness: str,
        freshness: str,
        max_records: int,
    ) -> Mapping[str, Any]:
        if isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 1:
            raise InvalidDiscoveryLimitError()
        result = self.evaluate_discovery(
            self._records(max_records),
            query,
            source=source,
            completeness=completeness,
            freshness=freshness,
            max_records=max_records,
        )
        if not isinstance(result, Mapping):
            raise InvalidDiscoveryEvaluatorResult()
        return result
