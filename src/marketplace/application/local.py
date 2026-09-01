"""Transport-neutral application facade over the local Marketplace runtime."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ..runtime.contracts import StoreDisposition
from ..runtime.node import IngestOutcome


class MarketplaceApplicationError(RuntimeError):
    """Stable application-boundary failure without external side effects."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ApplicationNode(Protocol):
    def ingest(self, record: Any) -> Any: ...

    def get(self, record_id: str) -> Any | None: ...


class ApplicationDiscovery(Protocol):
    def discover(
        self,
        query: Mapping[str, Any],
        *,
        source: str,
        completeness: str,
        freshness: str,
        max_records: int,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class PublishedRecord:
    record_id: str
    disposition: StoreDisposition


@dataclass(frozen=True, slots=True)
class LocalSearchResult:
    source: str
    completeness: str
    freshness: str
    global_completeness: str
    absence_is_negative_evidence: bool
    ordering: str
    record_ids: tuple[str, ...]
    records: tuple[Any, ...]


class LocalMarketplaceApplication:
    """Small local application surface for publishing and browsing evidence."""

    def __init__(
        self,
        *,
        node: ApplicationNode,
        discovery: ApplicationDiscovery,
        source: str,
    ) -> None:
        if type(source) is not str or not source:
            raise ValueError("source MUST be non-empty text")
        self._node = node
        self._discovery = discovery
        self._source = source

    @property
    def source(self) -> str:
        return self._source

    def publish(self, record: Any) -> PublishedRecord:
        outcome = self._node.ingest(record)
        if type(outcome) is not IngestOutcome:
            raise MarketplaceApplicationError(
                "PUBLISH_RESULT_INVALID",
                "runtime publish result did not have the exact reviewed outcome type",
            )
        record_id = outcome.record_id
        disposition = outcome.disposition
        if type(record_id) is not str or not record_id:
            raise MarketplaceApplicationError(
                "PUBLISH_RESULT_INVALID",
                "runtime publish result did not contain an exact Record Identity",
            )
        if type(disposition) is not StoreDisposition:
            raise MarketplaceApplicationError(
                "PUBLISH_RESULT_INVALID",
                "runtime publish result contained an invalid disposition",
            )
        return PublishedRecord(record_id=record_id, disposition=disposition)

    def get(self, record_id: str) -> Any | None:
        if type(record_id) is not str or not record_id:
            raise ValueError("record_id MUST be non-empty text")
        return self._node.get(record_id)

    def search(
        self,
        query: Mapping[str, Any],
        *,
        completeness: str = "PARTIAL_SOURCE",
        freshness: str = "FRESH",
        max_records: int = 256,
    ) -> LocalSearchResult:
        result = self._discovery.discover(
            query,
            source=self._source,
            completeness=completeness,
            freshness=freshness,
            max_records=max_records,
        )
        return self._materialize_search_result(result)

    def _materialize_search_result(self, result: Any) -> LocalSearchResult:
        if type(result) is not dict:
            self._invalid_search_result()
        source = result.get("source")
        completeness = result.get("completeness")
        freshness = result.get("freshness")
        global_completeness = result.get("global_completeness")
        absence_is_negative_evidence = result.get("absence_is_negative_evidence")
        ordering = result.get("ordering")
        refs = result.get("result_refs")
        result_count = result.get("result_count")
        text_fields = (
            (source, "source"),
            (completeness, "completeness"),
            (freshness, "freshness"),
            (global_completeness, "global_completeness"),
            (ordering, "ordering"),
        )
        if any(type(value) is not str or not value for value, _ in text_fields):
            self._invalid_search_result()
        if source != self._source:
            self._invalid_search_result()
        if type(absence_is_negative_evidence) is not bool:
            self._invalid_search_result()
        if type(refs) not in (list, tuple):
            self._invalid_search_result()
        record_ids = tuple(refs)
        if any(type(record_id) is not str or not record_id for record_id in record_ids):
            self._invalid_search_result()
        if type(result_count) is not int or result_count != len(record_ids):
            self._invalid_search_result()

        records: list[Any] = []
        for record_id in record_ids:
            record = self._node.get(record_id)
            if record is None:
                raise MarketplaceApplicationError(
                    "LOCAL_SEARCH_RESULT_MISSING_RECORD",
                    "local discovery returned a Record Identity that is not locally resolvable",
                )
            records.append(record)

        return LocalSearchResult(
            source=source,
            completeness=completeness,
            freshness=freshness,
            global_completeness=global_completeness,
            absence_is_negative_evidence=absence_is_negative_evidence,
            ordering=ordering,
            record_ids=record_ids,
            records=tuple(records),
        )

    @staticmethod
    def _invalid_search_result() -> None:
        raise MarketplaceApplicationError(
            "LOCAL_SEARCH_RESULT_INVALID",
            "local discovery returned an invalid application result shape",
        )
