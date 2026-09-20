from __future__ import annotations

import unittest

from marketplace.application.agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from marketplace.application.agreement_assent_http import (
    MarketplaceAuthenticatedAgreementAssentHttpAdapter,
)
from marketplace.application.agreement_assent_http_composition import (
    PROFILE_NAME,
    MarketplaceAgreementAssentHttpCompositionError,
    compose_marketplace_agreement_assent_http,
)
from marketplace.application.agreement_assent_workflow import (
    MarketplaceAgreementAssentWorkflowService,
)
from marketplace.application.auth import MarketplaceApplicationAuthService
from marketplace.application.auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from marketplace.application.auth_http_composition import MarketplaceAuthenticatedHttpComposition
from marketplace.application.auth_static_composition import MarketplaceStaticAuthenticationComposition


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return True


def _exact_graph():
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())

    authentication = object.__new__(MarketplaceStaticAuthenticationComposition)
    object.__setattr__(authentication, "auth_service", auth)

    base = object.__new__(MarketplaceAuthenticatedApplicationHttpAdapter)

    authenticated = object.__new__(MarketplaceAuthenticatedHttpComposition)
    object.__setattr__(authenticated, "authentication", authentication)
    object.__setattr__(authenticated, "application_http", base)

    resolver = object.__new__(MarketplaceAgreementAssentCandidateResolutionService)
    workflow = object.__new__(MarketplaceAgreementAssentWorkflowService)
    return authenticated, authentication, auth, base, resolver, workflow


class MarketplaceAgreementAssentHttpCompositionTests(unittest.TestCase):
    def test_profile_and_stable_type_failure(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_AGREEMENT_ASSENT_HTTP_COMPOSITION_V1",
        )
        authenticated, _, _, _, resolver, workflow = _exact_graph()
        with self.assertRaises(
            MarketplaceAgreementAssentHttpCompositionError
        ) as caught:
            compose_marketplace_agreement_assent_http(
                authenticated_http=object(),  # type: ignore[arg-type]
                candidate_resolution=resolver,
                workflow=workflow,
                encode_signing_input=lambda value: value,
                decode_signature=lambda value: value,
            )
        self.assertEqual(
            str(caught.exception),
            "Agreement assent HTTP composition failed",
        )
        with self.assertRaises(MarketplaceAgreementAssentHttpCompositionError):
            compose_marketplace_agreement_assent_http(
                authenticated_http=authenticated,
                candidate_resolution=object(),  # type: ignore[arg-type]
                workflow=workflow,
                encode_signing_input=lambda value: value,
                decode_signature=lambda value: value,
            )

    def test_composition_reuses_exact_authenticated_graph(self) -> None:
        authenticated, authentication, auth, base, resolver, workflow = _exact_graph()
        calls = []

        def encode(value):
            calls.append(("encode", value))
            return value

        def decode(value):
            calls.append(("decode", value))
            return value

        composition = compose_marketplace_agreement_assent_http(
            authenticated_http=authenticated,
            candidate_resolution=resolver,
            workflow=workflow,
            encode_signing_input=encode,
            decode_signature=decode,
        )

        self.assertIs(composition.authenticated_http, authenticated)
        self.assertIs(composition.candidate_resolution, resolver)
        self.assertIs(composition.workflow, workflow)
        self.assertIs(composition.assent_http._base, base)
        self.assertIs(composition.assent_http._auth, auth)
        self.assertIs(composition.assent_http._candidate_resolution, resolver)
        self.assertIs(composition.assent_http._workflow, workflow)
        self.assertIs(composition.assent_http._encode_signing_input, encode)
        self.assertIs(composition.assent_http._decode_signature, decode)
        self.assertIs(authenticated.authentication, authentication)
        self.assertEqual(calls, [])

    def test_noncallable_transport_boundary_fails_before_construction(self) -> None:
        authenticated, _, _, _, resolver, workflow = _exact_graph()
        with self.assertRaises(MarketplaceAgreementAssentHttpCompositionError):
            compose_marketplace_agreement_assent_http(
                authenticated_http=authenticated,
                candidate_resolution=resolver,
                workflow=workflow,
                encode_signing_input=object(),  # type: ignore[arg-type]
                decode_signature=lambda value: value,
            )

    def test_tampered_inner_graph_fails_closed(self) -> None:
        authenticated, _, _, _, resolver, workflow = _exact_graph()
        object.__setattr__(authenticated, "application_http", object())
        with self.assertRaises(MarketplaceAgreementAssentHttpCompositionError):
            compose_marketplace_agreement_assent_http(
                authenticated_http=authenticated,
                candidate_resolution=resolver,
                workflow=workflow,
                encode_signing_input=lambda value: value,
                decode_signature=lambda value: value,
            )


if __name__ == "__main__":
    unittest.main()
