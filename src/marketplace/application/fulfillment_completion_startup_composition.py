"""Inert startup overlay for authenticated fulfillment-completion composition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
)
from .agreement_publication import MarketplaceAgreementPublicationPreflightService
from .agreement_publication_http_composition import (
    MarketplaceAgreementPublicationHttpComposition,
    compose_marketplace_agreement_publication_http,
)
from .agreement_publication_write import MarketplaceAgreementPublicationService
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .fulfillment_completion_asgi_composition import (
    MarketplaceFulfillmentCompletionAsgiComposition,
    compose_marketplace_fulfillment_completion_asgi,
)
from .fulfillment_completion_http_composition import (
    MarketplaceFulfillmentCompletionHttpComposition,
    compose_marketplace_fulfillment_completion_http,
)
from .fulfillment_completion_publication import (
    MarketplaceFulfillmentCompletionPublicationService,
)


PROFILE_NAME: Final = "MARKETPLACE_FULFILLMENT_COMPLETION_STARTUP_COMPOSITION_V1"
_ERROR_MESSAGE: Final = "Fulfillment completion startup composition failed"


class MarketplaceFulfillmentCompletionStartupCompositionError(ValueError):
    """Stable non-reflective M17.7E startup-composition failure."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceFulfillmentCompletionStartupCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceFulfillmentCompletionStartupComposition:
    """One inert fulfillment overlay over the reviewed Agreement startup graph."""

    agreement_startup: MarketplaceAgreementAssentStartupComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    agreement_publication_http: MarketplaceAgreementPublicationHttpComposition
    fulfillment_http: MarketplaceFulfillmentCompletionHttpComposition
    fulfillment_asgi: MarketplaceFulfillmentCompletionAsgiComposition

    def __post_init__(self) -> None:
        if type(self.agreement_startup) is not MarketplaceAgreementAssentStartupComposition:
            _fail()
        if type(self.runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
            _fail()
        if (
            type(self.agreement_publication_http)
            is not MarketplaceAgreementPublicationHttpComposition
        ):
            _fail()
        if (
            type(self.fulfillment_http)
            is not MarketplaceFulfillmentCompletionHttpComposition
        ):
            _fail()
        if (
            type(self.fulfillment_asgi)
            is not MarketplaceFulfillmentCompletionAsgiComposition
        ):
            _fail()

        if self.agreement_startup.runtime_inputs is not self.runtime_inputs:
            _fail()
        if (
            self.agreement_publication_http.agreement_assent_http
            is not self.agreement_startup.agreement_http
        ):
            _fail()
        if (
            self.fulfillment_http.agreement_publication_http
            is not self.agreement_publication_http
        ):
            _fail()
        if self.fulfillment_asgi.fulfillment_http is not self.fulfillment_http:
            _fail()
        if (
            self.fulfillment_asgi.authenticated_http
            is not self.agreement_startup.authenticated_startup.http
        ):
            _fail()
        if self.fulfillment_asgi.runtime_inputs is not self.runtime_inputs:
            _fail()
        if (
            self.fulfillment_asgi.asgi._marketplace_http
            is not self.fulfillment_http.fulfillment_http
        ):
            _fail()
        if (
            self.fulfillment_asgi.asgi._auth_http
            is not self.agreement_startup.authenticated_startup.http.session_http
        ):
            _fail()


def compose_marketplace_fulfillment_completion_startup(
    *,
    agreement_startup: MarketplaceAgreementAssentStartupComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
    agreement_publication_preflight: MarketplaceAgreementPublicationPreflightService,
    agreement_publication: MarketplaceAgreementPublicationService,
    fulfillment_publication: MarketplaceFulfillmentCompletionPublicationService,
) -> MarketplaceFulfillmentCompletionStartupComposition:
    """Compose the reviewed fulfillment HTTP/ASGI overlay without runtime selection."""

    if type(agreement_startup) is not MarketplaceAgreementAssentStartupComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()
    if (
        type(agreement_publication_preflight)
        is not MarketplaceAgreementPublicationPreflightService
    ):
        _fail()
    if type(agreement_publication) is not MarketplaceAgreementPublicationService:
        _fail()
    if (
        type(fulfillment_publication)
        is not MarketplaceFulfillmentCompletionPublicationService
    ):
        _fail()
    if agreement_startup.runtime_inputs is not runtime_inputs:
        _fail()

    try:
        agreement_publication_http = compose_marketplace_agreement_publication_http(
            agreement_assent_http=agreement_startup.agreement_http,
            preflight=agreement_publication_preflight,
            publication=agreement_publication,
        )
        fulfillment_http = compose_marketplace_fulfillment_completion_http(
            agreement_publication_http=agreement_publication_http,
            fulfillment_publication=fulfillment_publication,
        )
        fulfillment_asgi = compose_marketplace_fulfillment_completion_asgi(
            authenticated_http=agreement_startup.authenticated_startup.http,
            fulfillment_http=fulfillment_http,
            runtime_inputs=runtime_inputs,
        )
        return MarketplaceFulfillmentCompletionStartupComposition(
            agreement_startup=agreement_startup,
            runtime_inputs=runtime_inputs,
            agreement_publication_http=agreement_publication_http,
            fulfillment_http=fulfillment_http,
            fulfillment_asgi=fulfillment_asgi,
        )
    except MarketplaceFulfillmentCompletionStartupCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceFulfillmentCompletionStartupComposition",
    "MarketplaceFulfillmentCompletionStartupCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_fulfillment_completion_startup",
]
