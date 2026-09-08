from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth_evidence_trust_ed25519 import (
    AUTH_EVIDENCE_TRUST_MAX_ANCHORS,
    AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES,
    AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX,
    AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION,
    AuthenticationEvidenceTrustAnchor,
    AuthenticationEvidenceTrustError,
    MarketplaceAuthenticationEvidenceTrustAnchorSnapshot,
    MarketplaceEd25519AuthenticationEvidenceTrustVerifier,
    PROFILE_NAME,
    build_marketplace_authentication_evidence_trust_transcript,
)
from marketplace.application.auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    encode_marketplace_authentication_verification_method_evidence_claims,
    materialize_marketplace_authentication_verification_method_snapshot,
)


RFC8032_SEED = bytes.fromhex(
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
)
RFC8032_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
FIXED_SIGNATURE = bytes.fromhex(
    "f8a4163fa99a1db9747328521b497539717b42566a59cb9eaa5751f4387d08e7"
    "c27defff4284697c1e1a407a1f2dee85a3e3e68591428ab397b047ed5c19480d"
)
AUTHORITY = "https://authority.example/auth"
METHOD = "did:example:alice#key-1"
PRINCIPAL = "did:example:alice"


def _claims(*, authority: str = AUTHORITY, controller: str = PRINCIPAL):
    return MarketplaceAuthenticationVerificationMethodEvidenceClaims(
        authority=authority,
        issued_at=100,
        expires_at=200,
        entries=(
            AuthenticationVerificationMethodEvidenceClaim(
                verification_method=METHOD,
                controller_principal=controller,
                public_key=bytes(range(32)),
                valid_from=110,
                valid_until=190,
            ),
        ),
    )


def _claims_json(*, authority: str = AUTHORITY, controller: str = PRINCIPAL) -> bytes:
    return encode_marketplace_authentication_verification_method_evidence_claims(
        _claims(authority=authority, controller=controller)
    )


def _private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(RFC8032_SEED)


def _signature(claims_json: bytes, authority: str) -> bytes:
    digest = hashlib.sha256(claims_json).digest()
    transcript = build_marketplace_authentication_evidence_trust_transcript(
        authority=authority,
        claims_sha256=digest,
    )
    return _private_key().sign(transcript)


def _snapshot(*anchors: AuthenticationEvidenceTrustAnchor):
    return MarketplaceAuthenticationEvidenceTrustAnchorSnapshot(list(anchors))


def _verifier(*anchors: AuthenticationEvidenceTrustAnchor):
    return MarketplaceEd25519AuthenticationEvidenceTrustVerifier(
        trust_anchors=_snapshot(*anchors)
    )


class M17AuthEvidenceTrustEd25519Tests(unittest.TestCase):
    def test_profile_and_frozen_transcript_vector(self):
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_EVIDENCE_ED25519_TRUST_V1")
        self.assertEqual(AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX, b"MARKETPLACE-AUTH-EVIDENCE")
        self.assertEqual(AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION, 1)
        self.assertEqual(AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES, 64)

        public_key = _private_key().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.assertEqual(public_key, RFC8032_PUBLIC_KEY)

        claims_json = _claims_json()
        digest = hashlib.sha256(claims_json).digest()
        self.assertEqual(
            digest.hex(),
            "8411822b8f5742acde82c78cc1a99ff36c3dbb4534214ea47e1e4061e5ae019d",
        )
        transcript = build_marketplace_authentication_evidence_trust_transcript(
            authority=AUTHORITY,
            claims_sha256=digest,
        )
        self.assertEqual(
            transcript.hex(),
            "4d41524b4554504c4143452d415554482d45564944454e43450001001e"
            "68747470733a2f2f617574686f726974792e6578616d706c652f61757468"
            "8411822b8f5742acde82c78cc1a99ff36c3dbb4534214ea47e1e4061e5ae019d",
        )
        self.assertEqual(_private_key().sign(transcript), FIXED_SIGNATURE)

    def test_anchor_snapshot_is_exact_bounded_and_immutable(self):
        anchor = AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY)
        anchors = [anchor]
        snapshot = MarketplaceAuthenticationEvidenceTrustAnchorSnapshot(anchors)
        anchors.clear()
        self.assertEqual(
            snapshot.authentication_evidence_trust_key_bytes(AUTHORITY),
            RFC8032_PUBLIC_KEY,
        )
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            snapshot._anchors = {}  # type: ignore[misc]
        with self.assertRaises(AuthenticationEvidenceTrustError):
            MarketplaceAuthenticationEvidenceTrustAnchorSnapshot([])
        with self.assertRaises(AuthenticationEvidenceTrustError):
            MarketplaceAuthenticationEvidenceTrustAnchorSnapshot(
                [AuthenticationEvidenceTrustAnchor(f"https://a.example/{i}", RFC8032_PUBLIC_KEY)
                 for i in range(AUTH_EVIDENCE_TRUST_MAX_ANCHORS + 1)]
            )
        with self.assertRaises(AuthenticationEvidenceTrustError):
            MarketplaceAuthenticationEvidenceTrustAnchorSnapshot([anchor, anchor])
        with self.assertRaises(AuthenticationEvidenceTrustError):
            AuthenticationEvidenceTrustAnchor(AUTHORITY, b"x" * 31)

    def test_authority_uri_rejects_whitespace_without_rejecting_letter_s(self):
        with self.assertRaises(AuthenticationEvidenceTrustError):
            AuthenticationEvidenceTrustAnchor(
                authority="https://authority.example/has space",
                public_key=RFC8032_PUBLIC_KEY,
            )

        anchor = AuthenticationEvidenceTrustAnchor(
            authority="https://authority.example/safe",
            public_key=RFC8032_PUBLIC_KEY,
        )
        self.assertEqual(anchor.authority, "https://authority.example/safe")

    def test_authority_lookup_is_exact_and_has_no_fallback(self):
        snapshot = _snapshot(AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY))
        self.assertEqual(
            snapshot.authentication_evidence_trust_key_bytes(AUTHORITY),
            RFC8032_PUBLIC_KEY,
        )
        for other in (
            "https://AUTHORITY.example/auth",
            AUTHORITY + "/",
            "https://authority.example/other",
        ):
            with self.assertRaises(AuthenticationEvidenceTrustError):
                snapshot.authentication_evidence_trust_key_bytes(other)

    def test_valid_attestation_verifies_and_materializes_one_coherent_k_snapshot(self):
        claims_json = _claims_json()
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=claims_json,
            attestation=FIXED_SIGNATURE,
        )
        verifier = _verifier(AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY))
        result = verifier.verify_authentication_verification_method_evidence(envelope)
        self.assertIs(result.accepted, True)
        self.assertEqual(result.authority, AUTHORITY)
        self.assertEqual(result.claims_sha256, hashlib.sha256(claims_json).digest())

        snapshot = materialize_marketplace_authentication_verification_method_snapshot(
            envelope=envelope,
            trust_verifier=verifier,
            at_time=150,
        )
        self.assertEqual(snapshot.verification_key_bytes(METHOD), bytes(range(32)))
        self.assertIs(
            snapshot.verify(
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=150,
            ),
            True,
        )
        self.assertIs(
            snapshot.verify(
                principal=PRINCIPAL,
                verification_method=METHOD,
                at_time=190,
            ),
            False,
        )

    def test_corrupted_signature_is_rejected_without_exception_reflection(self):
        corrupted = bytearray(FIXED_SIGNATURE)
        corrupted[-1] ^= 1
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=_claims_json(),
            attestation=bytes(corrupted),
        )
        verifier = _verifier(AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY))
        result = verifier.verify_authentication_verification_method_evidence(envelope)
        self.assertIs(result.accepted, False)
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            materialize_marketplace_authentication_verification_method_snapshot(
                envelope=envelope,
                trust_verifier=verifier,
                at_time=150,
            )

    def test_claims_substitution_changes_digest_bound_transcript(self):
        substituted = _claims_json(controller="did:example:mallory")
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=substituted,
            attestation=FIXED_SIGNATURE,
        )
        result = _verifier(
            AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY)
        ).verify_authentication_verification_method_evidence(envelope)
        self.assertIs(result.accepted, False)

    def test_authority_substitution_changes_anchor_selection_and_transcript(self):
        other = "https://other.example/auth"
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=_claims_json(authority=other),
            attestation=FIXED_SIGNATURE,
        )
        verifier = _verifier(
            AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY),
            AuthenticationEvidenceTrustAnchor(other, RFC8032_PUBLIC_KEY),
        )
        self.assertIs(
            verifier.verify_authentication_verification_method_evidence(envelope).accepted,
            False,
        )

    def test_unknown_authority_fails_closed_without_identifier_reflection(self):
        unknown = "https://unknown.example/auth"
        claims_json = _claims_json(authority=unknown)
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=claims_json,
            attestation=_signature(claims_json, unknown),
        )
        verifier = _verifier(AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY))
        with self.assertRaises(AuthenticationEvidenceTrustError) as caught:
            verifier.verify_authentication_verification_method_evidence(envelope)
        self.assertEqual(
            str(caught.exception),
            "authentication evidence trust verification failed",
        )
        self.assertNotIn(unknown, str(caught.exception))

    def test_malformed_attestation_and_inputs_fail_closed(self):
        verifier = _verifier(AuthenticationEvidenceTrustAnchor(AUTHORITY, RFC8032_PUBLIC_KEY))
        for signature in (b"x" * 63, b"x" * 65):
            envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
                claims_json=_claims_json(),
                attestation=signature,
            )
            with self.assertRaises(AuthenticationEvidenceTrustError):
                verifier.verify_authentication_verification_method_evidence(envelope)
        with self.assertRaises(AuthenticationEvidenceTrustError):
            verifier.verify_authentication_verification_method_evidence(object())  # type: ignore[arg-type]
        with self.assertRaises(AuthenticationEvidenceTrustError):
            build_marketplace_authentication_evidence_trust_transcript(
                authority=AUTHORITY,
                claims_sha256=b"x" * 31,
            )


if __name__ == "__main__":
    unittest.main()
