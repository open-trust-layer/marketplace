"""Inert ASGI composition for the authenticated Agreement-assent HTTP overlay."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_assent_http_composition import (
    MarketplaceAgreementAssentHttpComposition,
)
from .auth_http_composition import MarketplaceAuthenticatedHttpComposition
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter


PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_ASSENT_ASGI_COMPOSITION_V1"


class MarketplaceAgreementAssentAsgiCompositionError(ValueError):
    """Stable non-reflective failure for inert Agreement-assent ASGI composition."""

    def __init__(self) -> None:
        super().__init__("Agreement assent ASGI composition failed")


def _fail() -> None:
    raise MarketplaceAgreementAssentAsgiCompositionError() from None


def _bound_owner(value: object) -> object | None:
    try:
        if not callable(value):
            return None
        return getattr(value, "__self__", None)
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAgreementAssentAsgiComposition:
    """One authenticated ASGI adapter selecting the exact Agreement HTTP overlay."""

    authenticated_http: MarketplaceAuthenticatedHttpComposition
    agreement_http: MarketplaceAgreementAssentHttpComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        if type(self.authenticated_http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if type(self.agreement_http) is not MarketplaceAgreementAssentHttpComposition:
            _fail()
        if type(self.runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
            _fail()
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if self.agreement_http.authenticated_http is not self.authenticated_http:
            _fail()
        if self.asgi._site is not self.authenticated_http.application.site:
            _fail()
        if self.asgi._marketplace_http is not self.agreement_http.assent_http:
            _fail()
        if self.asgi._auth_http is not self.authenticated_http.session_http:
            _fail()
        if (
            _bound_owner(self.authenticated_http.session_http._challenge_bytes)
            is not self.runtime_inputs.material_source
        ):
            _fail()
        if (
            _bound_owner(self.authenticated_http.session_http._session_token_bytes)
            is not self.runtime_inputs.material_source
        ):
            _fail()
        if _bound_owner(self.asgi._now) is not self.runtime_inputs.clock:
            _fail()


def compose_marketplace_agreement_assent_asgi(
    *,
    authenticated_http: MarketplaceAuthenticatedHttpComposition,
    agreement_http: MarketplaceAgreementAssentHttpComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> MarketplaceAgreementAssentAsgiComposition:
    """Compose the Agreement HTTP overlay into authenticated ASGI without activation."""

    if type(authenticated_http) is not MarketplaceAuthenticatedHttpComposition:
        _fail()
    if type(agreement_http) is not MarketplaceAgreementAssentHttpComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()

    try:
        if agreement_http.authenticated_http is not authenticated_http:
            _fail()
        challenge_bytes = getattr(authenticated_http.session_http, "_challenge_bytes", None)
        session_token_bytes = getattr(
            authenticated_http.session_http,
            "_session_token_bytes",
            None,
        )
        if _bound_owner(challenge_bytes) is not runtime_inputs.material_source:
            _fail()
        if _bound_owner(session_token_bytes) is not runtime_inputs.material_source:
            _fail()

        asgi = MarketplaceSessionEstablishmentAsgiHttpAdapter(
            site=authenticated_http.application.site,
            marketplace_http=agreement_http.assent_http,
            auth_http=authenticated_http.session_http,
            now=runtime_inputs.clock.now,
        )
        return MarketplaceAgreementAssentAsgiComposition(
            authenticated_http=authenticated_http,
            agreement_http=agreement_http,
            runtime_inputs=runtime_inputs,
            asgi=asgi,
        )
    except MarketplaceAgreementAssentAsgiCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAgreementAssentAsgiComposition",
    "MarketplaceAgreementAssentAsgiCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_agreement_assent_asgi",
]
