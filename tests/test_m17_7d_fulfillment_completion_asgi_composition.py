from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_http_composition import (
    MarketplaceAgreementAssentHttpComposition,
)
from marketplace.application.agreement_publication_http_composition import (
    MarketplaceAgreementPublicationHttpComposition,
)
from marketplace.application.auth_http_composition import (
    compose_marketplace_authenticated_http,
)
from marketplace.application.auth_runtime_inputs import (
    compose_marketplace_authentication_runtime_inputs,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.auth_session_http import (
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.composition import MarketplaceApplicationComposition
from marketplace.application.fulfillment_completion_asgi_composition import (
    PROFILE_NAME,
    MarketplaceFulfillmentCompletionAsgiComposition,
    MarketplaceFulfillmentCompletionAsgiCompositionError,
    compose_marketplace_fulfillment_completion_asgi,
)
from marketplace.application.fulfillment_completion_http import (
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from marketplace.application.fulfillment_completion_http_composition import (
    MarketplaceFulfillmentCompletionHttpComposition,
)
from tests.test_m17_5p_auth_http_composition import (
    _application,
    _authentication,
    _decode_json,
)


def _graph():
    application, _store = _application()
    authentication = _authentication()
    runtime_inputs = compose_marketplace_authentication_runtime_inputs()
    authenticated_http = compose_marketplace_authenticated_http(
        application=application,
        authentication=authentication,
        material_source=runtime_inputs.material_source,
        decode_record_json=_decode_json,
        record_principal=lambda record: record["issuer"],
    )

    agreement_http = object.__new__(MarketplaceAgreementAssentHttpComposition)
    object.__setattr__(agreement_http, "authenticated_http", authenticated_http)

    agreement_publication = object.__new__(
        MarketplaceAgreementPublicationHttpComposition
    )
    object.__setattr__(
        agreement_publication,
        "agreement_assent_http",
        agreement_http,
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
        agreement_publication,
    )
    object.__setattr__(
        fulfillment_http,
        "fulfillment_http",
        fulfillment_adapter,
    )
    return authenticated_http, fulfillment_http, runtime_inputs


class M177DFulfillmentCompletionAsgiCompositionTests(unittest.TestCase):
    def test_profile_exact_types_and_identity_coherence(self) -> None:
        authenticated_http, fulfillment_http, runtime_inputs = _graph()
        result = compose_marketplace_fulfillment_completion_asgi(
            authenticated_http=authenticated_http,
            fulfillment_http=fulfillment_http,
            runtime_inputs=runtime_inputs,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_FULFILLMENT_COMPLETION_ASGI_COMPOSITION_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceFulfillmentCompletionAsgiComposition,
        )
        self.assertIs(result.authenticated_http, authenticated_http)
        self.assertIs(result.fulfillment_http, fulfillment_http)
        self.assertIs(result.runtime_inputs, runtime_inputs)
        self.assertIs(
            type(result.asgi),
            MarketplaceSessionEstablishmentAsgiHttpAdapter,
        )
        self.assertIs(result.asgi._site, authenticated_http.application.site)
        self.assertIs(
            result.asgi._marketplace_http,
            fulfillment_http.fulfillment_http,
        )
        self.assertIs(result.asgi._auth_http, authenticated_http.session_http)
        self.assertIs(result.asgi._now.__self__, runtime_inputs.clock)

    def test_composition_consumes_no_runtime_inputs_or_handlers(self) -> None:
        authenticated_http, fulfillment_http, runtime_inputs = _graph()
        with (
            patch("marketplace.application.auth_material._token_bytes") as material,
            patch("marketplace.application.auth_runtime_inputs._time_ns") as clock,
            patch.object(
                MarketplaceApplicationComposition,
                "initialize",
                side_effect=AssertionError("initialized"),
            ) as initialize,
            patch.object(
                MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
                "handle",
                side_effect=AssertionError("fulfillment request handled"),
            ) as fulfillment_handle,
            patch.object(
                MarketplaceAuthenticationSessionHttpAdapter,
                "handle",
                side_effect=AssertionError("auth request handled"),
            ) as auth_handle,
        ):
            result = compose_marketplace_fulfillment_completion_asgi(
                authenticated_http=authenticated_http,
                fulfillment_http=fulfillment_http,
                runtime_inputs=runtime_inputs,
            )

        self.assertIs(
            result.asgi._marketplace_http,
            fulfillment_http.fulfillment_http,
        )
        material.assert_not_called()
        clock.assert_not_called()
        initialize.assert_not_called()
        fulfillment_handle.assert_not_called()
        auth_handle.assert_not_called()

    def test_mismatched_http_graph_fails_before_asgi_construction(self) -> None:
        authenticated_http, fulfillment_http, runtime_inputs = _graph()
        other_http, _other_fulfillment, _other_runtime = _graph()

        with patch(
            "marketplace.application.fulfillment_completion_asgi_composition."
            "MarketplaceSessionEstablishmentAsgiHttpAdapter"
        ) as constructor:
            with self.assertRaises(
                MarketplaceFulfillmentCompletionAsgiCompositionError
            ):
                compose_marketplace_fulfillment_completion_asgi(
                    authenticated_http=other_http,
                    fulfillment_http=fulfillment_http,
                    runtime_inputs=runtime_inputs,
                )
        constructor.assert_not_called()

    def test_mismatched_runtime_material_fails_before_asgi_construction(self) -> None:
        authenticated_http, fulfillment_http, _runtime_inputs = _graph()
        other = compose_marketplace_authentication_runtime_inputs()

        with patch(
            "marketplace.application.fulfillment_completion_asgi_composition."
            "MarketplaceSessionEstablishmentAsgiHttpAdapter"
        ) as constructor:
            with self.assertRaises(
                MarketplaceFulfillmentCompletionAsgiCompositionError
            ):
                compose_marketplace_fulfillment_completion_asgi(
                    authenticated_http=authenticated_http,
                    fulfillment_http=fulfillment_http,
                    runtime_inputs=other,
                )
        constructor.assert_not_called()

    def test_session_asgi_accepts_exact_fulfillment_overlay_only(self) -> None:
        authenticated_http, fulfillment_http, runtime_inputs = _graph()
        exact = MarketplaceSessionEstablishmentAsgiHttpAdapter(
            site=authenticated_http.application.site,
            marketplace_http=fulfillment_http.fulfillment_http,
            auth_http=authenticated_http.session_http,
            now=runtime_inputs.clock.now,
        )
        self.assertIs(
            exact._marketplace_http,
            fulfillment_http.fulfillment_http,
        )
        with self.assertRaises(TypeError):
            MarketplaceSessionEstablishmentAsgiHttpAdapter(
                site=authenticated_http.application.site,
                marketplace_http=object(),  # type: ignore[arg-type]
                auth_http=authenticated_http.session_http,
                now=runtime_inputs.clock.now,
            )


if __name__ == "__main__":
    unittest.main()
