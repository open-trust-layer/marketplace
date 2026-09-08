from __future__ import annotations

import hashlib
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth import ApplicationAuthError
from marketplace.application.auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
    build_marketplace_authentication_evidence_trust_transcript,
)
from marketplace.application.auth_proof_profile import (
    AuthenticationProofSigningRequest,
    build_marketplace_auth_transcript,
    make_marketplace_authentication_proof,
)
from marketplace.application.auth_static_composition import (
    PROFILE_NAME,
    MarketplaceStaticAuthenticationCompositionError,
    compose_marketplace_static_authentication,
)
from marketplace.application.auth_trust_anchor_manifest import (
    MarketplaceAuthenticationEvidenceTrustAnchorManifest,
    encode_marketplace_authentication_trust_anchor_manifest,
)
from marketplace.application.auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceClaim,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    encode_marketplace_authentication_verification_method_evidence_claims,
)


AUTHORITY = "https://authority.example/auth"
OTHER_AUTHORITY = "https://other-authority.example/auth"
PRINCIPAL = "did:example:alice"
OTHER_PRINCIPAL = "did:example:bob"
METHOD = "did:example:alice#key-1"
AT_TIME = 1_000
CHALLENGE = b"C" * 32
SESSION_TOKEN = b"S" * 32
TRUST_PRIVATE_BYTES = bytes(range(1, 33))
AUTH_PRIVATE_BYTES = bytes(range(33, 65))
ALT_AUTH_PRIVATE_BYTES = bytes(range(65, 97))


def _private(raw: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(raw)


def _public(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _inputs(
    *,
    controller: str = PRINCIPAL,
    manifest_authority: str = AUTHORITY,
    evidence_authority: str = AUTHORITY,
    auth_public_key: bytes | None = None,
) -> tuple[bytes, MarketplaceAuthenticationVerificationMethodEvidenceEnvelope]:
    trust_private = _private(TRUST_PRIVATE_BYTES)
    auth_private = _private(AUTH_PRIVATE_BYTES)
    public_key = (
        auth_public_key if auth_public_key is not None else _public(auth_private)
    )

    manifest = MarketplaceAuthenticationEvidenceTrustAnchorManifest(
        anchors=(
            AuthenticationEvidenceTrustAnchor(
                authority=manifest_authority,
                public_key=_public(trust_private),
            ),
        )
    )
    manifest_bytes = encode_marketplace_authentication_trust_anchor_manifest(
        manifest
    )

    claims = MarketplaceAuthenticationVerificationMethodEvidenceClaims(
        authority=evidence_authority,
        issued_at=900,
        expires_at=1_100,
        entries=(
            AuthenticationVerificationMethodEvidenceClaim(
                verification_method=METHOD,
                controller_principal=controller,
                public_key=public_key,
                valid_from=900,
                valid_until=1_100,
            ),
        ),
    )
    claims_json = encode_marketplace_authentication_verification_method_evidence_claims(
        claims
    )
    transcript = build_marketplace_authentication_evidence_trust_transcript(
        authority=evidence_authority,
        claims_sha256=hashlib.sha256(claims_json).digest(),
    )
    envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
        claims_json=claims_json,
        attestation=trust_private.sign(transcript),
    )
    return manifest_bytes, envelope


def _proof_document(private_key: Ed25519PrivateKey) -> dict[str, object]:
    request = AuthenticationProofSigningRequest(
        verification_method=METHOD,
        challenge=CHALLENGE,
    )
    signature = private_key.sign(build_marketplace_auth_transcript(request))
    return make_marketplace_authentication_proof(request, signature).to_document()


class MarketplaceStaticAuthenticationCompositionTests(unittest.TestCase):
    def test_profile_and_exact_input_types(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_STATIC_COMPOSITION_V1",
        )
        manifest, envelope = _inputs()
        for bad_manifest in (bytearray(manifest), memoryview(manifest), None):
            with self.assertRaises(MarketplaceStaticAuthenticationCompositionError):
                compose_marketplace_static_authentication(
                    trust_anchor_manifest=bad_manifest,  # type: ignore[arg-type]
                    verification_method_evidence=envelope,
                    at_time=AT_TIME,
                )
        for bad_time in (True, -1, 1.5):
            with self.assertRaises(MarketplaceStaticAuthenticationCompositionError):
                compose_marketplace_static_authentication(
                    trust_anchor_manifest=manifest,
                    verification_method_evidence=envelope,
                    at_time=bad_time,  # type: ignore[arg-type]
                )

    def test_one_snapshot_is_shared_by_proof_and_binding(self) -> None:
        manifest, envelope = _inputs()
        composition = compose_marketplace_static_authentication(
            trust_anchor_manifest=manifest,
            verification_method_evidence=envelope,
            at_time=AT_TIME,
        )
        snapshot = composition.verification_method_snapshot
        self.assertIs(
            composition.proof_verifier._verification_key_bytes.__self__,
            snapshot,
        )
        self.assertIs(
            composition.auth_service._verify_principal_binding.__self__,
            snapshot,
        )

    def test_valid_synthetic_chain_authenticates_in_process(self) -> None:
        manifest, envelope = _inputs()
        composition = compose_marketplace_static_authentication(
            trust_anchor_manifest=manifest,
            verification_method_evidence=envelope,
            at_time=AT_TIME,
        )
        verified = composition.proof_verifier.verify(
            _proof_document(_private(AUTH_PRIVATE_BYTES))
        )
        self.assertTrue(verified.cryptographically_valid)

        composition.auth_service.register_challenge(
            challenge=CHALLENGE,
            principal=PRINCIPAL,
            verification_method=METHOD,
            now=AT_TIME,
        )
        attempt = composition.auth_service.begin_challenge_attempt(
            challenge=CHALLENGE,
            now=AT_TIME,
        )
        session = composition.auth_service.authenticate_challenge_attempt(
            attempt=attempt,
            proof=verified,
            session_token=SESSION_TOKEN,
            now=AT_TIME,
        )
        self.assertEqual(session.principal, PRINCIPAL)
        self.assertEqual(session.verification_method, METHOD)

    def test_explicit_controller_mismatch_rejects_valid_proof(self) -> None:
        manifest, envelope = _inputs(controller=OTHER_PRINCIPAL)
        composition = compose_marketplace_static_authentication(
            trust_anchor_manifest=manifest,
            verification_method_evidence=envelope,
            at_time=AT_TIME,
        )
        verified = composition.proof_verifier.verify(
            _proof_document(_private(AUTH_PRIVATE_BYTES))
        )
        self.assertTrue(verified.cryptographically_valid)
        composition.auth_service.register_challenge(
            challenge=CHALLENGE,
            principal=PRINCIPAL,
            verification_method=METHOD,
            now=AT_TIME,
        )
        attempt = composition.auth_service.begin_challenge_attempt(
            challenge=CHALLENGE,
            now=AT_TIME,
        )
        with self.assertRaises(ApplicationAuthError) as caught:
            composition.auth_service.authenticate_challenge_attempt(
                attempt=attempt,
                proof=verified,
                session_token=SESSION_TOKEN,
                now=AT_TIME,
            )
        self.assertEqual(caught.exception.code, "AUTH_PRINCIPAL_BINDING_REJECTED")

    def test_wrong_proof_key_fails_without_fallback(self) -> None:
        alternate_public = _public(_private(ALT_AUTH_PRIVATE_BYTES))
        manifest, envelope = _inputs(auth_public_key=alternate_public)
        composition = compose_marketplace_static_authentication(
            trust_anchor_manifest=manifest,
            verification_method_evidence=envelope,
            at_time=AT_TIME,
        )
        verified = composition.proof_verifier.verify(
            _proof_document(_private(AUTH_PRIVATE_BYTES))
        )
        self.assertFalse(verified.cryptographically_valid)
        composition.auth_service.register_challenge(
            challenge=CHALLENGE,
            principal=PRINCIPAL,
            verification_method=METHOD,
            now=AT_TIME,
        )
        attempt = composition.auth_service.begin_challenge_attempt(
            challenge=CHALLENGE,
            now=AT_TIME,
        )
        with self.assertRaises(ApplicationAuthError) as caught:
            composition.auth_service.authenticate_challenge_attempt(
                attempt=attempt,
                proof=verified,
                session_token=SESSION_TOKEN,
                now=AT_TIME,
            )
        self.assertEqual(caught.exception.code, "AUTH_PROOF_INVALID")

    def test_stale_evidence_fails_atomically(self) -> None:
        manifest, envelope = _inputs()
        with self.assertRaises(MarketplaceStaticAuthenticationCompositionError):
            compose_marketplace_static_authentication(
                trust_anchor_manifest=manifest,
                verification_method_evidence=envelope,
                at_time=1_100,
            )

    def test_unknown_authority_and_bad_attestation_fail_closed(self) -> None:
        manifest, envelope = _inputs(manifest_authority=OTHER_AUTHORITY)
        with self.assertRaises(MarketplaceStaticAuthenticationCompositionError):
            compose_marketplace_static_authentication(
                trust_anchor_manifest=manifest,
                verification_method_evidence=envelope,
                at_time=AT_TIME,
            )

        manifest, envelope = _inputs()
        bad_attestation = (
            bytes((envelope.attestation[0] ^ 1,)) + envelope.attestation[1:]
        )
        malformed = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=envelope.claims_json,
            attestation=bad_attestation,
        )
        with self.assertRaises(MarketplaceStaticAuthenticationCompositionError):
            compose_marketplace_static_authentication(
                trust_anchor_manifest=manifest,
                verification_method_evidence=malformed,
                at_time=AT_TIME,
            )

    def test_noncanonical_manifest_fails_closed(self) -> None:
        manifest, envelope = _inputs()
        with self.assertRaises(MarketplaceStaticAuthenticationCompositionError):
            compose_marketplace_static_authentication(
                trust_anchor_manifest=manifest + b"\n",
                verification_method_evidence=envelope,
                at_time=AT_TIME,
            )


if __name__ == "__main__":
    unittest.main()
