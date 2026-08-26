"""Composition helpers for the transport-neutral Marketplace reference runtime."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .contracts import (
    DiscoveryEvaluator,
    FederationEnvelopeMaker,
    FederationEnvelopeValidator,
    FederationRequestValidator,
    FederationResultValidator,
    MatchEvaluator,
    RecordIdentityProvider,
    RecordRepository,
    RecordValidator,
)
from .discovery import LocalDiscoveryService
from .federation import FederationOperationProfile, OfflineFederationService
from .matching import LocalMatchService
from .node import MarketplaceNode
from .repository import DEFAULT_MAX_ENTRIES, InMemoryEphemeralRecordRepository
from .retention import DEFAULT_EPHEMERAL_RETENTION_SECONDS, ExpiryScheduler


@dataclass(frozen=True)
class MarketplaceRuntime:
    """One local runtime whose services share one owned repository lifecycle.

    Closing this object performs process-local runtime cleanup only. It does not
    publish an OLP lifecycle event, retire a Marketplace record, or establish
    global deletion of any evidence.
    """

    repository: RecordRepository
    node: MarketplaceNode
    discovery: LocalDiscoveryService
    matching: LocalMatchService

    def close(self) -> None:
        self.repository.close()

    def __enter__(self) -> "MarketplaceRuntime":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.close()
        return False


def compose_runtime(
    *,
    validate_record: RecordValidator,
    record_identity_text: RecordIdentityProvider,
    evaluate_discovery: DiscoveryEvaluator,
    evaluate_match: MatchEvaluator,
    repository: RecordRepository,
) -> MarketplaceRuntime:
    """Assemble local runtime services around one explicitly supplied repository."""
    return MarketplaceRuntime(
        repository=repository,
        node=MarketplaceNode(
            validate_record=validate_record,
            record_identity_text=record_identity_text,
            repository=repository,
        ),
        discovery=LocalDiscoveryService(
            record_source=repository,
            evaluate_discovery=evaluate_discovery,
        ),
        matching=LocalMatchService(
            record_source=repository,
            evaluate_match=evaluate_match,
        ),
    )


def create_in_memory_runtime(
    *,
    validate_record: RecordValidator,
    record_identity_text: RecordIdentityProvider,
    evaluate_discovery: DiscoveryEvaluator,
    evaluate_match: MatchEvaluator,
    retention_seconds: float = DEFAULT_EPHEMERAL_RETENTION_SECONDS,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    scheduler: ExpiryScheduler | None = None,
) -> MarketplaceRuntime:
    """Create the bounded EPHEMERAL in-process reference composition.

    Semantic validation, Record Identity, discovery, and matching remain
    explicit required inputs. This factory selects only the already-defined
    process-local memory repository; it does not select a protocol truth method.
    """
    repository = InMemoryEphemeralRecordRepository(
        retention_seconds=retention_seconds,
        max_entries=max_entries,
        scheduler=scheduler,
    )
    return compose_runtime(
        validate_record=validate_record,
        record_identity_text=record_identity_text,
        evaluate_discovery=evaluate_discovery,
        evaluate_match=evaluate_match,
        repository=repository,
    )


def compose_offline_federation_service(
    runtime: MarketplaceRuntime,
    *,
    validate_record: RecordValidator,
    record_identity_text: RecordIdentityProvider,
    validate_exchange_request: FederationRequestValidator,
    make_transport_envelope: FederationEnvelopeMaker,
    validate_transport_envelope: FederationEnvelopeValidator,
    validate_exchange_result: FederationResultValidator,
    operation_profiles: Sequence[FederationOperationProfile],
) -> OfflineFederationService:
    """Attach offline M8 preparation/validation to an existing local runtime.

    This helper selects no concrete transport. It cannot resolve an endpoint or
    send a request; it only gives the offline federation service access to the
    same node/repository lifecycle already owned by ``runtime``.
    """
    if not isinstance(runtime, MarketplaceRuntime):
        raise TypeError("runtime MUST be a MarketplaceRuntime")
    return OfflineFederationService(
        node=runtime.node,
        validate_record=validate_record,
        record_identity_text=record_identity_text,
        validate_exchange_request=validate_exchange_request,
        make_transport_envelope=make_transport_envelope,
        validate_transport_envelope=validate_transport_envelope,
        validate_exchange_result=validate_exchange_result,
        operation_profiles=operation_profiles,
    )
