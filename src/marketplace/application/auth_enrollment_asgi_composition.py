"""M17.6K enrollment-aware authenticated ASGI composition.

This module selects the reviewed M17.6J enrollment HTTP graph into the existing
single authenticated ASGI parser/bearer/time boundary. Composition is inert and
performs no material generation, clock read, request handling, provider access,
startup selection, launch, or runtime execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_enrollment_http_composition import (
    MarketplaceAuthenticationEnrollmentHttpComposition,
)
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_ASGI_COMPOSITION_V1"


class MarketplaceAuthenticationEnrollmentAsgiCompositionError(ValueError):
    """Stable fail-closed composition error without enrollment reflection."""

    def __init__(self) -> None:
        super().__init__("authentication enrollment ASGI composition failed")


def _fail() -> None:
    raise MarketplaceAuthenticationEnrollmentAsgiCompositionError() from None


def _bound_owner(value: object) -> object | None:
    try:
        if not callable(value):
            return None
        return getattr(value, "__self__", None)
    except Exception:
        _fail()


def _authenticated_http(
    enrollment: MarketplaceAuthenticationEnrollmentHttpComposition,
):
    if type(enrollment) is not MarketplaceAuthenticationEnrollmentHttpComposition:
        _fail()
    http = enrollment.http
    try:
        auth_service = http.authentication.auth_service
        if http.application_http._auth is not auth_service:
            _fail()
        if http.session_http._auth is not auth_service:
            _fail()
        if enrollment.enrollment_http._auth is not auth_service:
            _fail()
    except MarketplaceAuthenticationEnrollmentAsgiCompositionError:
        raise
    except Exception:
        _fail()
    return http


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEnrollmentAsgiComposition:
    """Immutable coherent references to J + runtime inputs + one ASGI adapter."""

    enrollment: MarketplaceAuthenticationEnrollmentHttpComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        if type(self.enrollment) is not MarketplaceAuthenticationEnrollmentHttpComposition:
            _fail()
        if type(self.runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
            _fail()
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()

        http = _authenticated_http(self.enrollment)
        if self.asgi._site is not http.application.site:
            _fail()
        if self.asgi._marketplace_http is not http.application_http:
            _fail()
        if self.asgi._auth_http is not http.session_http:
            _fail()
        if self.asgi._enrollment_http is not self.enrollment.enrollment_http:
            _fail()
        if (
            _bound_owner(http.session_http._challenge_bytes)
            is not self.runtime_inputs.material_source
        ):
            _fail()
        if (
            _bound_owner(http.session_http._session_token_bytes)
            is not self.runtime_inputs.material_source
        ):
            _fail()
        if _bound_owner(self.asgi._now) is not self.runtime_inputs.clock:
            _fail()


def compose_marketplace_authentication_enrollment_asgi(
    *,
    enrollment: MarketplaceAuthenticationEnrollmentHttpComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> MarketplaceAuthenticationEnrollmentAsgiComposition:
    """Compose exact enrollment-aware ASGI routing without consuming inputs."""

    if type(enrollment) is not MarketplaceAuthenticationEnrollmentHttpComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()

    try:
        http = _authenticated_http(enrollment)
        if (
            _bound_owner(http.session_http._challenge_bytes)
            is not runtime_inputs.material_source
        ):
            _fail()
        if (
            _bound_owner(http.session_http._session_token_bytes)
            is not runtime_inputs.material_source
        ):
            _fail()

        asgi = MarketplaceSessionEstablishmentAsgiHttpAdapter(
            site=http.application.site,
            marketplace_http=http.application_http,
            auth_http=http.session_http,
            now=runtime_inputs.clock.now,
            enrollment_http=enrollment.enrollment_http,
        )
        return MarketplaceAuthenticationEnrollmentAsgiComposition(
            enrollment=enrollment,
            runtime_inputs=runtime_inputs,
            asgi=asgi,
        )
    except MarketplaceAuthenticationEnrollmentAsgiCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticationEnrollmentAsgiComposition",
    "MarketplaceAuthenticationEnrollmentAsgiCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_authentication_enrollment_asgi",
]
