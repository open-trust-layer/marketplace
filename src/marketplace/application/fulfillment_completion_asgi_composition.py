"""Inert ASGI composition for authenticated fulfillment completion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_http_composition import MarketplaceAuthenticatedHttpComposition
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .fulfillment_completion_http_composition import (
    MarketplaceFulfillmentCompletionHttpComposition,
)

PROFILE_NAME: Final = "MARKETPLACE_FULFILLMENT_COMPLETION_ASGI_COMPOSITION_V1"
_ERROR_MESSAGE: Final = "Fulfillment completion ASGI composition failed"


class MarketplaceFulfillmentCompletionAsgiCompositionError(ValueError):
    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceFulfillmentCompletionAsgiCompositionError() from None


def _owner(value: object) -> object | None:
    if not callable(value):
        return None
    return getattr(value, "__self__", None)


def _authenticated_graph(
    value: MarketplaceFulfillmentCompletionHttpComposition,
) -> MarketplaceAuthenticatedHttpComposition:
    return (
        value.agreement_publication_http
        .agreement_assent_http
        .authenticated_http
    )


@dataclass(frozen=True, slots=True)
class MarketplaceFulfillmentCompletionAsgiComposition:
    authenticated_http: MarketplaceAuthenticatedHttpComposition
    fulfillment_http: MarketplaceFulfillmentCompletionHttpComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        if type(self.authenticated_http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if type(self.fulfillment_http) is not MarketplaceFulfillmentCompletionHttpComposition:
            _fail()
        if type(self.runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
            _fail()
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if _authenticated_graph(self.fulfillment_http) is not self.authenticated_http:
            _fail()
        if self.asgi._site is not self.authenticated_http.application.site:
            _fail()
        if self.asgi._marketplace_http is not self.fulfillment_http.fulfillment_http:
            _fail()
        if self.asgi._auth_http is not self.authenticated_http.session_http:
            _fail()
        if _owner(self.authenticated_http.session_http._challenge_bytes) is not self.runtime_inputs.material_source:
            _fail()
        if _owner(self.authenticated_http.session_http._session_token_bytes) is not self.runtime_inputs.material_source:
            _fail()
        if _owner(self.asgi._now) is not self.runtime_inputs.clock:
            _fail()


def compose_marketplace_fulfillment_completion_asgi(
    *,
    authenticated_http: MarketplaceAuthenticatedHttpComposition,
    fulfillment_http: MarketplaceFulfillmentCompletionHttpComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> MarketplaceFulfillmentCompletionAsgiComposition:
    if type(authenticated_http) is not MarketplaceAuthenticatedHttpComposition:
        _fail()
    if type(fulfillment_http) is not MarketplaceFulfillmentCompletionHttpComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()
    if _authenticated_graph(fulfillment_http) is not authenticated_http:
        _fail()
    if _owner(authenticated_http.session_http._challenge_bytes) is not runtime_inputs.material_source:
        _fail()
    if _owner(authenticated_http.session_http._session_token_bytes) is not runtime_inputs.material_source:
        _fail()

    asgi = MarketplaceSessionEstablishmentAsgiHttpAdapter(
        site=authenticated_http.application.site,
        marketplace_http=fulfillment_http.fulfillment_http,
        auth_http=authenticated_http.session_http,
        now=runtime_inputs.clock.now,
    )
    return MarketplaceFulfillmentCompletionAsgiComposition(
        authenticated_http=authenticated_http,
        fulfillment_http=fulfillment_http,
        runtime_inputs=runtime_inputs,
        asgi=asgi,
    )


__all__ = [
    "MarketplaceFulfillmentCompletionAsgiComposition",
    "MarketplaceFulfillmentCompletionAsgiCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_fulfillment_completion_asgi",
]
