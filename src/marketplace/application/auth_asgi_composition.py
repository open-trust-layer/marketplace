"""M17.5R static authenticated ASGI composition without runtime activation.

This module only proves identity coherence between the reviewed M17.5P HTTP
composition, M17.5Q runtime inputs, and the reviewed authentication ASGI seam.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_http_composition import MarketplaceAuthenticatedHttpComposition
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ASGI_COMPOSITION_V1"
_ERROR_MESSAGE: Final = "authenticated Marketplace ASGI composition failed"


class MarketplaceAuthenticatedAsgiCompositionError(ValueError):
    """Stable fail-closed composition error without authentication reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticatedAsgiCompositionError() from None


def _bound_owner(value: object) -> object | None:
    """Return a bound callable owner without invoking the callable."""

    try:
        if not callable(value):
            return None
        return getattr(value, "__self__", None)
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticatedAsgiComposition:
    """Immutable coherent references to reviewed authenticated ASGI inputs."""

    http: MarketplaceAuthenticatedHttpComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        if type(self.http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if type(self.runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
            _fail()
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if self.asgi._site is not self.http.application.site:
            _fail()
        if self.asgi._marketplace_http is not self.http.application_http:
            _fail()
        if self.asgi._auth_http is not self.http.session_http:
            _fail()
        if (
            _bound_owner(self.http.session_http._challenge_bytes)
            is not self.runtime_inputs.material_source
        ):
            _fail()
        if (
            _bound_owner(self.http.session_http._session_token_bytes)
            is not self.runtime_inputs.material_source
        ):
            _fail()
        if _bound_owner(self.asgi._now) is not self.runtime_inputs.clock:
            _fail()


def compose_marketplace_authenticated_asgi(
    *,
    http: MarketplaceAuthenticatedHttpComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> MarketplaceAuthenticatedAsgiComposition:
    """Compose reviewed authenticated ASGI objects without consuming them."""

    if type(http) is not MarketplaceAuthenticatedHttpComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()

    try:
        challenge_bytes = getattr(http.session_http, "_challenge_bytes", None)
        session_token_bytes = getattr(
            http.session_http,
            "_session_token_bytes",
            None,
        )
        if _bound_owner(challenge_bytes) is not runtime_inputs.material_source:
            _fail()
        if _bound_owner(session_token_bytes) is not runtime_inputs.material_source:
            _fail()

        asgi = MarketplaceSessionEstablishmentAsgiHttpAdapter(
            site=http.application.site,
            marketplace_http=http.application_http,
            auth_http=http.session_http,
            now=runtime_inputs.clock.now,
        )
        return MarketplaceAuthenticatedAsgiComposition(
            http=http,
            runtime_inputs=runtime_inputs,
            asgi=asgi,
        )
    except MarketplaceAuthenticatedAsgiCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticatedAsgiComposition",
    "MarketplaceAuthenticatedAsgiCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_authenticated_asgi",
]
