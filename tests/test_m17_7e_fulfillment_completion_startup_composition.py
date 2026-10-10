from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_http_composition import (
    MarketplaceAgreementAssentHttpComposition,
)
from marketplace.application.agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
)
from marketplace.application.agreement_publication import (
    MarketplaceAgreementPublicationPreflightService,
)
from marketplace.application.agreement_publication_http import (
    MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
)
from marketplace.application.agreement_publication_http_composition import (
    MarketplaceAgreementPublicationHttpComposition,
)
from marketplace.application.agreement_publication_write import (
    MarketplaceAgreementPublicationService,
)
from marketplace.application.auth_http_composition import (
    MarketplaceAuthenticatedHttpComposition,
)
from marketplace.application.auth_runtime_inputs import (
    MarketplaceAuthenticationRuntimeInputs,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.auth_session_http import (
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
)
from marketplace.application.fulfillment_completion_asgi_composition import (
    MarketplaceFulfillmentCompletionAsgiComposition,
)
from marketplace.application.fulfillment_completion_http import (
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from marketplace.application.fulfillment_completion_http_composition import (
    MarketplaceFulfillmentCompletionHttpComposition,
)
from marketplace.application.fulfillment_completion_publication import (
    MarketplaceFulfillmentCompletionPublicationService,
)
from marketplace.application.fulfillment_completion_startup_composition import (
    PROFILE_NAME,
    MarketplaceFulfillmentCompletionStartupComposition,
    MarketplaceFulfillmentCompletionStartupCompositionError,
    compose_marketplace_fulfillment_completion_startup,
)


def _exact_graph():
    runtime_inputs = object.__new__(MarketplaceAuthenticationRuntimeInputs)

    session_http = object.__new__(MarketplaceAuthenticationSessionHttpAdapter)
    authenticated_http = object.__new__(MarketplaceAuthenticatedHttpComposition)
    object.__setattr__(authenticated_http, "session_http", session_http)

    authenticated_startup = object.__new__(MarketplaceAuthenticatedStartupComposition)
    object.__setattr__(authenticated_startup, "http", authenticated_http)

    agreement_http = object.__new__(MarketplaceAgreementAssentHttpComposition)
    object.__setattr__(agreement_http, "authenticated_http", authenticated_http)

    agreement_startup = object.__new__(MarketplaceAgreementAssentStartupComposition)
    object.__setattr__(agreement_startup, "authenticated_startup", authenticated_startup)
    object.__setattr__(agreement_startup, "runtime_inputs", runtime_inputs)
    object.__setattr__(agreement_startup, "agreement_http", agreement_http)

    preflight = object.__new__(MarketplaceAgreementPublicationPreflightService)
    agreement_publication = object.__new__(MarketplaceAgreementPublicationService)
    fulfillment_publication = object.__new__(
        MarketplaceFulfillmentCompletionPublicationService
    )

    agreement_publication_adapter = object.__new__(
        MarketplaceAuthenticatedAgreementPublicationHttpAdapter
    )
    agreement_publication_http = object.__new__(
        MarketplaceAgreementPublicationHttpComposition
    )
    object.__setattr__(
        agreement_publication_http,
        "agreement_assent_http",
        agreement_http,
    )
    object.__setattr__(
        agreement_publication_http,
        "publication_http",
        agreement_publication_adapter,
    )

    fulfillment_adapter = object.__new__(
        MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter
    )
    fulfillment_http = object.__new__(
        MarketplaceFulfillmentCompletionHttpComposition
    )
    object.__setattr__(
        fulfillment_http,
        "agreement_publication_http",
        agreement_publication_http,
    )
    object.__setattr__(
        fulfillment_http,
        "fulfillment_http",
        fulfillment_adapter,
    )

    asgi = object.__new__(MarketplaceSessionEstablishmentAsgiHttpAdapter)
    object.__setattr__(asgi, "_marketplace_http", fulfillment_adapter)
    object.__setattr__(asgi, "_auth_http", session_http)

    fulfillment_asgi = object.__new__(
        MarketplaceFulfillmentCompletionAsgiComposition
    )
    object.__setattr__(fulfillment_asgi, "authenticated_http", authenticated_http)
    object.__setattr__(fulfillment_asgi, "fulfillment_http", fulfillment_http)
    object.__setattr__(fulfillment_asgi, "runtime_inputs", runtime_inputs)
    object.__setattr__(fulfillment_asgi, "asgi", asgi)

    return {
        "runtime_inputs": runtime_inputs,
        "authenticated_http": authenticated_http,
        "agreement_startup": agreement_startup,
        "preflight": preflight,
        "agreement_publication": agreement_publication,
        "fulfillment_publication": fulfillment_publication,
        "agreement_publication_http": agreement_publication_http,
        "fulfillment_http": fulfillment_http,
        "fulfillment_asgi": fulfillment_asgi,
    }


class M177EFulfillmentCompletionStartupCompositionTests(unittest.TestCase):
    def test_profile_is_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_FULFILLMENT_COMPLETION_STARTUP_COMPOSITION_V1",
        )

    def test_composition_chains_exact_reviewed_graphs(self) -> None:
        graph = _exact_graph()

        with (
            patch(
                "marketplace.application.fulfillment_completion_startup_composition."
                "compose_marketplace_agreement_publication_http",
                return_value=graph["agreement_publication_http"],
            ) as compose_agreement,
            patch(
                "marketplace.application.fulfillment_completion_startup_composition."
                "compose_marketplace_fulfillment_completion_http",
                return_value=graph["fulfillment_http"],
            ) as compose_http,
            patch(
                "marketplace.application.fulfillment_completion_startup_composition."
                "compose_marketplace_fulfillment_completion_asgi",
                return_value=graph["fulfillment_asgi"],
            ) as compose_asgi,
        ):
            result = compose_marketplace_fulfillment_completion_startup(
                agreement_startup=graph["agreement_startup"],
                runtime_inputs=graph["runtime_inputs"],
                agreement_publication_preflight=graph["preflight"],
                agreement_publication=graph["agreement_publication"],
                fulfillment_publication=graph["fulfillment_publication"],
            )

        self.assertIs(
            type(result),
            MarketplaceFulfillmentCompletionStartupComposition,
        )
        self.assertIs(result.agreement_startup, graph["agreement_startup"])
        self.assertIs(result.runtime_inputs, graph["runtime_inputs"])
        self.assertIs(
            result.agreement_publication_http,
            graph["agreement_publication_http"],
        )
        self.assertIs(result.fulfillment_http, graph["fulfillment_http"])
        self.assertIs(result.fulfillment_asgi, graph["fulfillment_asgi"])

        compose_agreement.assert_called_once_with(
            agreement_assent_http=graph["agreement_startup"].agreement_http,
            preflight=graph["preflight"],
            publication=graph["agreement_publication"],
        )
        compose_http.assert_called_once_with(
            agreement_publication_http=graph["agreement_publication_http"],
            fulfillment_publication=graph["fulfillment_publication"],
        )
        compose_asgi.assert_called_once_with(
            authenticated_http=graph["authenticated_http"],
            fulfillment_http=graph["fulfillment_http"],
            runtime_inputs=graph["runtime_inputs"],
        )

    def test_mismatched_runtime_inputs_fail_before_nested_composition(self) -> None:
        graph = _exact_graph()
        other_runtime_inputs = object.__new__(MarketplaceAuthenticationRuntimeInputs)

        with (
            patch(
                "marketplace.application.fulfillment_completion_startup_composition."
                "compose_marketplace_agreement_publication_http"
            ) as compose_agreement,
            patch(
                "marketplace.application.fulfillment_completion_startup_composition."
                "compose_marketplace_fulfillment_completion_http"
            ) as compose_http,
            patch(
                "marketplace.application.fulfillment_completion_startup_composition."
                "compose_marketplace_fulfillment_completion_asgi"
            ) as compose_asgi,
        ):
            with self.assertRaises(
                MarketplaceFulfillmentCompletionStartupCompositionError
            ):
                compose_marketplace_fulfillment_completion_startup(
                    agreement_startup=graph["agreement_startup"],
                    runtime_inputs=other_runtime_inputs,
                    agreement_publication_preflight=graph["preflight"],
                    agreement_publication=graph["agreement_publication"],
                    fulfillment_publication=graph["fulfillment_publication"],
                )

        compose_agreement.assert_not_called()
        compose_http.assert_not_called()
        compose_asgi.assert_not_called()

    def test_wrong_service_types_fail_before_nested_composition(self) -> None:
        graph = _exact_graph()

        with patch(
            "marketplace.application.fulfillment_completion_startup_composition."
            "compose_marketplace_agreement_publication_http"
        ) as compose_agreement:
            with self.assertRaises(
                MarketplaceFulfillmentCompletionStartupCompositionError
            ):
                compose_marketplace_fulfillment_completion_startup(
                    agreement_startup=graph["agreement_startup"],
                    runtime_inputs=graph["runtime_inputs"],
                    agreement_publication_preflight=object(),  # type: ignore[arg-type]
                    agreement_publication=graph["agreement_publication"],
                    fulfillment_publication=graph["fulfillment_publication"],
                )
        compose_agreement.assert_not_called()


if __name__ == "__main__":
    unittest.main()
