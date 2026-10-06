from __future__ import annotations

import unittest

from marketplace.application.agreement_assent_http_composition import (
    MarketplaceAgreementAssentHttpComposition,
)
from marketplace.application.agreement_publication_http import (
    MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
)
from marketplace.application.agreement_publication_http_composition import (
    MarketplaceAgreementPublicationHttpComposition,
)
from marketplace.application.auth import MarketplaceApplicationAuthService
from marketplace.application.auth_http_composition import MarketplaceAuthenticatedHttpComposition
from marketplace.application.auth_static_composition import MarketplaceStaticAuthenticationComposition
from marketplace.application.fulfillment_completion_http import (
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from marketplace.application.fulfillment_completion_http_composition import (
    PROFILE_NAME,
    MarketplaceFulfillmentCompletionHttpCompositionError,
    compose_marketplace_fulfillment_completion_http,
)
from marketplace.application.fulfillment_completion_publication import (
    MarketplaceFulfillmentCompletionPublicationService,
)


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return True


def _exact_graph():
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())

    authentication = object.__new__(MarketplaceStaticAuthenticationComposition)
    object.__setattr__(authentication, "auth_service", auth)

    authenticated = object.__new__(MarketplaceAuthenticatedHttpComposition)
    object.__setattr__(authenticated, "authentication", authentication)

    assent = object.__new__(MarketplaceAgreementAssentHttpComposition)
    object.__setattr__(assent, "authenticated_http", authenticated)

    publication_http = object.__new__(
        MarketplaceAuthenticatedAgreementPublicationHttpAdapter
    )
    agreement_publication = object.__new__(
        MarketplaceAgreementPublicationHttpComposition
    )
    object.__setattr__(agreement_publication, "agreement_assent_http", assent)
    object.__setattr__(agreement_publication, "publication_http", publication_http)

    fulfillment_publication = object.__new__(
        MarketplaceFulfillmentCompletionPublicationService
    )
    return auth, agreement_publication, publication_http, fulfillment_publication


class M177CFulfillmentCompletionHttpCompositionTests(unittest.TestCase):
    def test_profile_and_type_failures_are_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_FULFILLMENT_COMPLETION_HTTP_COMPOSITION_V1",
        )
        _, agreement_publication, _, fulfillment_publication = _exact_graph()
        with self.assertRaises(
            MarketplaceFulfillmentCompletionHttpCompositionError
        ) as caught:
            compose_marketplace_fulfillment_completion_http(
                agreement_publication_http=object(),  # type: ignore[arg-type]
                fulfillment_publication=fulfillment_publication,
            )
        self.assertEqual(
            str(caught.exception),
            "Fulfillment completion HTTP composition failed",
        )

        with self.assertRaises(MarketplaceFulfillmentCompletionHttpCompositionError):
            compose_marketplace_fulfillment_completion_http(
                agreement_publication_http=agreement_publication,
                fulfillment_publication=object(),  # type: ignore[arg-type]
            )

    def test_composition_reuses_exact_reviewed_graph(self) -> None:
        auth, agreement_publication, publication_http, fulfillment_publication = (
            _exact_graph()
        )

        composition = compose_marketplace_fulfillment_completion_http(
            agreement_publication_http=agreement_publication,
            fulfillment_publication=fulfillment_publication,
        )

        self.assertIs(composition.agreement_publication_http, agreement_publication)
        self.assertIs(composition.fulfillment_publication, fulfillment_publication)
        self.assertIs(
            type(composition.fulfillment_http),
            MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
        )
        self.assertIs(composition.fulfillment_http._base, publication_http)
        self.assertIs(composition.fulfillment_http._auth, auth)
        self.assertIs(
            composition.fulfillment_http._publication,
            fulfillment_publication,
        )


if __name__ == "__main__":
    unittest.main()
