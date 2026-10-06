"""Inert composition for authenticated fulfillment completion HTTP."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_publication_http_composition import (
    MarketplaceAgreementPublicationHttpComposition,
)
from .fulfillment_completion_http import (
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from .fulfillment_completion_publication import (
    MarketplaceFulfillmentCompletionPublicationService,
)


PROFILE_NAME: Final = "MARKETPLACE_FULFILLMENT_COMPLETION_HTTP_COMPOSITION_V1"


class MarketplaceFulfillmentCompletionHttpCompositionError(ValueError):
    """Stable non-reflective failure for inert fulfillment HTTP composition."""

    def __init__(self) -> None:
        super().__init__("Fulfillment completion HTTP composition failed")


def _fail() -> None:
    raise MarketplaceFulfillmentCompletionHttpCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceFulfillmentCompletionHttpComposition:
    """One fulfillment adapter bound to the reviewed Agreement publication graph."""

    agreement_publication_http: MarketplaceAgreementPublicationHttpComposition
    fulfillment_publication: MarketplaceFulfillmentCompletionPublicationService
    fulfillment_http: MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter

    def __post_init__(self) -> None:
        if (
            type(self.agreement_publication_http)
            is not MarketplaceAgreementPublicationHttpComposition
        ):
            _fail()
        if (
            type(self.fulfillment_publication)
            is not MarketplaceFulfillmentCompletionPublicationService
        ):
            _fail()
        if (
            type(self.fulfillment_http)
            is not MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter
        ):
            _fail()
        if (
            self.fulfillment_http._base
            is not self.agreement_publication_http.publication_http
        ):
            _fail()
        if (
            self.fulfillment_http._auth
            is not self.agreement_publication_http.agreement_assent_http.authenticated_http.authentication.auth_service
        ):
            _fail()
        if (
            self.fulfillment_http._publication
            is not self.fulfillment_publication
        ):
            _fail()


def compose_marketplace_fulfillment_completion_http(
    *,
    agreement_publication_http: MarketplaceAgreementPublicationHttpComposition,
    fulfillment_publication: MarketplaceFulfillmentCompletionPublicationService,
) -> MarketplaceFulfillmentCompletionHttpComposition:
    """Compose fulfillment HTTP over the exact already-reviewed application graph."""
    if (
        type(agreement_publication_http)
        is not MarketplaceAgreementPublicationHttpComposition
    ):
        _fail()
    if (
        type(fulfillment_publication)
        is not MarketplaceFulfillmentCompletionPublicationService
    ):
        _fail()

    try:
        fulfillment_http = MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter(
            base=agreement_publication_http.publication_http,
            auth=agreement_publication_http.agreement_assent_http.authenticated_http.authentication.auth_service,
            publication=fulfillment_publication,
        )
        return MarketplaceFulfillmentCompletionHttpComposition(
            agreement_publication_http=agreement_publication_http,
            fulfillment_publication=fulfillment_publication,
            fulfillment_http=fulfillment_http,
        )
    except MarketplaceFulfillmentCompletionHttpCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceFulfillmentCompletionHttpComposition",
    "MarketplaceFulfillmentCompletionHttpCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_fulfillment_completion_http",
]
