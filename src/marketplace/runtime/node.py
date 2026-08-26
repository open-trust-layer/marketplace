"""In-process Marketplace node orchestration with explicit dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import (
    RecordIdentityProvider,
    RecordRepository,
    RecordValidator,
    StoreDisposition,
)


class RuntimeNodeError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InvalidIdentityProviderResult(RuntimeNodeError):
    def __init__(self) -> None:
        super().__init__(
            "INVALID_IDENTITY_PROVIDER_RESULT",
            "OLP identity provider MUST return non-empty canonical identity text",
        )


@dataclass(frozen=True)
class IngestOutcome:
    record_id: str
    disposition: StoreDisposition


class MarketplaceNode:
    """Small transport-neutral composition root for validated Marketplace evidence.

    The node intentionally has no network, filesystem, database, credential,
    deployment, settlement, fulfillment, or protected-action executor.
    """

    def __init__(
        self,
        *,
        validate_record: RecordValidator,
        record_identity_text: RecordIdentityProvider,
        repository: RecordRepository,
    ) -> None:
        self._validate_record = validate_record
        self._record_identity_text = record_identity_text
        self._repository = repository

    @property
    def retention_class(self) -> str:
        return self._repository.retention_class

    @property
    def retention_seconds(self) -> float:
        return self._repository.retention_seconds

    def ingest(self, record: Any) -> IngestOutcome:
        # Validation MUST precede identity derivation and repository mutation.
        self._validate_record(record)
        record_id = self._record_identity_text(record)
        if not isinstance(record_id, str) or not record_id:
            raise InvalidIdentityProviderResult()
        disposition = self._repository.put(record_id, record)
        return IngestOutcome(record_id=record_id, disposition=disposition)

    def get(self, record_id: str) -> Any | None:
        return self._repository.get(record_id)

    def close(self) -> None:
        self._repository.close()
