"""Inert startup overlay for authenticated Agreement-assent HTTP/ASGI composition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_assent_asgi_composition import (
    MarketplaceAgreementAssentAsgiComposition,
    compose_marketplace_agreement_assent_asgi,
)
from .agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from .agreement_assent_http import SignatureCarrierDecoder, SigningInputCarrierEncoder
from .agreement_assent_http_composition import (
    MarketplaceAgreementAssentHttpComposition,
    compose_marketplace_agreement_assent_http,
)
from .agreement_assent_workflow import MarketplaceAgreementAssentWorkflowService
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_startup_composition import MarketplaceAuthenticatedStartupComposition


PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_ASSENT_STARTUP_COMPOSITION_V1"


class MarketplaceAgreementAssentStartupCompositionError(ValueError):
    """Stable non-reflective failure for inert Agreement-assent startup composition."""

    def __init__(self) -> None:
        super().__init__("Agreement assent startup composition failed")


def _fail() -> None:
    raise MarketplaceAgreementAssentStartupCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceAgreementAssentStartupComposition:
    """One Agreement HTTP/ASGI overlay bound to an existing authenticated startup."""

    authenticated_startup: MarketplaceAuthenticatedStartupComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    agreement_http: MarketplaceAgreementAssentHttpComposition
    agreement_asgi: MarketplaceAgreementAssentAsgiComposition

    def __post_init__(self) -> None:
        if type(self.authenticated_startup) is not MarketplaceAuthenticatedStartupComposition:
            _fail()
        if type(self.runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
            _fail()
        if type(self.agreement_http) is not MarketplaceAgreementAssentHttpComposition:
            _fail()
        if type(self.agreement_asgi) is not MarketplaceAgreementAssentAsgiComposition:
            _fail()
        if self.agreement_http.authenticated_http is not self.authenticated_startup.http:
            _fail()
        if self.agreement_asgi.authenticated_http is not self.authenticated_startup.http:
            _fail()
        if self.agreement_asgi.agreement_http is not self.agreement_http:
            _fail()
        if self.agreement_asgi.runtime_inputs is not self.runtime_inputs:
            _fail()
        if self.agreement_asgi.asgi._marketplace_http is not self.agreement_http.assent_http:
            _fail()


def compose_marketplace_agreement_assent_startup(
    *,
    authenticated_startup: MarketplaceAuthenticatedStartupComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
    candidate_resolution: MarketplaceAgreementAssentCandidateResolutionService,
    workflow: MarketplaceAgreementAssentWorkflowService,
    encode_signing_input: SigningInputCarrierEncoder,
    decode_signature: SignatureCarrierDecoder,
) -> MarketplaceAgreementAssentStartupComposition:
    """Compose Agreement HTTP/ASGI over one existing authenticated startup, inertly."""

    if type(authenticated_startup) is not MarketplaceAuthenticatedStartupComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
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
        agreement_http = compose_marketplace_agreement_assent_http(
            authenticated_http=authenticated_startup.http,
            candidate_resolution=candidate_resolution,
            workflow=workflow,
            encode_signing_input=encode_signing_input,
            decode_signature=decode_signature,
        )
        agreement_asgi = compose_marketplace_agreement_assent_asgi(
            authenticated_http=authenticated_startup.http,
            agreement_http=agreement_http,
            runtime_inputs=runtime_inputs,
        )
        return MarketplaceAgreementAssentStartupComposition(
            authenticated_startup=authenticated_startup,
            runtime_inputs=runtime_inputs,
            agreement_http=agreement_http,
            agreement_asgi=agreement_asgi,
        )
    except MarketplaceAgreementAssentStartupCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAgreementAssentStartupComposition",
    "MarketplaceAgreementAssentStartupCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_agreement_assent_startup",
]
