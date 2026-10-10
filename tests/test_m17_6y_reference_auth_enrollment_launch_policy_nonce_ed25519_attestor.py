from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.reference.auth_enrollment_approval_policy_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
)
from marketplace.reference.auth_enrollment_attestor_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_ed25519_attestor_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError,
    build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)
from marketplace.reference.auth_enrollment_launch_policy_nonce_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce,
    build_reference_authentication_enrollment_launch_policy_nonce as _build_s,
)
from tests.test_m17_6i_auth_enrollment_http import LEASE_SECONDS
from tests.test_m17_6o_reference_auth_enrollment_launch import _inputs as _o_inputs
from tests.test_m17_6r_reference_auth_enrollment_approval_policy import (
    AUTHORITY,
    binding,
)


MODULE = (
    "marketplace.reference."
    "auth_enrollment_launch_policy_nonce_ed25519_attestor_v1"
)
PRIVATE_KEY = bytes(range(32))
ERROR_MESSAGE = (
    "reference authentication enrollment existing Ed25519 attestor "
    "composition failed"
)


def _inputs():
    authenticated, _source, _old_nonce, _old_policy, _old_attestor = _o_inputs()
    return authenticated, (binding(),)


def _attestor():
    return MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
        private_key_bytes=PRIVATE_KEY,
    )


class M176YReferenceAuthenticationEnrollmentExistingEd25519AttestorTests(
    unittest.TestCase
):
    def test_profile_and_exact_existing_t_to_s_to_u_graph(self) -> None:
        authenticated, bindings = _inputs()
        attestor = _attestor()

        result = (
            build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                authenticated_plan=authenticated,
                bindings=bindings,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
            "LAUNCH_POLICY_NONCE_ED25519_ATTESTOR_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
        )
        self.assertIs(
            type(result.launch),
            MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce,
        )
        self.assertIs(result.authenticated_plan, authenticated)
        self.assertIs(result.bindings, bindings)
        self.assertIs(result.attestor, attestor)
        self.assertIs(result.launch.authenticated_plan, authenticated)
        self.assertIs(result.launch.bindings, bindings)
        self.assertIs(result.launch.attestor, attestor)
        self.assertIs(result.launch.launch.attestor, attestor)
        self.assertEqual(result.authority, AUTHORITY)
        self.assertEqual(result.launch.authority, AUTHORITY)
        self.assertEqual(result.evidence_lease_seconds, LEASE_SECONDS)
        self.assertFalse(hasattr(result, "private_key_bytes"))
        self.assertFalse(hasattr(result, "_private_key_bytes"))

    def test_builder_calls_s_once_with_exact_caller_attestor(self) -> None:
        authenticated, bindings = _inputs()
        attestor = _attestor()

        with patch(
            f"{MODULE}.build_reference_authentication_enrollment_launch_policy_nonce",
            wraps=_build_s,
        ) as build_s:
            result = (
                build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                    authenticated_plan=authenticated,
                    bindings=bindings,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
            )

        self.assertEqual(build_s.call_count, 1)
        self.assertIs(build_s.call_args.kwargs["authenticated_plan"], authenticated)
        self.assertIs(build_s.call_args.kwargs["bindings"], bindings)
        self.assertIs(build_s.call_args.kwargs["attestor"], attestor)
        self.assertEqual(build_s.call_args.kwargs["authority"], AUTHORITY)
        self.assertEqual(
            build_s.call_args.kwargs["evidence_lease_seconds"],
            LEASE_SECONDS,
        )
        self.assertIs(result.attestor, attestor)

    def test_wrong_attestor_type_fails_before_s(self) -> None:
        authenticated, bindings = _inputs()

        with (
            patch(
                f"{MODULE}.build_reference_authentication_enrollment_launch_policy_nonce"
            ) as build_s,
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError
            ) as caught,
        ):
            build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                authenticated_plan=authenticated,
                bindings=bindings,
                attestor=object(),  # type: ignore[arg-type]
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        build_s.assert_not_called()

    def test_construction_does_not_consume_key_or_enrollment_authority(self) -> None:
        authenticated, bindings = _inputs()
        attestor = _attestor()

        with (
            patch.object(
                MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
                "attest_authentication_enrollment",
                side_effect=AssertionError("attestation used"),
            ) as attest,
            patch(
                "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
                side_effect=AssertionError("entropy consumed"),
            ) as entropy,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "issue_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce issued"),
            ) as issue_nonce,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "consume_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce consumed"),
            ) as consume_nonce,
            patch.object(
                MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
                "approve_authentication_enrollment",
                side_effect=AssertionError("policy decision"),
            ) as decide,
            patch.object(
                MarketplaceSessionEstablishmentAsgiHttpAdapter,
                "__call__",
                side_effect=AssertionError("request handled"),
            ) as request,
            patch(
                "marketplace.application.auth_enrollment_runtime_server."
                "run_marketplace_authentication_enrollment_foreground",
                side_effect=AssertionError("runtime executed"),
            ) as runtime,
            patch(
                "marketplace.application.uvicorn_provider."
                "UvicornLoopbackServerProvider.run",
                side_effect=AssertionError("provider invoked"),
            ) as provider,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
        ):
            result = (
                build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                    authenticated_plan=authenticated,
                    bindings=bindings,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
            )

        attest.assert_not_called()
        entropy.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        decide.assert_not_called()
        request.assert_not_called()
        runtime.assert_not_called()
        provider.assert_not_called()
        socket.assert_not_called()
        self.assertIs(result.attestor, attestor)
        self.assertEqual(result.launch.nonce.nonce_authority._outstanding, {})
        self.assertEqual(result.launch.nonce.nonce_authority._spent, {})

    def test_s_failure_collapses_to_y_error(self) -> None:
        authenticated, bindings = _inputs()
        attestor = _attestor()

        with patch(
            f"{MODULE}.build_reference_authentication_enrollment_launch_policy_nonce",
            side_effect=RuntimeError("nested composition detail"),
        ):
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError
            ) as caught:
                build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                    authenticated_plan=authenticated,
                    bindings=bindings,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("nested composition detail", str(caught.exception))

    def test_u_result_construction_failure_collapses_to_y_error(self) -> None:
        authenticated, bindings = _inputs()
        attestor = _attestor()

        with patch(
            f"{MODULE}.MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519",
            side_effect=RuntimeError("nested U detail"),
        ):
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError
            ) as caught:
                build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                    authenticated_plan=authenticated,
                    bindings=bindings,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("nested U detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
