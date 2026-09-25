"""Inert reference selection of Agreement-assent services into launch metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.agreement_assent_coordination import AgreementAssentCoordinationStore
from ..application.agreement_assent_launch import (
    MarketplaceAgreementAssentLoopbackLaunchPlan,
    build_marketplace_agreement_assent_loopback_launch_plan,
)
from ..application.agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
    compose_marketplace_agreement_assent_startup,
)
from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .agreement_assent_application_v1 import (
    MarketplaceReferenceAgreementAssentServices,
    build_reference_agreement_assent_services,
)
from .agreement_assent_http_v1 import (
    decode_agreement_assent_signature,
    encode_agreement_assent_signing_input,
)


PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_LAUNCH_V1"


class MarketplaceReferenceAgreementAssentLaunchError(ValueError):
    """Stable fail-closed reference Agreement launch composition error."""

    def __init__(self) -> None:
        super().__init__("reference Agreement assent launch composition failed")


def _fail() -> None:
    raise MarketplaceReferenceAgreementAssentLaunchError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAgreementAssentLaunch:
    """Coherent inert Agreement launch graph over one authenticated launch plan."""

    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan
    services: MarketplaceReferenceAgreementAssentServices
    startup: MarketplaceAgreementAssentStartupComposition
    plan: MarketplaceAgreementAssentLoopbackLaunchPlan

    def __post_init__(self) -> None:
        if type(self.authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
            _fail()
        if type(self.services) is not MarketplaceReferenceAgreementAssentServices:
            _fail()
        if type(self.startup) is not MarketplaceAgreementAssentStartupComposition:
            _fail()
        if type(self.plan) is not MarketplaceAgreementAssentLoopbackLaunchPlan:
            _fail()
        if self.services.authenticated_startup is not self.authenticated_plan.startup:
            _fail()
        if self.startup.authenticated_startup is not self.authenticated_plan.startup:
            _fail()
        if self.startup.agreement_http.candidate_resolution is not self.services.candidate_resolution:
            _fail()
        if self.startup.agreement_http.workflow is not self.services.workflow:
            _fail()
        if self.plan.startup is not self.startup:
            _fail()
        if self.plan.host != self.authenticated_plan.host:
            _fail()
        if self.plan.port != self.authenticated_plan.port:
            _fail()
        if self.plan.asgi is not self.startup.agreement_asgi.asgi:
            _fail()
        if self.services.coordination._initialized is not False:
            _fail()


def build_reference_agreement_assent_launch(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    coordination_store: AgreementAssentCoordinationStore,
) -> MarketplaceReferenceAgreementAssentLaunch:
    """Select exact reference Agreement services into inert startup/launch layers."""

    if type(authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
        _fail()

    try:
        authenticated_startup = authenticated_plan.startup
        application = authenticated_startup.http.application
        runtime_inputs = authenticated_startup.asgi.runtime_inputs
        services = build_reference_agreement_assent_services(
            application=application,
            authenticated_startup=authenticated_startup,
            coordination_store=coordination_store,
        )
        startup = compose_marketplace_agreement_assent_startup(
            authenticated_startup=authenticated_startup,
            runtime_inputs=runtime_inputs,
            candidate_resolution=services.candidate_resolution,
            workflow=services.workflow,
            encode_signing_input=encode_agreement_assent_signing_input,
            decode_signature=decode_agreement_assent_signature,
        )
        plan = build_marketplace_agreement_assent_loopback_launch_plan(
            host=authenticated_plan.host,
            port=authenticated_plan.port,
            startup=startup,
        )
        return MarketplaceReferenceAgreementAssentLaunch(
            authenticated_plan=authenticated_plan,
            services=services,
            startup=startup,
            plan=plan,
        )
    except MarketplaceReferenceAgreementAssentLaunchError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAgreementAssentLaunch",
    "MarketplaceReferenceAgreementAssentLaunchError",
    "PROFILE_NAME",
    "build_reference_agreement_assent_launch",
]
