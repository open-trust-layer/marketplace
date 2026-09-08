"""M17.5P static authenticated HTTP composition without runtime selection.

This module wires only already-reviewed in-memory application/authentication
objects into reviewed HTTP adapters. It performs no provisioning, credential
generation, external I/O, clock selection, ASGI selection, or runtime execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth import (
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAuthoringService,
)
from .auth_http import (
    MarketplaceAuthenticatedApplicationHttpAdapter,
    RecordJsonDecoder,
    RecordPrincipalExtractor,
)
from .auth_session_http import (
    CredentialMaterialSource,
    MarketplaceAuthenticationSessionHttpAdapter,
)
from .auth_static_composition import MarketplaceStaticAuthenticationComposition
from .composition import MarketplaceApplicationComposition


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_HTTP_COMPOSITION_V1"


class MarketplaceAuthenticatedHttpCompositionError(ValueError):
    """Stable fail-closed composition error without authentication-data reflection."""

    def __init__(self) -> None:
        super().__init__("authenticated Marketplace HTTP composition failed")


def _fail() -> None:
    raise MarketplaceAuthenticatedHttpCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticatedHttpComposition:
    """One immutable reference to a coherent authenticated HTTP object graph."""

    application: MarketplaceApplicationComposition
    authentication: MarketplaceStaticAuthenticationComposition
    product_listing_authoring: AuthenticatedProductListingAuthoringService
    proposal_authoring: AuthenticatedProposalAuthoringService
    application_http: MarketplaceAuthenticatedApplicationHttpAdapter
    session_http: MarketplaceAuthenticationSessionHttpAdapter

    def __post_init__(self) -> None:
        if type(self.application) is not MarketplaceApplicationComposition:
            _fail()
        if (
            type(self.authentication)
            is not MarketplaceStaticAuthenticationComposition
        ):
            _fail()
        if (
            type(self.product_listing_authoring)
            is not AuthenticatedProductListingAuthoringService
        ):
            _fail()
        if (
            type(self.proposal_authoring)
            is not AuthenticatedProposalAuthoringService
        ):
            _fail()
        if (
            type(self.application_http)
            is not MarketplaceAuthenticatedApplicationHttpAdapter
        ):
            _fail()
        if (
            type(self.session_http)
            is not MarketplaceAuthenticationSessionHttpAdapter
        ):
            _fail()


def compose_marketplace_authenticated_http(
    *,
    application: MarketplaceApplicationComposition,
    authentication: MarketplaceStaticAuthenticationComposition,
    material_source: CredentialMaterialSource,
    decode_record_json: RecordJsonDecoder,
    record_principal: RecordPrincipalExtractor,
) -> MarketplaceAuthenticatedHttpComposition:
    """Compose one inert authenticated HTTP graph from reviewed injected objects."""

    if type(application) is not MarketplaceApplicationComposition:
        _fail()
    if (
        type(authentication)
        is not MarketplaceStaticAuthenticationComposition
    ):
        _fail()
    if not callable(decode_record_json) or not callable(record_principal):
        _fail()

    try:
        challenge_bytes = getattr(material_source, "challenge_bytes", None)
        session_token_bytes = getattr(material_source, "session_token_bytes", None)
        if not callable(challenge_bytes) or not callable(session_token_bytes):
            _fail()

        auth_service = authentication.auth_service
        product_listing_authoring = AuthenticatedProductListingAuthoringService(
            auth=auth_service,
            authoring=application.authoring,
        )
        proposal_authoring = AuthenticatedProposalAuthoringService(
            auth=auth_service,
            authoring=application.proposal_authoring,
        )
        application_http = MarketplaceAuthenticatedApplicationHttpAdapter(
            base=application.http,
            auth=auth_service,
            product_listing_authoring=product_listing_authoring,
            proposal_authoring=proposal_authoring,
            decode_record_json=decode_record_json,
            create_intent=application.api.create_intent,
            respond_to_intent=application.api.respond_to_intent,
            record_principal=record_principal,
        )
        session_http = MarketplaceAuthenticationSessionHttpAdapter(
            auth=auth_service,
            material_source=material_source,
            proof_verifier=authentication.proof_verifier,
        )
        return MarketplaceAuthenticatedHttpComposition(
            application=application,
            authentication=authentication,
            product_listing_authoring=product_listing_authoring,
            proposal_authoring=proposal_authoring,
            application_http=application_http,
            session_http=session_http,
        )
    except MarketplaceAuthenticatedHttpCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticatedHttpComposition",
    "MarketplaceAuthenticatedHttpCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_authenticated_http",
]
