from __future__ import annotations

import base64
import hashlib
import unittest

from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_enrollment_authority import (
    MarketplaceAuthenticationEnrollmentProposal,
)
from marketplace.application.auth_enrollment_coordination import (
    AUTH_ENROLLMENT_NONCE_BYTES,
    AuthenticationEnrollmentCoordinationError,
    PROFILE_NAME,
    coordinate_marketplace_authentication_enrollment,
)
from marketplace.application.auth_verification_method_evidence import (
    AUTH_EVIDENCE_MAX_LEASE_SECONDS,
    decode_marketplace_authentication_verification_method_evidence_claims,
)


AUTHORITY = "https://authority.example/auth-enrollment"
PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
OTHER_PRINCIPAL = "did:example:bob"
OTHER_METHOD = "did:example:bob#key-1"
KEY_BYTES = bytes(range(32))
PAYLOAD = base64.urlsafe_b64encode(KEY_BYTES).rstrip(b"=").decode("ascii")
PUBLIC_KEY = "mkp1_" + PAYLOAD
SESSION_TOKEN = b"t" * 32
NONCE = b"n" * AUTH_ENROLLMENT_NONCE_BYTES


class AllowBinding:
    def verify(self, **_kwargs) -> bool:
        return True


def authenticated_service() -> MarketplaceApplicationAuthService:
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    challenge = b"c" * 32
    auth.register_challenge(
        challenge=challenge,
        principal=PRINCIPAL,
        verification_method=METHOD,
        now=100,
    )
    attempt = auth.begin_challenge_attempt(challenge=challenge, now=100)
    proof = VerifiedAuthenticationProof(
        challenge_sha256=hashlib.sha256(challenge).digest(),
        domain=AUTH_PROOF_DOMAIN,
        proof_purpose=AUTH_PROOF_PURPOSE,
        verification_method=METHOD,
        cryptographically_valid=True,
    )
    auth.authenticate_challenge_attempt(
        attempt=attempt,
        proof=proof,
        session_token=SESSION_TOKEN,
        now=100,
    )
    return auth


def proposal(
    *,
    principal: str = PRINCIPAL,
    method: str = METHOD,
) -> MarketplaceAuthenticationEnrollmentProposal:
    return MarketplaceAuthenticationEnrollmentProposal(
        principal=principal,
        verification_method=method,
        public_key=PUBLIC_KEY,
    )


class RecordingReplayGuard:
    def __init__(self, result: object = True, *, raises: bool = False) -> None:
        self.result = result
        self.raises = raises
        self.calls = 0
        self.kwargs = None

    def consume_authentication_enrollment_nonce(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        if self.raises:
            raise RuntimeError("sensitive replay detail")
        return self.result


class OneShotReplayGuard:
    def __init__(self) -> None:
        self.consumed = False
        self.calls = 0

    def consume_authentication_enrollment_nonce(self, **_kwargs):
        self.calls += 1
        if self.consumed:
            return False
        self.consumed = True
        return True


class RecordingPolicy:
    def __init__(self, result: object = True) -> None:
        self.result = result
        self.calls = 0

    def approve_authentication_enrollment(self, **_kwargs):
        self.calls += 1
        return self.result


class RecordingAttestor:
    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.calls = 0

    def attest_authentication_enrollment(self, _transcript: bytes) -> bytes:
        self.calls += 1
        if self.raises:
            raise RuntimeError("sensitive attestor detail")
        return b"s" * 64


class M176GAuthenticationEnrollmentCoordinationTests(unittest.TestCase):
    def test_profile_and_nonce_bound_are_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_COORDINATION_V1",
        )
        self.assertEqual(AUTH_ENROLLMENT_NONCE_BYTES, 32)

    def test_invalid_static_inputs_fail_before_replay_policy_and_attestor(self) -> None:
        cases = (
            {"auth": object()},
            {"session_token": b"x" * 31},
            {"proposal": object()},
            {"nonce": b"x" * 31},
            {"now": True},
            {"authority": "relative"},
            {"lease_seconds": 0},
            {"lease_seconds": AUTH_EVIDENCE_MAX_LEASE_SECONDS + 1},
        )
        for changes in cases:
            replay = RecordingReplayGuard()
            policy = RecordingPolicy()
            attestor = RecordingAttestor()
            kwargs = {
                "auth": authenticated_service(),
                "session_token": SESSION_TOKEN,
                "proposal": proposal(),
                "nonce": NONCE,
                "now": 101,
                "authority": AUTHORITY,
                "lease_seconds": 600,
                "replay_guard": replay,
                "policy": policy,
                "attestor": attestor,
            }
            kwargs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(AuthenticationEnrollmentCoordinationError):
                    coordinate_marketplace_authentication_enrollment(
                        **kwargs  # type: ignore[arg-type]
                    )
                self.assertEqual(replay.calls, 0)
                self.assertEqual(policy.calls, 0)
                self.assertEqual(attestor.calls, 0)

    def test_session_principal_mismatch_fails_before_replay(self) -> None:
        replay = RecordingReplayGuard()
        policy = RecordingPolicy()
        attestor = RecordingAttestor()
        with self.assertRaises(AuthenticationEnrollmentCoordinationError):
            coordinate_marketplace_authentication_enrollment(
                auth=authenticated_service(),
                session_token=SESSION_TOKEN,
                proposal=proposal(principal=OTHER_PRINCIPAL, method=OTHER_METHOD),
                nonce=NONCE,
                now=101,
                authority=AUTHORITY,
                lease_seconds=600,
                replay_guard=replay,
                policy=policy,
                attestor=attestor,
            )
        self.assertEqual(replay.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_replay_failure_is_nonreflective_and_blocks_policy_and_attestor(self) -> None:
        for result in (False, 1, "yes"):
            replay = RecordingReplayGuard(result)
            policy = RecordingPolicy()
            attestor = RecordingAttestor()
            with self.subTest(result=result):
                with self.assertRaises(AuthenticationEnrollmentCoordinationError):
                    coordinate_marketplace_authentication_enrollment(
                        auth=authenticated_service(),
                        session_token=SESSION_TOKEN,
                        proposal=proposal(),
                        nonce=NONCE,
                        now=101,
                        authority=AUTHORITY,
                        lease_seconds=600,
                        replay_guard=replay,
                        policy=policy,
                        attestor=attestor,
                    )
                self.assertEqual(replay.calls, 1)
                self.assertEqual(policy.calls, 0)
                self.assertEqual(attestor.calls, 0)

        replay = RecordingReplayGuard(raises=True)
        with self.assertRaises(AuthenticationEnrollmentCoordinationError) as caught:
            coordinate_marketplace_authentication_enrollment(
                auth=authenticated_service(),
                session_token=SESSION_TOKEN,
                proposal=proposal(),
                nonce=NONCE,
                now=101,
                authority=AUTHORITY,
                lease_seconds=600,
                replay_guard=replay,
                policy=RecordingPolicy(),
                attestor=RecordingAttestor(),
            )
        self.assertEqual(str(caught.exception), "authentication enrollment coordination failed")
        self.assertNotIn("sensitive", str(caught.exception))

    def test_approved_path_preserves_exact_binding_and_lease(self) -> None:
        replay = RecordingReplayGuard()
        policy = RecordingPolicy()
        attestor = RecordingAttestor()
        envelope = coordinate_marketplace_authentication_enrollment(
            auth=authenticated_service(),
            session_token=SESSION_TOKEN,
            proposal=proposal(),
            nonce=NONCE,
            now=101,
            authority=AUTHORITY,
            lease_seconds=600,
            replay_guard=replay,
            policy=policy,
            attestor=attestor,
        )
        self.assertEqual(replay.calls, 1)
        self.assertEqual(
            replay.kwargs,
            {
                "nonce": NONCE,
                "principal": PRINCIPAL,
                "verification_method": METHOD,
                "public_key": PUBLIC_KEY,
                "authority": AUTHORITY,
                "issued_at": 101,
                "expires_at": 701,
            },
        )
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            envelope.claims_json
        )
        self.assertEqual(claims.authority, AUTHORITY)
        self.assertEqual(claims.issued_at, 101)
        self.assertEqual(claims.expires_at, 701)
        self.assertEqual(claims.entries[0].controller_principal, PRINCIPAL)
        self.assertEqual(claims.entries[0].verification_method, METHOD)
        self.assertEqual(claims.entries[0].public_key, KEY_BYTES)

    def test_policy_rejection_happens_after_nonce_is_burned(self) -> None:
        replay = OneShotReplayGuard()
        policy = RecordingPolicy(False)
        attestor = RecordingAttestor()
        with self.assertRaises(AuthenticationEnrollmentCoordinationError):
            coordinate_marketplace_authentication_enrollment(
                auth=authenticated_service(),
                session_token=SESSION_TOKEN,
                proposal=proposal(),
                nonce=NONCE,
                now=101,
                authority=AUTHORITY,
                lease_seconds=600,
                replay_guard=replay,
                policy=policy,
                attestor=attestor,
            )
        self.assertTrue(replay.consumed)
        self.assertEqual(replay.calls, 1)
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 0)

    def test_same_nonce_cannot_drive_policy_or_attestor_twice(self) -> None:
        auth = authenticated_service()
        replay = OneShotReplayGuard()
        policy = RecordingPolicy()
        attestor = RecordingAttestor()
        coordinate_marketplace_authentication_enrollment(
            auth=auth,
            session_token=SESSION_TOKEN,
            proposal=proposal(),
            nonce=NONCE,
            now=101,
            authority=AUTHORITY,
            lease_seconds=600,
            replay_guard=replay,
            policy=policy,
            attestor=attestor,
        )
        with self.assertRaises(AuthenticationEnrollmentCoordinationError):
            coordinate_marketplace_authentication_enrollment(
                auth=auth,
                session_token=SESSION_TOKEN,
                proposal=proposal(),
                nonce=NONCE,
                now=102,
                authority=AUTHORITY,
                lease_seconds=600,
                replay_guard=replay,
                policy=policy,
                attestor=attestor,
            )
        self.assertEqual(replay.calls, 2)
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)

    def test_attestor_failure_occurs_after_nonce_consumption(self) -> None:
        replay = OneShotReplayGuard()
        policy = RecordingPolicy()
        attestor = RecordingAttestor(raises=True)
        with self.assertRaises(AuthenticationEnrollmentCoordinationError):
            coordinate_marketplace_authentication_enrollment(
                auth=authenticated_service(),
                session_token=SESSION_TOKEN,
                proposal=proposal(),
                nonce=NONCE,
                now=101,
                authority=AUTHORITY,
                lease_seconds=600,
                replay_guard=replay,
                policy=policy,
                attestor=attestor,
            )
        self.assertTrue(replay.consumed)
        self.assertEqual(replay.calls, 1)
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)


if __name__ == "__main__":
    unittest.main()
