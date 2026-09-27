from __future__ import annotations

import base64
import hashlib
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityError,
    MarketplaceAuthenticationEnrollmentProposal,
    PROFILE_NAME,
    issue_marketplace_authentication_enrollment_evidence,
)
from marketplace.application.auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
    MarketplaceAuthenticationEvidenceTrustAnchorSnapshot,
    MarketplaceEd25519AuthenticationEvidenceTrustVerifier,
    build_marketplace_authentication_evidence_trust_transcript,
)
from marketplace.application.auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceError,
    decode_marketplace_authentication_verification_method_evidence_claims,
    materialize_marketplace_authentication_verification_method_snapshot,
)


AUTHORITY = "https://authority.example/auth-enrollment"
PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
OTHER_METHOD = "did:example:alice#key-2"
KEY_BYTES = bytes(range(32))
PAYLOAD = base64.urlsafe_b64encode(KEY_BYTES).rstrip(b"=").decode("ascii")
PUBLIC_KEY = "mkp1_" + PAYLOAD
RFC8032_SEED = bytes.fromhex(
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
)


class RecordingAttestor:
    def __init__(self, signature: bytes = b"s" * 64) -> None:
        self.signature = signature
        self.calls = 0
        self.transcript = None

    def attest_authentication_enrollment(self, transcript: bytes) -> bytes:
        self.calls += 1
        self.transcript = transcript
        return self.signature


class RaisingAttestor:
    def __init__(self) -> None:
        self.calls = 0

    def attest_authentication_enrollment(self, _transcript: bytes) -> bytes:
        self.calls += 1
        raise RuntimeError("sensitive signer detail")


class FixedEd25519Attestor:
    def __init__(self) -> None:
        self.private_key = Ed25519PrivateKey.from_private_bytes(RFC8032_SEED)
        self.calls = 0

    def attest_authentication_enrollment(self, transcript: bytes) -> bytes:
        self.calls += 1
        return self.private_key.sign(transcript)


def proposal(
    *,
    principal: str = PRINCIPAL,
    method: str = METHOD,
    public_key: str = PUBLIC_KEY,
) -> MarketplaceAuthenticationEnrollmentProposal:
    return MarketplaceAuthenticationEnrollmentProposal(
        principal=principal,
        verification_method=method,
        public_key=public_key,
    )


class M176EAuthenticationEnrollmentAuthorityTests(unittest.TestCase):
    def test_profile_is_exact(self) -> None:
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_AUTHORITY_V1")

    def test_proposal_preserves_exact_values_and_rejects_invalid_input(self) -> None:
        value = proposal()
        self.assertEqual(value.principal, PRINCIPAL)
        self.assertEqual(value.verification_method, METHOD)
        self.assertEqual(value.public_key, PUBLIC_KEY)
        for kwargs in (
            {"principal": "relative"},
            {"method": "relative"},
            {"public_key": PUBLIC_KEY + "="},
            {"public_key": "mkpk1_" + PAYLOAD},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(AuthenticationEnrollmentAuthorityError):
                    proposal(**kwargs)

    def test_issuance_creates_exact_one_entry_canonical_claims_and_calls_attestor_once(self) -> None:
        attestor = RecordingAttestor()
        envelope = issue_marketplace_authentication_enrollment_evidence(
            proposal=proposal(),
            authority=AUTHORITY,
            issued_at=100,
            expires_at=200,
            attestor=attestor,
        )
        self.assertEqual(attestor.calls, 1)
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            envelope.claims_json
        )
        self.assertEqual(claims.authority, AUTHORITY)
        self.assertEqual(claims.issued_at, 100)
        self.assertEqual(claims.expires_at, 200)
        self.assertEqual(len(claims.entries), 1)
        entry = claims.entries[0]
        self.assertEqual(entry.controller_principal, PRINCIPAL)
        self.assertEqual(entry.verification_method, METHOD)
        self.assertEqual(entry.public_key, KEY_BYTES)
        self.assertIsNone(entry.valid_from)
        self.assertIsNone(entry.valid_until)
        expected = build_marketplace_authentication_evidence_trust_transcript(
            authority=AUTHORITY,
            claims_sha256=hashlib.sha256(envelope.claims_json).digest(),
        )
        self.assertEqual(attestor.transcript, expected)
        self.assertEqual(envelope.attestation, b"s" * 64)

    def test_authority_and_lease_fail_before_attestor_call(self) -> None:
        for authority, issued_at, expires_at in (
            ("relative", 100, 200),
            (AUTHORITY, True, 200),
            (AUTHORITY, 100, 100),
            (AUTHORITY, 100, 100 + 86401),
        ):
            attestor = RecordingAttestor()
            with self.subTest(authority=authority, issued_at=issued_at, expires_at=expires_at):
                with self.assertRaises(AuthenticationEnrollmentAuthorityError):
                    issue_marketplace_authentication_enrollment_evidence(
                        proposal=proposal(),
                        authority=authority,
                        issued_at=issued_at,
                        expires_at=expires_at,
                        attestor=attestor,
                    )
                self.assertEqual(attestor.calls, 0)

    def test_attestor_failure_and_malformed_signature_fail_closed_once(self) -> None:
        raising = RaisingAttestor()
        with self.assertRaises(AuthenticationEnrollmentAuthorityError) as caught:
            issue_marketplace_authentication_enrollment_evidence(
                proposal=proposal(),
                authority=AUTHORITY,
                issued_at=100,
                expires_at=200,
                attestor=raising,
            )
        self.assertEqual(raising.calls, 1)
        self.assertNotIn("sensitive", str(caught.exception))

        for signature in (b"", b"x" * 63, b"x" * 65):
            attestor = RecordingAttestor(signature)
            with self.subTest(length=len(signature)):
                with self.assertRaises(AuthenticationEnrollmentAuthorityError):
                    issue_marketplace_authentication_enrollment_evidence(
                        proposal=proposal(),
                        authority=AUTHORITY,
                        issued_at=100,
                        expires_at=200,
                        attestor=attestor,
                    )
                self.assertEqual(attestor.calls, 1)

    def test_full_synthetic_issuance_verification_materialization_path(self) -> None:
        attestor = FixedEd25519Attestor()
        envelope = issue_marketplace_authentication_enrollment_evidence(
            proposal=proposal(),
            authority=AUTHORITY,
            issued_at=100,
            expires_at=200,
            attestor=attestor,
        )
        authority_public_key = attestor.private_key.public_key().public_bytes_raw()
        verifier = MarketplaceEd25519AuthenticationEvidenceTrustVerifier(
            trust_anchors=MarketplaceAuthenticationEvidenceTrustAnchorSnapshot(
                [AuthenticationEvidenceTrustAnchor(AUTHORITY, authority_public_key)]
            )
        )
        snapshot = materialize_marketplace_authentication_verification_method_snapshot(
            envelope=envelope,
            trust_verifier=verifier,
            at_time=150,
        )
        self.assertEqual(attestor.calls, 1)
        self.assertTrue(
            snapshot.verify(
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=150,
            )
        )

    def test_prior_attestation_cannot_be_reused_for_changed_proposal(self) -> None:
        signer = FixedEd25519Attestor()
        original = issue_marketplace_authentication_enrollment_evidence(
            proposal=proposal(),
            authority=AUTHORITY,
            issued_at=100,
            expires_at=200,
            attestor=signer,
        )
        replay = RecordingAttestor(original.attestation)
        changed = issue_marketplace_authentication_enrollment_evidence(
            proposal=proposal(method=OTHER_METHOD),
            authority=AUTHORITY,
            issued_at=100,
            expires_at=200,
            attestor=replay,
        )
        public_key = signer.private_key.public_key().public_bytes_raw()
        verifier = MarketplaceEd25519AuthenticationEvidenceTrustVerifier(
            trust_anchors=MarketplaceAuthenticationEvidenceTrustAnchorSnapshot(
                [AuthenticationEvidenceTrustAnchor(AUTHORITY, public_key)]
            )
        )
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            materialize_marketplace_authentication_verification_method_snapshot(
                envelope=changed,
                trust_verifier=verifier,
                at_time=150,
            )

    def test_authority_is_separate_from_controller_principal(self) -> None:
        envelope = issue_marketplace_authentication_enrollment_evidence(
            proposal=proposal(),
            authority=AUTHORITY,
            issued_at=100,
            expires_at=200,
            attestor=RecordingAttestor(),
        )
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            envelope.claims_json
        )
        self.assertNotEqual(claims.authority, claims.entries[0].controller_principal)
        self.assertEqual(claims.entries[0].controller_principal, PRINCIPAL)


if __name__ == "__main__":
    unittest.main()
