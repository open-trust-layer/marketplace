"""Inert reference composition of the reviewed fulfillment-completion launch graph."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from olp.encoding.record_identity import record_identity_text

from ..application.agreement_publication import (
    MarketplaceAgreementPublicationPreflightService,
)
from ..application.agreement_publication_write import (
    MarketplaceAgreementPublicationService,
)
from ..application.fulfillment_completion_launch import (
    MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
    build_marketplace_fulfillment_completion_loopback_launch_plan,
)
from ..application.fulfillment_completion_publication import (
    MarketplaceFulfillmentCompletionPublicationService,
)
from ..application.fulfillment_completion_startup_composition import (
    MarketplaceFulfillmentCompletionStartupComposition,
    compose_marketplace_fulfillment_completion_startup,
)
from .agreement_assent_postgres_v1 import (
    MarketplaceReferenceAgreementAssentPostgres,
)
from .agreement_candidate_v1 import agreement_candidate_record_id
from .fulfillment_completion_evidence_v1 import (
    build_claimed_complete_performance_event,
    build_commitment_acceptance_event,
    build_commitment_completion_event,
    fulfillment_event_target,
)


PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_LAUNCH_V1"
_ERROR_MESSAGE: Final = "reference fulfillment completion launch composition failed"


class MarketplaceReferenceFulfillmentCompletionLaunchError(ValueError):
    """Stable fail-closed M17.7G reference-composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceFulfillmentCompletionLaunchError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceFulfillmentCompletionLaunch:
    """One coherent inert fulfillment launch over the reference Agreement graph."""

    agreement_graph: MarketplaceReferenceAgreementAssentPostgres
    preflight: MarketplaceAgreementPublicationPreflightService
    agreement_publication: MarketplaceAgreementPublicationService
    fulfillment_publication: MarketplaceFulfillmentCompletionPublicationService
    startup: MarketplaceFulfillmentCompletionStartupComposition
    plan: MarketplaceFulfillmentCompletionLoopbackLaunchPlan

    def __post_init__(self) -> None:
        if type(self.agreement_graph) is not MarketplaceReferenceAgreementAssentPostgres:
            _fail()
        if type(self.preflight) is not MarketplaceAgreementPublicationPreflightService:
            _fail()
        if type(self.agreement_publication) is not MarketplaceAgreementPublicationService:
            _fail()
        if (
            type(self.fulfillment_publication)
            is not MarketplaceFulfillmentCompletionPublicationService
        ):
            _fail()
        if (
            type(self.startup)
            is not MarketplaceFulfillmentCompletionStartupComposition
        ):
            _fail()
        if (
            type(self.plan)
            is not MarketplaceFulfillmentCompletionLoopbackLaunchPlan
        ):
            _fail()

        application = self.agreement_graph.launch.services.application
        agreement_startup = self.agreement_graph.launch.startup
        if self.agreement_publication._state is not application.state:
            _fail()
        if self.fulfillment_publication._state is not application.state:
            _fail()
        if self.startup.agreement_startup is not agreement_startup:
            _fail()
        if self.startup.runtime_inputs is not agreement_startup.runtime_inputs:
            _fail()
        if self.startup.agreement_publication_http.preflight is not self.preflight:
            _fail()
        if (
            self.startup.agreement_publication_http.publication
            is not self.agreement_publication
        ):
            _fail()
        if (
            self.startup.fulfillment_http.fulfillment_publication
            is not self.fulfillment_publication
        ):
            _fail()
        if self.plan.startup is not self.startup:
            _fail()
        if self.plan.host != self.agreement_graph.launch.plan.host:
            _fail()
        if self.plan.port != self.agreement_graph.launch.plan.port:
            _fail()
        if self.plan.asgi is not self.startup.fulfillment_asgi.asgi:
            _fail()


def build_reference_fulfillment_completion_launch(
    *,
    agreement_graph: MarketplaceReferenceAgreementAssentPostgres,
) -> MarketplaceReferenceFulfillmentCompletionLaunch:
    """Compose B-F from one exact Agreement PostgreSQL graph without execution."""

    if type(agreement_graph) is not MarketplaceReferenceAgreementAssentPostgres:
        _fail()

    try:
        application = agreement_graph.launch.services.application
        agreement_startup = agreement_graph.launch.startup
        runtime_inputs = agreement_startup.runtime_inputs

        preflight = MarketplaceAgreementPublicationPreflightService(
            record_identity=agreement_candidate_record_id,
        )
        agreement_publication = MarketplaceAgreementPublicationService(
            state=application.state,
            record_identity=agreement_candidate_record_id,
        )
        fulfillment_publication = MarketplaceFulfillmentCompletionPublicationService(
            state=application.state,
            build_claimed_complete_performance=build_claimed_complete_performance_event,
            build_commitment_acceptance=build_commitment_acceptance_event,
            build_commitment_completion=build_commitment_completion_event,
            event_target=fulfillment_event_target,
            record_identity=record_identity_text,
        )
        startup = compose_marketplace_fulfillment_completion_startup(
            agreement_startup=agreement_startup,
            runtime_inputs=runtime_inputs,
            agreement_publication_preflight=preflight,
            agreement_publication=agreement_publication,
            fulfillment_publication=fulfillment_publication,
        )
        plan = build_marketplace_fulfillment_completion_loopback_launch_plan(
            host=agreement_graph.launch.plan.host,
            port=agreement_graph.launch.plan.port,
            startup=startup,
        )
        return MarketplaceReferenceFulfillmentCompletionLaunch(
            agreement_graph=agreement_graph,
            preflight=preflight,
            agreement_publication=agreement_publication,
            fulfillment_publication=fulfillment_publication,
            startup=startup,
            plan=plan,
        )
    except MarketplaceReferenceFulfillmentCompletionLaunchError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceFulfillmentCompletionLaunch",
    "MarketplaceReferenceFulfillmentCompletionLaunchError",
    "PROFILE_NAME",
    "build_reference_fulfillment_completion_launch",
]
