from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.reference.auth_enrollment_launch_nonce_authority_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthority,
    MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError,
    build_reference_authentication_enrollment_launch_nonce_authority,
)
from marketplace.reference.auth_enrollment_launch_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
    build_reference_authentication_enrollment_launch as _build_o,
)
from marketplace.reference.auth_enrollment_nonce_authority_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
    build_reference_authentication_enrollment_nonce_authority as _build_q,
)
from tests.test_m17_6i_auth_enrollment_http import AUTHORITY, LEASE_SECONDS
from tests.test_m17_6o_reference_auth_enrollment_launch import _inputs as _o_inputs


MODULE = "marketplace.reference.auth_enrollment_launch_nonce_authority_v1"
ERROR_MESSAGE = (
    "reference authentication enrollment launch nonce authority composition failed"
)


def _inputs():
    authenticated, _source, _nonce_authority, policy, attestor = _o_inputs()
    return authenticated, policy, attestor


def _build():
    authenticated, policy, attestor = _inputs()
    result = build_reference_authentication_enrollment_launch_nonce_authority(
        authenticated_plan=authenticated,
        policy=policy,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return result, authenticated, policy, attestor


class M176RReferenceAuthenticationEnrollmentLaunchNonceAuthorityTests(unittest.TestCase):
    def test_profile_and_exact_q_to_o_graph(self) -> None:
        result, authenticated, policy, attestor = _build()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_AUTHORITY_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthority,
        )
        self.assertIs(
            type(result.nonce),
            MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
        )
        self.assertIs(
            type(result.launch),
            MarketplaceReferenceAuthenticationEnrollmentLaunch,
        )
        self.assertIs(result.launch.nonce_authority, result.nonce.nonce_authority)
        self.assertIs(
            result.nonce.nonce_authority._nonce_bytes.__self__,
            result.nonce.material_source,
        )
        self.assertEqual(result.nonce.nonce_authority._outstanding, {})
        self.assertEqual(result.nonce.nonce_authority._spent, {})
        self.assertIs(result.launch.authenticated_plan, authenticated)
        self.assertIs(result.launch.policy, policy)
        self.assertIs(result.launch.attestor, attestor)
        self.assertEqual(result.launch.authority, AUTHORITY)
        self.assertEqual(result.launch.evidence_lease_seconds, LEASE_SECONDS)

    def test_builder_constructs_q_once_and_o_once_with_exact_nonce_authority(self) -> None:
        authenticated, policy, attestor = _inputs()

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
            result = build_reference_authentication_enrollment_launch_nonce_authority(
                authenticated_plan=authenticated,
                policy=policy,
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
        self.assertIs(build_o.call_args.kwargs["authenticated_plan"], authenticated)
        self.assertIs(build_o.call_args.kwargs["policy"], policy)
        self.assertIs(build_o.call_args.kwargs["attestor"], attestor)

    def test_construction_consumes_no_entropy_nonce_policy_attestation_or_runtime(self) -> None:
        authenticated, policy, attestor = _inputs()

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
            result = build_reference_authentication_enrollment_launch_nonce_authority(
                authenticated_plan=authenticated,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertIs(result.launch.nonce_authority, result.nonce.nonce_authority)
        entropy.assert_not_called()
        issue_nonce.assert_not_called()
        consume_nonce.assert_not_called()
        request.assert_not_called()
        runtime.assert_not_called()
        provider.assert_not_called()
        socket.assert_not_called()
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_dependency_failure_is_stable_and_non_reflective(self) -> None:
        authenticated, policy, attestor = _inputs()
        with patch(
            f"{MODULE}.build_reference_authentication_enrollment_nonce_authority",
            side_effect=RuntimeError("provider detail"),
        ):
            with self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError
            ) as caught:
                build_reference_authentication_enrollment_launch_nonce_authority(
                    authenticated_plan=authenticated,
                    policy=policy,
                    attestor=attestor,
                    authority=AUTHORITY,
                    evidence_lease_seconds=LEASE_SECONDS,
                )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("provider detail", str(caught.exception))

    def test_invalid_authenticated_plan_fails_stably(self) -> None:
        _authenticated, policy, attestor = _inputs()
        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError
        ) as caught:
            build_reference_authentication_enrollment_launch_nonce_authority(
                authenticated_plan=object(),  # type: ignore[arg-type]
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)


if __name__ == "__main__":
    unittest.main()
