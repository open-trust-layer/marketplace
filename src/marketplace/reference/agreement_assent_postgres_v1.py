"""Inert PostgreSQL store selection for the reference Agreement-assent launch."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from ..application.postgres_agreement_assent import (
    PostgresAgreementAssentCoordinationStore,
)
from ..application.postgres_state import Clock, ConnectionFactory
from .agreement_assent_launch_v1 import (
    MarketplaceReferenceAgreementAssentLaunch,
    build_reference_agreement_assent_launch,
)


PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_POSTGRES_V1"


class MarketplaceReferenceAgreementAssentPostgresError(ValueError):
    """Stable fail-closed PostgreSQL Agreement composition error."""

    def __init__(self) -> None:
        super().__init__("reference Agreement assent PostgreSQL composition failed")


def _fail() -> None:
    raise MarketplaceReferenceAgreementAssentPostgresError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAgreementAssentPostgres:
    """One inert PostgreSQL store bound to one reference Agreement launch."""

    store: PostgresAgreementAssentCoordinationStore
    launch: MarketplaceReferenceAgreementAssentLaunch

    def __post_init__(self) -> None:
        if type(self.store) is not PostgresAgreementAssentCoordinationStore:
            _fail()
        if type(self.launch) is not MarketplaceReferenceAgreementAssentLaunch:
            _fail()
        if self.launch.services.coordination._store is not self.store:
            _fail()
        if self.launch.services.coordination._initialized is not False:
            _fail()


def build_reference_agreement_assent_postgres(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    connection_factory: ConnectionFactory,
    clock: Clock,
) -> MarketplaceReferenceAgreementAssentPostgres:
    """Select exact PostgreSQL coordination storage without initializing it."""

    if type(authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
        _fail()
    if not callable(connection_factory) or not callable(clock):
        _fail()

    try:
        store = PostgresAgreementAssentCoordinationStore(
            connection_factory=connection_factory,
            clock=clock,
        )
        launch = build_reference_agreement_assent_launch(
            authenticated_plan=authenticated_plan,
            coordination_store=store,
        )
        return MarketplaceReferenceAgreementAssentPostgres(
            store=store,
            launch=launch,
        )
    except MarketplaceReferenceAgreementAssentPostgresError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAgreementAssentPostgres",
    "MarketplaceReferenceAgreementAssentPostgresError",
    "PROFILE_NAME",
    "build_reference_agreement_assent_postgres",
]
