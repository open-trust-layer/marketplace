from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
import unittest

from marketplace.application.auth_verification_method_evidence import (
    AUTH_EVIDENCE_ATTESTATION_MAX_BYTES,
    AUTH_EVIDENCE_BUNDLE_TYPE,
    AUTH_EVIDENCE_BUNDLE_VERSION,
    AUTH_EVIDENCE_CLAIMS_MAX_BYTES,
    AUTH_EVIDENCE_MAX_ENTRIES,
    AUTH_EVIDENCE_MAX_LEASE_SECONDS,
    AUTH_EVIDENCE_PUBLIC_KEY_PREFIX,
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    PROFILE_NAME,
    VerifiedAuthenticationVerificationMethodEvidence,
    decode_marketplace_authentication_verification_method_evidence_claims,
    encode_marketplace_auth_verification_public_key,
    encode_marketplace_authentication_verification_method_evidence_claims,
    materialize_marketplace_authentication_verification_method_snapshot,
    parse_marketplace_auth_verification_public_key,
)


AUTHORITY = "https://authority.example/evidence"
PRINCIPAL = "did:example:alice"
OTHER_PRINCIPAL = "did:example:bob"
METHOD = "did:example:alice#key-1"
KEY = bytes(range(32))


def evidence_claim(
    *,
    method: str = METHOD,
    controller: str = PRINCIPAL,
    key: bytes = KEY,
    valid_from: int | None = None,
    valid_until: int | None = None,
) -> AuthenticationVerificationMethodEvidenceClaim:
    return AuthenticationVerificationMethodEvidenceClaim(
        verification_method=method,
        controller_principal=controller,
        public_key=key,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def evidence_claims(
    *,
    authority: str = AUTHORITY,
    issued_at: int = 100,
    expires_at: int = 200,
    entries: tuple[AuthenticationVerificationMethodEvidenceClaim, ...] | None = None,
) -> MarketplaceAuthenticationVerificationMethodEvidenceClaims:
    return MarketplaceAuthenticationVerificationMethodEvidenceClaims(
        authority=authority,
        issued_at=issued_at,
        expires_at=expires_at,
        entries=entries if entries is not None else (evidence_claim(),),
    )


def envelope_for(claims: MarketplaceAuthenticationVerificationMethodEvidenceClaims | None = None):
    raw = encode_marketplace_authentication_verification_method_evidence_claims(
        claims if claims is not None else evidence_claims()
    )
    return MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(raw, b"opaque-attestation")


class AcceptingVerifier:
    def __init__(self, *, accepted: bool = True, authority: str = AUTHORITY, digest: bytes | None = None):
        self.accepted = accepted
        self.authority = authority
        self.digest = digest
        self.calls = 0
        self.seen = None

    def verify_authentication_verification_method_evidence(self, envelope):
        self.calls += 1
        self.seen = envelope
        digest = self.digest if self.digest is not None else hashlib.sha256(envelope.claims_json).digest()
        return VerifiedAuthenticationVerificationMethodEvidence(digest, self.authority, self.accepted)


class RaisingVerifier:
    def __init__(self):
        self.calls = 0

    def verify_authentication_verification_method_evidence(self, _envelope):
        self.calls += 1
        raise RuntimeError("sensitive provider details")


class MalformedVerifier:
    def __init__(self):
        self.calls = 0

    def verify_authentication_verification_method_evidence(self, _envelope):
        self.calls += 1
        return object()


class M17AuthVerificationMethodEvidenceTests(unittest.TestCase):
    def test_profile_and_exact_bounds(self):
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_EVIDENCE_BUNDLE_V1")
        self.assertEqual(AUTH_EVIDENCE_BUNDLE_TYPE, "MarketplaceAuthenticationVerificationMethodEvidenceBundle")
        self.assertEqual(AUTH_EVIDENCE_BUNDLE_VERSION, 1)
        self.assertEqual(AUTH_EVIDENCE_CLAIMS_MAX_BYTES, 512 * 1024)
        self.assertEqual(AUTH_EVIDENCE_ATTESTATION_MAX_BYTES, 16 * 1024)
        self.assertEqual(AUTH_EVIDENCE_MAX_ENTRIES, 256)
        self.assertEqual(AUTH_EVIDENCE_MAX_LEASE_SECONDS, 86400)

    def test_public_key_carrier_is_exact_canonical_32_byte_base64url(self):
        encoded = encode_marketplace_auth_verification_public_key(KEY)
        self.assertTrue(encoded.startswith(AUTH_EVIDENCE_PUBLIC_KEY_PREFIX))
        self.assertEqual(len(encoded), 48)
        self.assertEqual(parse_marketplace_auth_verification_public_key(encoded), KEY)
        for invalid in (encoded + "=", encoded[:-1], "mkp2_" + encoded[5:], "mkp1_" + "*" * 43):
            with self.subTest(invalid=invalid[:12]):
                with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
                    parse_marketplace_auth_verification_public_key(invalid)

    def test_canonical_claims_round_trip_exactly(self):
        claims = evidence_claims(entries=(evidence_claim(valid_from=110, valid_until=190),))
        raw = encode_marketplace_authentication_verification_method_evidence_claims(claims)
        decoded = decode_marketplace_authentication_verification_method_evidence_claims(raw)
        self.assertEqual(decoded, claims)
        self.assertEqual(encode_marketplace_authentication_verification_method_evidence_claims(decoded), raw)
        self.assertNotIn(b" ", raw)
        self.assertNotIn(b"\n", raw)

    def test_noncanonical_duplicate_unknown_bom_nan_and_invalid_utf8_fail_closed(self):
        raw = encode_marketplace_authentication_verification_method_evidence_claims(evidence_claims())
        document = json.loads(raw)
        document["unexpected"] = True
        unknown = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        duplicate = raw.replace(
            b'"authority":"https://authority.example/evidence"',
            b'"authority":"https://authority.example/evidence","authority":"https://authority.example/evidence"',
            1,
        )
        noncanonical = raw.replace(b'{"authority"', b'{ "authority"', 1)
        nan = raw.replace(b'"version":1', b'"version":NaN', 1)
        for invalid in (b"\xef\xbb\xbf" + raw, unknown, duplicate, noncanonical, nan, b"\xff"):
            with self.subTest(prefix=invalid[:24]):
                with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
                    decode_marketplace_authentication_verification_method_evidence_claims(invalid)

    def test_entry_count_duplicate_method_and_uri_shape_are_atomic(self):
        full = tuple(evidence_claim(method=f"did:example:alice#key-{i}") for i in range(AUTH_EVIDENCE_MAX_ENTRIES))
        evidence_claims(entries=full)
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            evidence_claims(entries=())
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            evidence_claims(entries=full + (evidence_claim(method="did:example:overflow#key"),))
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            evidence_claims(entries=(evidence_claim(), evidence_claim(controller=OTHER_PRINCIPAL)))
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            evidence_claim(method="relative/key")

    def test_uri_shape_accepts_post_scheme_s_and_rejects_actual_whitespace(self):
        claim = evidence_claim(
            method="did:example:synthetic#key-1",
            controller="did:example:synthetic",
        )
        claims = evidence_claims(
            authority="https://synthetic.example/evidence",
            entries=(claim,),
        )
        raw = encode_marketplace_authentication_verification_method_evidence_claims(claims)
        self.assertEqual(decode_marketplace_authentication_verification_method_evidence_claims(raw), claims)

        for invalid in (
            "did:example:synthetic key",
            "did:example:synthetic\tkey",
            "https://synthetic.example/evidence path",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
                    evidence_claim(method=invalid)

    def test_bundle_lease_is_half_open_and_at_most_24_hours(self):
        evidence_claims(issued_at=100, expires_at=100 + AUTH_EVIDENCE_MAX_LEASE_SECONDS)
        for issued, expires in ((100, 100), (101, 100), (100, 100 + AUTH_EVIDENCE_MAX_LEASE_SECONDS + 1)):
            with self.subTest(issued=issued, expires=expires):
                with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
                    evidence_claims(issued_at=issued, expires_at=expires)
        for invalid in (True, -1, 1.5):
            with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
                evidence_claims(issued_at=invalid)  # type: ignore[arg-type]

    def test_envelope_bounds_and_frozen_state(self):
        envelope = envelope_for()
        with self.assertRaises(FrozenInstanceError):
            envelope.attestation = b"changed"  # type: ignore[misc]
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(b"x" * (AUTH_EVIDENCE_CLAIMS_MAX_BYTES + 1), b"a")
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(b"{}", b"")
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(b"{}", b"a" * (AUTH_EVIDENCE_ATTESTATION_MAX_BYTES + 1))

    def test_success_calls_verifier_once_on_exact_envelope_and_materializes_snapshot(self):
        envelope = envelope_for(evidence_claims(entries=(evidence_claim(valid_from=120, valid_until=180),)))
        verifier = AcceptingVerifier()
        snapshot = materialize_marketplace_authentication_verification_method_snapshot(
            envelope=envelope, trust_verifier=verifier, at_time=150
        )
        self.assertEqual(verifier.calls, 1)
        self.assertIs(verifier.seen, envelope)
        self.assertEqual(snapshot.verification_key_bytes(METHOD), KEY)
        self.assertFalse(snapshot.verify(principal=PRINCIPAL, verification_method=METHOD, at_time=119))
        self.assertTrue(snapshot.verify(principal=PRINCIPAL, verification_method=METHOD, at_time=120))
        self.assertTrue(snapshot.verify(principal=PRINCIPAL, verification_method=METHOD, at_time=179))
        self.assertFalse(snapshot.verify(principal=PRINCIPAL, verification_method=METHOD, at_time=180))

    def test_bundle_lease_caps_unbounded_entry_validity(self):
        verifier = AcceptingVerifier()
        snapshot = materialize_marketplace_authentication_verification_method_snapshot(
            envelope=envelope_for(evidence_claims(issued_at=100, expires_at=200)),
            trust_verifier=verifier,
            at_time=100,
        )
        self.assertTrue(snapshot.verify(principal=PRINCIPAL, verification_method=METHOD, at_time=199))
        self.assertFalse(snapshot.verify(principal=PRINCIPAL, verification_method=METHOD, at_time=200))

    def test_authority_never_becomes_controller(self):
        authority = "did:example:authority"
        claims = evidence_claims(authority=authority, entries=(evidence_claim(controller=OTHER_PRINCIPAL),))
        verifier = AcceptingVerifier(authority=authority)
        snapshot = materialize_marketplace_authentication_verification_method_snapshot(
            envelope=envelope_for(claims), trust_verifier=verifier, at_time=150
        )
        self.assertFalse(snapshot.verify(principal=authority, verification_method=METHOD, at_time=150))
        self.assertTrue(snapshot.verify(principal=OTHER_PRINCIPAL, verification_method=METHOD, at_time=150))

    def test_rejection_digest_authority_exception_and_malformed_result_fail_closed_once(self):
        cases = (
            AcceptingVerifier(accepted=False),
            AcceptingVerifier(digest=b"\x00" * 32),
            AcceptingVerifier(authority="https://other.example/evidence"),
            RaisingVerifier(),
            MalformedVerifier(),
        )
        for verifier in cases:
            with self.subTest(verifier=type(verifier).__name__):
                with self.assertRaises(AuthenticationVerificationMethodEvidenceError) as caught:
                    materialize_marketplace_authentication_verification_method_snapshot(
                        envelope=envelope_for(), trust_verifier=verifier, at_time=150
                    )
                self.assertEqual(verifier.calls, 1)
                self.assertNotIn(AUTHORITY, str(caught.exception))
                self.assertNotIn(METHOD, str(caught.exception))
                self.assertNotIn("sensitive", str(caught.exception))

    def test_stale_bundle_fails_closed_after_exactly_one_trust_decision(self):
        for at_time in (99, 200):
            verifier = AcceptingVerifier()
            with self.subTest(at_time=at_time):
                with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
                    materialize_marketplace_authentication_verification_method_snapshot(
                        envelope=envelope_for(), trust_verifier=verifier, at_time=at_time
                    )
                self.assertEqual(verifier.calls, 1)

    def test_empty_validity_intersection_rejects_whole_bundle(self):
        claims = evidence_claims(
            entries=(
                evidence_claim(method="did:example:alice#key-1"),
                evidence_claim(method="did:example:alice#key-2", valid_until=50),
            )
        )
        verifier = AcceptingVerifier()
        with self.assertRaises(AuthenticationVerificationMethodEvidenceError):
            materialize_marketplace_authentication_verification_method_snapshot(
                envelope=envelope_for(claims), trust_verifier=verifier, at_time=150
            )
        self.assertEqual(verifier.calls, 1)

    def test_parsing_alone_never_materializes_authentication_authority(self):
        claims = decode_marketplace_authentication_verification_method_evidence_claims(envelope_for().claims_json)
        self.assertIsInstance(claims, MarketplaceAuthenticationVerificationMethodEvidenceClaims)
        self.assertFalse(hasattr(claims, "verification_key_bytes"))
        self.assertFalse(hasattr(claims, "verify"))


if __name__ == "__main__":
    unittest.main()
