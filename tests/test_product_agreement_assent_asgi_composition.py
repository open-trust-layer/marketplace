from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_asgi_composition import (
    PROFILE_NAME,
    MarketplaceAgreementAssentAsgiComposition,
    MarketplaceAgreementAssentAsgiCompositionError,
    compose_marketplace_agreement_assent_asgi,
)
from marketplace.application.agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from marketplace.application.agreement_assent_http import (
    MarketplaceAuthenticatedAgreementAssentHttpAdapter,
)
from marketplace.application.agreement_assent_http_composition import (
    compose_marketplace_agreement_assent_http,
)
from marketplace.application.agreement_assent_workflow import (
    MarketplaceAgreementAssentWorkflowService,
)
from marketplace.application.auth_http_composition import (
    compose_marketplace_authenticated_http,
)
from marketplace.application.auth_session_http import (
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.composition import MarketplaceApplicationComposition
from marketplace.application.auth_runtime_inputs import (
    compose_marketplace_authentication_runtime_inputs,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
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
    resolver = object.__new__(MarketplaceAgreementAssentCandidateResolutionService)
    workflow = object.__new__(MarketplaceAgreementAssentWorkflowService)
    agreement_http = compose_marketplace_agreement_assent_http(
        authenticated_http=authenticated_http,
        candidate_resolution=resolver,
        workflow=workflow,
        encode_signing_input=lambda value: value,
        decode_signature=lambda value: value,
    )
    return authenticated_http, agreement_http, runtime_inputs


class ProductAgreementAssentAsgiCompositionTests(unittest.TestCase):
    def test_profile_exact_types_and_identity_coherence(self) -> None:
        authenticated_http, agreement_http, runtime_inputs = _graph()
        result = compose_marketplace_agreement_assent_asgi(
            authenticated_http=authenticated_http,
            agreement_http=agreement_http,
            runtime_inputs=runtime_inputs,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_AGREEMENT_ASSENT_ASGI_COMPOSITION_V1",
        )
        self.assertIs(type(result), MarketplaceAgreementAssentAsgiComposition)
        self.assertIs(result.authenticated_http, authenticated_http)
        self.assertIs(result.agreement_http, agreement_http)
        self.assertIs(result.runtime_inputs, runtime_inputs)
        self.assertIs(type(result.asgi), MarketplaceSessionEstablishmentAsgiHttpAdapter)
        self.assertIs(result.asgi._site, authenticated_http.application.site)
        self.assertIs(result.asgi._marketplace_http, agreement_http.assent_http)
        self.assertIs(result.asgi._auth_http, authenticated_http.session_http)
        self.assertIs(result.asgi._now.__self__, runtime_inputs.clock)

    def test_composition_consumes_no_runtime_inputs_or_http_handlers(self) -> None:
        authenticated_http, agreement_http, runtime_inputs = _graph()
        with (
            patch("marketplace.application.auth_material._token_bytes") as material,
            patch("marketplace.application.auth_runtime_inputs._time_ns") as clock,
            patch.object(
                MarketplaceApplicationComposition,
                "initialize",
                side_effect=AssertionError("initialized"),
            ) as initialize,
            patch.object(
                MarketplaceAuthenticatedAgreementAssentHttpAdapter,
                "handle",
                side_effect=AssertionError("agreement request handled"),
            ) as agreement_handle,
            patch.object(
                MarketplaceAuthenticationSessionHttpAdapter,
                "handle",
                side_effect=AssertionError("auth request handled"),
            ) as auth_handle,
        ):
            result = compose_marketplace_agreement_assent_asgi(
                authenticated_http=authenticated_http,
                agreement_http=agreement_http,
                runtime_inputs=runtime_inputs,
            )

        self.assertIs(result.asgi._marketplace_http, agreement_http.assent_http)
        material.assert_not_called()
        clock.assert_not_called()
        initialize.assert_not_called()
        agreement_handle.assert_not_called()
        auth_handle.assert_not_called()

    def test_mismatched_http_graph_fails_before_asgi_construction(self) -> None:
        authenticated_http, agreement_http, runtime_inputs = _graph()
        other_http, _other_agreement_http, _other_runtime_inputs = _graph()
        self.assertIsNot(agreement_http.authenticated_http, other_http)

        with patch(
            "marketplace.application.agreement_assent_asgi_composition."
            "MarketplaceSessionEstablishmentAsgiHttpAdapter"
        ) as constructor:
            with self.assertRaises(
                MarketplaceAgreementAssentAsgiCompositionError
            ):
                compose_marketplace_agreement_assent_asgi(
                    authenticated_http=other_http,
                    agreement_http=agreement_http,
                    runtime_inputs=runtime_inputs,
                )
        constructor.assert_not_called()

    def test_mismatched_runtime_material_fails_before_asgi_construction(self) -> None:
        authenticated_http, agreement_http, _runtime_inputs = _graph()
        other = compose_marketplace_authentication_runtime_inputs()
        with patch(
            "marketplace.application.agreement_assent_asgi_composition."
            "MarketplaceSessionEstablishmentAsgiHttpAdapter"
        ) as constructor:
            with self.assertRaises(
                MarketplaceAgreementAssentAsgiCompositionError
            ):
                compose_marketplace_agreement_assent_asgi(
                    authenticated_http=authenticated_http,
                    agreement_http=agreement_http,
                    runtime_inputs=other,
                )
        constructor.assert_not_called()

    def test_unknown_marketplace_http_type_remains_rejected_by_session_asgi(self) -> None:
        authenticated_http, _agreement_http, runtime_inputs = _graph()
        with self.assertRaises(TypeError):
            MarketplaceSessionEstablishmentAsgiHttpAdapter(
                site=authenticated_http.application.site,
                marketplace_http=object(),  # type: ignore[arg-type]
                auth_http=authenticated_http.session_http,
                now=runtime_inputs.clock.now,
            )


if __name__ == "__main__":
    unittest.main()
