from __future__ import annotations

import base64
import unittest

from marketplace.application.auth_enrollment_authority import (
    MarketplaceAuthenticationEnrollmentProposal,
)
from marketplace.application.auth_enrollment_policy import (
    AuthenticationEnrollmentPolicyError,
    PROFILE_NAME,
    issue_marketplace_authentication_enrollment_evidence_after_policy,
)
from marketplace.application.auth_verification_method_evidence import (
    decode_marketplace_authentication_verification_method_evidence_claims,
)


AUTHORITY = "https://authority.example/auth-enrollment"
PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
KEY_BYTES = bytes(range(32))
PAYLOAD = base64.urlsafe_b64encode(KEY_BYTES).rstrip(b"=").decode("ascii")
PUBLIC_KEY = "mkp1_" + PAYLOAD


def proposal() -> MarketplaceAuthenticationEnrollmentProposal:
    return MarketplaceAuthenticationEnrollmentProposal(
        principal=PRINCIPAL,
        verification_method=METHOD,
        public_key=PUBLIC_KEY,
    )


class RecordingPolicy:
    def __init__(self, result: object = True) -> None:
        self.result = result
        self.calls = 0
        self.kwargs = None

    def approve_authentication_enrollment(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return self.result


class RaisingPolicy:
    def __init__(self) -> None:
        self.calls = 0

    def approve_authentication_enrollment(self, **_kwargs):
        self.calls += 1
        raise RuntimeError("sensitive policy detail")


class RecordingAttestor:
    def __init__(self, *, raises: bool = False) -> None:
        self.calls = 0
        self.raises = raises

    def attest_authentication_enrollment(self, _transcript: bytes) -> bytes:
        self.calls += 1
        if self.raises:
            raise RuntimeError("sensitive attestor detail")
        return b"s" * 64


class M176FAuthenticationEnrollmentPolicyTests(unittest.TestCase):
    def test_profile_is_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_POLICY_V1",
        )

    def test_invalid_request_fails_before_policy_and_attestor(self) -> None:
        cases = (
            {"proposal": object()},
            {"authority": "relative"},
            {"issued_at": True},
            {"expires_at": 100},
            {"expires_at": 100 + 86401},
        )
        for changes in cases:
            policy = RecordingPolicy()
            attestor = RecordingAttestor()
            kwargs = {
                "proposal": proposal(),
                "authority": AUTHORITY,
                "issued_at": 100,
                "expires_at": 200,
                "policy": policy,
                "attestor": attestor,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(AuthenticationEnrollmentPolicyError):
                    issue_marketplace_authentication_enrollment_evidence_after_policy(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(policy.calls, 0)
                self.assertEqual(attestor.calls, 0)

    def test_policy_rejection_and_malformed_result_fail_before_attestor(self) -> None:
        for result in (False, 1, "yes", object()):
            policy = RecordingPolicy(result)
            attestor = RecordingAttestor()
            with self.subTest(result_type=type(result).__name__):
                with self.assertRaises(AuthenticationEnrollmentPolicyError):
                    issue_marketplace_authentication_enrollment_evidence_after_policy(
                        proposal=proposal(),
                        authority=AUTHORITY,
                        issued_at=100,
                        expires_at=200,
                        policy=policy,
                        attestor=attestor,
                    )
                self.assertEqual(policy.calls, 1)
                self.assertEqual(attestor.calls, 0)

    def test_policy_exception_is_non_reflective_and_attestor_is_not_called(self) -> None:
        policy = RaisingPolicy()
        attestor = RecordingAttestor()
        with self.assertRaises(AuthenticationEnrollmentPolicyError) as caught:
            issue_marketplace_authentication_enrollment_evidence_after_policy(
                proposal=proposal(),
                authority=AUTHORITY,
                issued_at=100,
                expires_at=200,
                policy=policy,
                attestor=attestor,
            )
        self.assertEqual(str(caught.exception), "authentication enrollment policy operation failed")
        self.assertNotIn("sensitive", str(caught.exception))
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 0)

    def test_approved_request_preserves_exact_values_and_issues_once(self) -> None:
        value = proposal()
        policy = RecordingPolicy(True)
        attestor = RecordingAttestor()
        envelope = issue_marketplace_authentication_enrollment_evidence_after_policy(
            proposal=value,
            authority=AUTHORITY,
            issued_at=100,
            expires_at=200,
            policy=policy,
            attestor=attestor,
        )

        self.assertEqual(policy.calls, 1)
        self.assertEqual(
            policy.kwargs,
            {
                "principal": PRINCIPAL,
                "verification_method": METHOD,
                "public_key": PUBLIC_KEY,
                "authority": AUTHORITY,
                "issued_at": 100,
                "expires_at": 200,
            },
        )
        self.assertEqual(attestor.calls, 1)
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            envelope.claims_json
        )
        self.assertEqual(claims.authority, AUTHORITY)
        self.assertEqual(claims.issued_at, 100)
        self.assertEqual(claims.expires_at, 200)
        self.assertEqual(len(claims.entries), 1)
        self.assertEqual(claims.entries[0].controller_principal, PRINCIPAL)
        self.assertEqual(claims.entries[0].verification_method, METHOD)
        self.assertEqual(claims.entries[0].public_key, KEY_BYTES)
        self.assertEqual(envelope.attestation, b"s" * 64)

    def test_approved_attestor_failure_is_normalized_after_one_policy_call(self) -> None:
        policy = RecordingPolicy(True)
        attestor = RecordingAttestor(raises=True)
        with self.assertRaises(AuthenticationEnrollmentPolicyError) as caught:
            issue_marketplace_authentication_enrollment_evidence_after_policy(
                proposal=proposal(),
                authority=AUTHORITY,
                issued_at=100,
                expires_at=200,
                policy=policy,
                attestor=attestor,
            )
        self.assertEqual(str(caught.exception), "authentication enrollment policy operation failed")
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)


if __name__ == "__main__":
    unittest.main()
