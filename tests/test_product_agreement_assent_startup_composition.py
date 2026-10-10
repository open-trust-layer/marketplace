from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from marketplace.application.agreement_assent_startup_composition import (
    PROFILE_NAME,
    MarketplaceAgreementAssentStartupComposition,
    MarketplaceAgreementAssentStartupCompositionError,
    compose_marketplace_agreement_assent_startup,
)
from marketplace.application.agreement_assent_workflow import (
    MarketplaceAgreementAssentWorkflowService,
)
from marketplace.application.auth_runtime_inputs import (
    compose_marketplace_authentication_runtime_inputs,
)
from tests.test_m17_5t_auth_startup_composition import _compose as _compose_auth_startup


def _candidate_resolution() -> MarketplaceAgreementAssentCandidateResolutionService:
    return object.__new__(MarketplaceAgreementAssentCandidateResolutionService)


def _workflow() -> MarketplaceAgreementAssentWorkflowService:
    return object.__new__(MarketplaceAgreementAssentWorkflowService)


def _encode(value: bytes) -> bytes:
    return value


def _decode(value: object) -> bytes:
    if type(value) is not bytes:
        raise TypeError("test carrier must be bytes")
    return value


def _compose():
    authenticated_startup, _application, _provisioning, runtime_inputs = (
        _compose_auth_startup()
    )
    result = compose_marketplace_agreement_assent_startup(
        authenticated_startup=authenticated_startup,
        runtime_inputs=runtime_inputs,
        candidate_resolution=_candidate_resolution(),
        workflow=_workflow(),
        encode_signing_input=_encode,
        decode_signature=_decode,
    )
    return result, authenticated_startup, runtime_inputs


class ProductAgreementAssentStartupCompositionTests(unittest.TestCase):
    def test_profile_exact_types_and_identity_coherence(self) -> None:
        result, authenticated_startup, runtime_inputs = _compose()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_AGREEMENT_ASSENT_STARTUP_COMPOSITION_V1",
        )
        self.assertIs(type(result), MarketplaceAgreementAssentStartupComposition)
        self.assertIs(result.authenticated_startup, authenticated_startup)
        self.assertIs(result.runtime_inputs, runtime_inputs)
        self.assertIs(
            result.agreement_http.authenticated_http,
            authenticated_startup.http,
        )
        self.assertIs(
            result.agreement_asgi.authenticated_http,
            authenticated_startup.http,
        )
        self.assertIs(result.agreement_asgi.agreement_http, result.agreement_http)
        self.assertIs(
            result.agreement_asgi.asgi._marketplace_http,
            result.agreement_http.assent_http,
        )
        self.assertIs(
            result.agreement_asgi.asgi._auth_http,
            authenticated_startup.http.session_http,
        )

    def test_overlay_composition_consumes_no_new_clock_or_material(self) -> None:
        authenticated_startup, _application, _provisioning, runtime_inputs = (
            _compose_auth_startup()
        )
        candidate = _candidate_resolution()
        workflow = _workflow()

        with (
            patch("marketplace.application.auth_runtime_inputs._time_ns") as clock,
            patch("marketplace.application.auth_material._token_bytes") as material,
            patch.object(
                MarketplaceAgreementAssentCandidateResolutionService,
                "resolve",
                side_effect=AssertionError("candidate resolution executed"),
            ) as resolve,
            patch.object(
                MarketplaceAgreementAssentWorkflowService,
                "prepare",
                side_effect=AssertionError("workflow executed"),
            ) as prepare,
        ):
            result = compose_marketplace_agreement_assent_startup(
                authenticated_startup=authenticated_startup,
                runtime_inputs=runtime_inputs,
                candidate_resolution=candidate,
                workflow=workflow,
                encode_signing_input=_encode,
                decode_signature=_decode,
            )

        self.assertIs(result.authenticated_startup, authenticated_startup)
        clock.assert_not_called()
        material.assert_not_called()
        resolve.assert_not_called()
        prepare.assert_not_called()

    def test_mismatched_runtime_inputs_fail_closed(self) -> None:
        authenticated_startup, _application, _provisioning, _runtime_inputs = (
            _compose_auth_startup()
        )
        other = compose_marketplace_authentication_runtime_inputs()

        with self.assertRaises(MarketplaceAgreementAssentStartupCompositionError):
            compose_marketplace_agreement_assent_startup(
                authenticated_startup=authenticated_startup,
                runtime_inputs=other,
                candidate_resolution=_candidate_resolution(),
                workflow=_workflow(),
                encode_signing_input=_encode,
                decode_signature=_decode,
            )

    def test_invalid_exact_types_fail_before_overlay_construction(self) -> None:
        authenticated_startup, _application, _provisioning, runtime_inputs = (
            _compose_auth_startup()
        )
        with self.assertRaises(MarketplaceAgreementAssentStartupCompositionError):
            compose_marketplace_agreement_assent_startup(
                authenticated_startup=object(),  # type: ignore[arg-type]
                runtime_inputs=runtime_inputs,
                candidate_resolution=_candidate_resolution(),
                workflow=_workflow(),
                encode_signing_input=_encode,
                decode_signature=_decode,
            )
        with self.assertRaises(MarketplaceAgreementAssentStartupCompositionError):
            compose_marketplace_agreement_assent_startup(
                authenticated_startup=authenticated_startup,
                runtime_inputs=runtime_inputs,
                candidate_resolution=object(),  # type: ignore[arg-type]
                workflow=_workflow(),
                encode_signing_input=_encode,
                decode_signature=_decode,
            )


if __name__ == "__main__":
    unittest.main()
