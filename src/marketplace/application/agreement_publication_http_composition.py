"""Inert composition for authenticated Agreement publication HTTP."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_assent_http_composition import (
    MarketplaceAgreementAssentHttpComposition,
)
from .agreement_publication import MarketplaceAgreementPublicationPreflightService
from .agreement_publication_http import (
    MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
)
from .agreement_publication_write import MarketplaceAgreementPublicationService


PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_PUBLICATION_HTTP_COMPOSITION_V1"


class MarketplaceAgreementPublicationHttpCompositionError(ValueError):
    """Stable non-reflective failure for inert Agreement publication composition."""

    def __init__(self) -> None:
        super().__init__("Agreement publication HTTP composition failed")


def _fail() -> None:
    raise MarketplaceAgreementPublicationHttpCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceAgreementPublicationHttpComposition:
    """One publication adapter bound to the reviewed Agreement-assent graph."""

    agreement_assent_http: MarketplaceAgreementAssentHttpComposition
    preflight: MarketplaceAgreementPublicationPreflightService
    publication: MarketplaceAgreementPublicationService
    publication_http: MarketplaceAuthenticatedAgreementPublicationHttpAdapter

    def __post_init__(self) -> None:
        if type(self.agreement_assent_http) is not MarketplaceAgreementAssentHttpComposition:
            _fail()
        if type(self.preflight) is not MarketplaceAgreementPublicationPreflightService:
            _fail()
        if type(self.publication) is not MarketplaceAgreementPublicationService:
            _fail()
        if (
            type(self.publication_http)
            is not MarketplaceAuthenticatedAgreementPublicationHttpAdapter
        ):
            _fail()
        if self.publication_http._base is not self.agreement_assent_http.assent_http:
            _fail()
        if (
            self.publication_http._auth
            is not self.agreement_assent_http.authenticated_http.authentication.auth_service
        ):
            _fail()
        if (
            self.publication_http._candidate_resolution
            is not self.agreement_assent_http.candidate_resolution
        ):
            _fail()
        if self.publication_http._workflow is not self.agreement_assent_http.workflow:
            _fail()
        if self.publication_http._preflight is not self.preflight:
            _fail()
        if self.publication_http._publication is not self.publication:
            _fail()


def compose_marketplace_agreement_publication_http(
    *,
    agreement_assent_http: MarketplaceAgreementAssentHttpComposition,
    preflight: MarketplaceAgreementPublicationPreflightService,
    publication: MarketplaceAgreementPublicationService,
) -> MarketplaceAgreementPublicationHttpComposition:
    """Compose publication over the exact already-reviewed assent object graph."""
    if type(agreement_assent_http) is not MarketplaceAgreementAssentHttpComposition:
        _fail()
    if type(preflight) is not MarketplaceAgreementPublicationPreflightService:
        _fail()
    if type(publication) is not MarketplaceAgreementPublicationService:
        _fail()

    try:
        publication_http = MarketplaceAuthenticatedAgreementPublicationHttpAdapter(
            base=agreement_assent_http.assent_http,
            auth=agreement_assent_http.authenticated_http.authentication.auth_service,
            candidate_resolution=agreement_assent_http.candidate_resolution,
            workflow=agreement_assent_http.workflow,
            preflight=preflight,
            publication=publication,
        )
        return MarketplaceAgreementPublicationHttpComposition(
            agreement_assent_http=agreement_assent_http,
            preflight=preflight,
            publication=publication,
            publication_http=publication_http,
        )
    except MarketplaceAgreementPublicationHttpCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAgreementPublicationHttpComposition",
    "MarketplaceAgreementPublicationHttpCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_agreement_publication_http",
]
