"""M17.6J static authenticated enrollment HTTP composition.

This module binds the reviewed M17.6I enrollment HTTP adapter to the exact
M17.5P authenticated HTTP object graph without selecting ASGI, startup/runtime,
browser behavior, material generation, persistence, policy implementation, or
attestor/private-key custody.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_enrollment_authority import AuthenticationEnrollmentAuthorityAttestor
from .auth_enrollment_http import (
    MarketplaceAuthenticationEnrollmentHttpAdapter,
)
from .auth_enrollment_nonce import MarketplaceAuthenticationEnrollmentNonceAuthority
from .auth_enrollment_policy import AuthenticationEnrollmentApprovalPolicy
from .auth_http_composition import MarketplaceAuthenticatedHttpComposition


PROFILE_NAME: Final = (
    "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_COMPOSITION_V1"
)


class MarketplaceAuthenticationEnrollmentHttpCompositionError(ValueError):
    """Stable fail-closed composition error without enrollment-data reflection."""

    def __init__(self) -> None:
        super().__init__(
            "authenticated enrollment HTTP composition failed"
        )


def _fail() -> None:
    raise MarketplaceAuthenticationEnrollmentHttpCompositionError() from None


def _purpose_callable(owner: object, name: str):
    try:
        operation = getattr(owner, name, None)
    except Exception:
        _fail()
    if not callable(operation):
        _fail()
    return operation


def _validate_http_auth_identity(
    http: MarketplaceAuthenticatedHttpComposition,
) -> object:
    auth_service = http.authentication.auth_service
    if http.application_http._auth is not auth_service:
        _fail()
    if http.session_http._auth is not auth_service:
        _fail()
    if http.product_listing_authoring._auth is not auth_service:
        _fail()
    if http.proposal_authoring._auth is not auth_service:
        _fail()
    if (
        http.proposal_acceptance_authoring is not None
        and http.proposal_acceptance_authoring._auth is not auth_service
    ):
        _fail()
    return auth_service


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEnrollmentHttpComposition:
    """Immutable coherent references for source-only enrollment HTTP."""

    http: MarketplaceAuthenticatedHttpComposition
    nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority
    policy: AuthenticationEnrollmentApprovalPolicy
    attestor: AuthenticationEnrollmentAuthorityAttestor
    authority: str
    evidence_lease_seconds: int
    enrollment_http: MarketplaceAuthenticationEnrollmentHttpAdapter

    def __post_init__(self) -> None:
        if type(self.http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if (
            type(self.nonce_authority)
            is not MarketplaceAuthenticationEnrollmentNonceAuthority
        ):
            _fail()
        _purpose_callable(
            self.policy,
            "approve_authentication_enrollment",
        )
        _purpose_callable(
            self.attestor,
            "attest_authentication_enrollment",
        )
        if (
            type(self.enrollment_http)
            is not MarketplaceAuthenticationEnrollmentHttpAdapter
        ):
            _fail()

        auth_service = _validate_http_auth_identity(self.http)
        if self.enrollment_http._auth is not auth_service:
            _fail()
        if self.enrollment_http._nonce_authority is not self.nonce_authority:
            _fail()
        if self.enrollment_http._policy is not self.policy:
            _fail()
        if self.enrollment_http._attestor is not self.attestor:
            _fail()
        if self.enrollment_http._authority != self.authority:
            _fail()
        if (
            self.enrollment_http._lease_seconds
            != self.evidence_lease_seconds
        ):
            _fail()


def compose_marketplace_authentication_enrollment_http(
    *,
    http: MarketplaceAuthenticatedHttpComposition,
    nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceAuthenticationEnrollmentHttpComposition:
    """Compose reviewed enrollment HTTP objects without consuming them."""

    if type(http) is not MarketplaceAuthenticatedHttpComposition:
        _fail()
    if (
        type(nonce_authority)
        is not MarketplaceAuthenticationEnrollmentNonceAuthority
    ):
        _fail()

    try:
        _purpose_callable(
            policy,
            "approve_authentication_enrollment",
        )
        _purpose_callable(
            attestor,
            "attest_authentication_enrollment",
        )
        auth_service = _validate_http_auth_identity(http)
        enrollment_http = MarketplaceAuthenticationEnrollmentHttpAdapter(
            auth=auth_service,
            nonce_authority=nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
        )
        return MarketplaceAuthenticationEnrollmentHttpComposition(
            http=http,
            nonce_authority=nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            enrollment_http=enrollment_http,
        )
    except MarketplaceAuthenticationEnrollmentHttpCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticationEnrollmentHttpComposition",
    "MarketplaceAuthenticationEnrollmentHttpCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_authentication_enrollment_http",
]
