from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_launch import (
    build_marketplace_authenticated_loopback_launch_plan,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST
from marketplace.reference.auth_enrollment_launch_nonce_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticationEnrollmentLaunchNonce,
    MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError,
    build_reference_authentication_enrollment_launch_nonce,
)
from marketplace.reference.auth_enrollment_launch_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
    build_reference_authentication_enrollment_launch,
)
from marketplace.reference.auth_enrollment_nonce_authority_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
    build_reference_authentication_enrollment_nonce_authority,
)
from marketplace.reference.auth_enrollment_nonce_material_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
)
from tests.test_m17_5t_auth_startup_composition import _compose as _compose_authenticated
from tests.test_m17_6i_auth_enrollment_http import (
    AUTHORITY,
    LEASE_SECONDS,
    RecordingAttestor,
    RecordingPolicy,
)


MODULE = "marketplace.reference.auth_enrollment_launch_nonce_v1"
PORT = 18443
ERROR_MESSAGE = "reference authentication enrollment launch nonce composition failed"


def _inputs():
    startup, _application, _provisioning, _runtime_inputs = _compose_authenticated()
    authenticated_plan = build_marketplace_authenticated_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=PORT,
        startup=startup,
    )
    policy = RecordingPolicy()
    attestor = RecordingAttestor()
    return authenticated_plan, policy, attestor


def _build():
    authenticated_plan, policy, attestor = _inputs()
    result = build_reference_authentication_enrollment_launch_nonce(
        authenticated_plan=authenticated_plan,
        policy=policy,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return result, authenticated_plan, policy, attestor


class M176RReferenceAuthenticationEnrollmentLaunchNonceTests(unittest.TestCase):
    def test_profile_and_exact_q_to_o_graph_are_frozen(self) -> None:
        result, authenticated_plan, policy, attestor = _build()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_V1",
        )
        self.assertIs(
            type(result),
            MarketplaceReferenceAuthenticationEnrollmentLaunchNonce,
        )
        self.assertIs(result.authenticated_plan, authenticated_plan)
        self.assertIs(result.policy, policy)
        self.assertIs(result.attestor, attestor)
        self.assertEqual(result.authority, AUTHORITY)
        self.assertEqual(result.evidence_lease_seconds, LEASE_SECONDS)
        self.assertIs(
            type(result.nonce),
            MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
        )
        self.assertIs(
            type(result.nonce.material_source),
            MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
        )
        self.assertIs(
            type(result.nonce.nonce_authority),
            MarketplaceAuthenticationEnrollmentNonceAuthority,
        )
        self.assertIs(
            type(result.launch),
            MarketplaceReferenceAuthenticationEnrollmentLaunch,
        )
        self.assertIs(result.launch.authenticated_plan, authenticated_plan)
        self.assertIs(result.launch.nonce_authority, result.nonce.nonce_authority)
        self.assertIs(result.launch.policy, policy)
        self.assertIs(result.launch.attestor, attestor)
        self.assertEqual(result.launch.authority, AUTHORITY)
        self.assertEqual(result.launch.evidence_lease_seconds, LEASE_SECONDS)

    def test_selection_builds_exactly_one_q_then_one_o(self) -> None:
        authenticated_plan, policy, attestor = _inputs()

        with (
            patch(
                f"{MODULE}.build_reference_authentication_enrollment_nonce_authority",
                wraps=build_reference_authentication_enrollment_nonce_authority,
            ) as build_q,
            patch(
                f"{MODULE}.build_reference_authentication_enrollment_launch",
                wraps=build_reference_authentication_enrollment_launch,
            ) as build_o,
        ):
            result = build_reference_authentication_enrollment_launch_nonce(
                authenticated_plan=authenticated_plan,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        build_q.assert_called_once_with()
        build_o.assert_called_once_with(
            authenticated_plan=authenticated_plan,
            nonce_authority=result.nonce.nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=AUTHORITY,
            evidence_lease_seconds=LEASE_SECONDS,
        )

    def test_construction_consumes_no_entropy_nonce_policy_or_attestation(self) -> None:
        authenticated_plan, policy, attestor = _inputs()

        with (
            patch(
                "marketplace.reference.auth_enrollment_nonce_material_v1._token_bytes",
                side_effect=AssertionError("entropy consumed during composition"),
            ) as entropy,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "issue_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce issued during composition"),
            ) as issue,
            patch.object(
                MarketplaceAuthenticationEnrollmentNonceAuthority,
                "consume_authentication_enrollment_nonce",
                side_effect=AssertionError("nonce consumed during composition"),
            ) as consume,
        ):
            result = build_reference_authentication_enrollment_launch_nonce(
                authenticated_plan=authenticated_plan,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        entropy.assert_not_called()
        issue.assert_not_called()
        consume.assert_not_called()
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)
        self.assertEqual(result.nonce.nonce_authority._outstanding, {})
        self.assertEqual(result.nonce.nonce_authority._spent, {})

    def test_wrong_authenticated_plan_fails_stably_before_q_construction(self) -> None:
        policy = RecordingPolicy()
        attestor = RecordingAttestor()

        with (
            patch(
                f"{MODULE}.build_reference_authentication_enrollment_nonce_authority",
                side_effect=AssertionError("Q constructed for malformed plan"),
            ) as build_q,
            self.assertRaises(
                MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError
            ) as caught,
        ):
            build_reference_authentication_enrollment_launch_nonce(
                authenticated_plan=object(),  # type: ignore[arg-type]
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        build_q.assert_not_called()
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_cross_bound_nonce_and_launch_fail_stably(self) -> None:
        first, authenticated_plan, policy, attestor = _build()
        second, _authenticated_plan2, _policy2, _attestor2 = _build()

        with self.assertRaises(
            MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError
        ) as caught:
            MarketplaceReferenceAuthenticationEnrollmentLaunchNonce(
                authenticated_plan=authenticated_plan,
                policy=policy,
                attestor=attestor,
                authority=AUTHORITY,
                evidence_lease_seconds=LEASE_SECONDS,
                nonce=first.nonce,
                launch=second.launch,
            )

        self.assertEqual(str(caught.exception), ERROR_MESSAGE)


if __name__ == "__main__":
    unittest.main()
