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
from marketplace.reference.auth_enrollment_launch_policy_nonce_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce,
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError,
    build_reference_authentication_enrollment_launch_policy_nonce,
)
from marketplace.reference.auth_enrollment_launch_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
    build_reference_authentication_enrollment_launch as _build_o,
)
from marketplace.reference.auth_enrollment_nonce_authority_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
    build_reference_authentication_enrollment_nonce_authority as _build_q,
)
from tests.test_m17_6i_auth_enrollment_http import LEASE_SECONDS
from tests.test_m17_6o_reference_auth_enrollment_launch import _inputs as _o_inputs
from tests.test_m17_6r_reference_auth_enrollment_approval_policy import (
    AUTHORITY,
    binding,
)


MODULE = "marketplace.reference.auth_enrollment_launch_policy_nonce_v1"
ERROR_MESSAGE = (
    "reference authentication enrollment launch policy nonce composition failed"
)


def _inputs():
    authenticated, _source, _old_nonce, _old_policy, attestor = _o_inputs()
    bindings = (binding(),)
    return authenticated, bindings, attestor


def _build():
    authenticated, bindings, attestor = _inputs()
    result = build_reference_authentication_enrollment_launch_policy_nonce(
        authenticated_plan=authenticated,
        bindings=bindings,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return result, authenticated, bindings, attestor


class M176SReferenceAuthenticationEnrollmentLaunchPolicyNonceTests(
    unittest.TestCase
):
    def test_profile_and_exact_q_r_to_o_graph(self) -> None:
        result, authenticated, bindings, attestor = _build()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce,
        )
        self.assertIs(
            type(result.nonce),
            MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
        )
        self.assertIs(
            type(result.policy),
            MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
        )
        self.assertIs(
            type(result.launch),
            MarketplaceReferenceAuthenticationEnrollmentLaunch,
        )
        self.assertIs(result.authenticated_plan, authenticated)
        self.assertIs(result.bindings, bindings)
        self.assertIs(result.policy.bindings, bindings)
        self.assertIs(result.attestor, attestor)
        self.assertEqual(result.authority, AUTHORITY)
        self.assertEqual(result.evidence_lease_seconds, LEASE_SECONDS)
        self.assertIs(result.launch.authenticated_plan, authenticated)
        self.assertIs(result.launch.nonce_authority, result.nonce.nonce_authority)
        self.assertIs(result.launch.policy, result.policy)
        self.assertIs(result.launch.attestor, attestor)
        self.assertEqual(result.launch.authority, AUTHORITY)
        self.assertEqual(result.launch.evidence_lease_seconds, LEASE_SECONDS)
        self.assertIs(
            result.nonce.nonce_authority._nonce_bytes.__self__,
            result.nonce.material_source,
        )
        self.assertEqual(result.nonce.nonce_authority._outstanding, {})
        self.assertEqual(result.nonce.nonce_authority._spent, {})

    def test_builder_constructs_q_once_and_o_once_with_exact_policy_and_nonce(self) -> None:
        authenticated, bindings, attestor = _inputs()

        with (
            patch(
                f"{MODULE}.build_reference_authentication_enrollment_nonce_authority",
                wraps=_build_q,
            ) as build_q,
            patch(
                f"{MODULE}.build_reference_authentication_enrollment_launch",
                wraps=_build_o,
            ) as build_o,
        ):
            result = build_reference_authentication_enrollment_launch_policy_nonce(
                authenticated_plan=authenticated,
                bindings=bindings,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(build_q.call_count, 1)
        self.assertEqual(build_o.call_count, 1)
        self.assertIs(
            build_o.call_args.kwargs["nonce_authority"],
            result.nonce.nonce_authority,
        )
        self.assertIs(build_o.call_args.kwargs["policy"], result.policy)
        self.assertIs(build_o.call_args.kwargs["authenticated_plan"], authenticated)
        self.assertIs(build_o.call_args.kwargs["attestor"], attestor)
        self.assertIs(result.policy.bindings, bindings)

    def test_construction_consumes_nothing_and_keeps_replay_state_empty(self) -> None:
        authenticated, bindings, attestor = _inputs()

        with (
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
            result = build_reference_authentication_enrollment_launch_policy_nonce(
                authenticated_plan=authenticated,
                bindings=bindings,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        entropy.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        decide.assert_not_called()
        request.assert_not_called()
        runtime.assert_not_called()
        provider.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(attestor.calls, 0)
        self.assertEqual(result.nonce.nonce_authority._outstanding, {})
        self.assertEqual(result.nonce.nonce_authority._spent, {})

    def test_invalid_bindings_fail_with_stable_nonreflective_error(self) -> None:
        authenticated, _bindings, attestor = _inputs()
        for bindings in ((), [binding()]):
            with self.subTest(kind=type(bindings).__name__):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError
                ) as caught:
                    build_reference_authentication_enrollment_launch_policy_nonce(
                        authenticated_plan=authenticated,
                        bindings=bindings,  # type: ignore[arg-type]
                        attestor=attestor,
                        authority=AUTHORITY,
                        evidence_lease_seconds=LEASE_SECONDS,
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_dependency_failure_is_stable(self) -> None:
        authenticated, bindings, attestor = _inputs()
        with patch(
            f"{MODULE}.build_reference_authentication_enrollment_nonce_authority",
            side_effect=RuntimeError("provider detail"),
        ):
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError
            ) as caught:
                build_reference_authentication_enrollment_launch_policy_nonce(
                    authenticated_plan=authenticated,
                    bindings=bindings,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
