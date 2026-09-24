"""Inert composition for the authenticated Agreement-assent HTTP seam."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from .agreement_assent_http import (
    MarketplaceAuthenticatedAgreementAssentHttpAdapter,
    SignatureCarrierDecoder,
    SigningInputCarrierEncoder,
)
from .agreement_assent_workflow import (
    MarketplaceAgreementAssentWorkflowService,
)
from .auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from .auth_http_composition import MarketplaceAuthenticatedHttpComposition
from .auth_static_composition import MarketplaceStaticAuthenticationComposition


PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_ASSENT_HTTP_COMPOSITION_V1"


class MarketplaceAgreementAssentHttpCompositionError(ValueError):
    """Stable non-reflective failure for inert Agreement-assent composition."""

    def __init__(self) -> None:
        super().__init__("Agreement assent HTTP composition failed")


def _fail() -> None:
    raise MarketplaceAgreementAssentHttpCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceAgreementAssentHttpComposition:
    """One immutable Agreement-assent adapter bound to the existing auth graph."""

    authenticated_http: MarketplaceAuthenticatedHttpComposition
    candidate_resolution: MarketplaceAgreementAssentCandidateResolutionService
    workflow: MarketplaceAgreementAssentWorkflowService
    assent_http: MarketplaceAuthenticatedAgreementAssentHttpAdapter

    def __post_init__(self) -> None:
        if type(self.authenticated_http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if (
            type(self.candidate_resolution)
            is not MarketplaceAgreementAssentCandidateResolutionService
        ):
            _fail()
        if type(self.workflow) is not MarketplaceAgreementAssentWorkflowService:
            _fail()
        if type(self.assent_http) is not MarketplaceAuthenticatedAgreementAssentHttpAdapter:
            _fail()
        if self.assent_http._base is not self.authenticated_http.application_http:
            _fail()
        if (
            self.assent_http._auth
            is not self.authenticated_http.authentication.auth_service
        ):
            _fail()
        if self.assent_http._candidate_resolution is not self.candidate_resolution:
            _fail()
        if self.assent_http._workflow is not self.workflow:
            _fail()


def compose_marketplace_agreement_assent_http(
    *,
    authenticated_http: MarketplaceAuthenticatedHttpComposition,
    candidate_resolution: MarketplaceAgreementAssentCandidateResolutionService,
    workflow: MarketplaceAgreementAssentWorkflowService,
    encode_signing_input: SigningInputCarrierEncoder,
    decode_signature: SignatureCarrierDecoder,
) -> MarketplaceAgreementAssentHttpComposition:
    """Compose an inert assent HTTP adapter over one existing auth object graph."""
    if type(authenticated_http) is not MarketplaceAuthenticatedHttpComposition:
        _fail()
    if (
        type(authenticated_http.authentication)
        is not MarketplaceStaticAuthenticationComposition
    ):
        _fail()
    if (
        type(authenticated_http.application_http)
        is not MarketplaceAuthenticatedApplicationHttpAdapter
    ):
        _fail()
    if (
        type(candidate_resolution)
        is not MarketplaceAgreementAssentCandidateResolutionService
    ):
        _fail()
    if type(workflow) is not MarketplaceAgreementAssentWorkflowService:
        _fail()
    if not callable(encode_signing_input) or not callable(decode_signature):
        _fail()

    try:
        assent_http = MarketplaceAuthenticatedAgreementAssentHttpAdapter(
            base=authenticated_http.application_http,
            auth=authenticated_http.authentication.auth_service,
            candidate_resolution=candidate_resolution,
            workflow=workflow,
            encode_signing_input=encode_signing_input,
            decode_signature=decode_signature,
        )
        return MarketplaceAgreementAssentHttpComposition(
            authenticated_http=authenticated_http,
            candidate_resolution=candidate_resolution,
            workflow=workflow,
            assent_http=assent_http,
        )
    except MarketplaceAgreementAssentHttpCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAgreementAssentHttpComposition",
    "MarketplaceAgreementAssentHttpCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_agreement_assent_http",
]
