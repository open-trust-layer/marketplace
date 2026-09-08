from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from marketplace.application.auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
    AuthenticationEvidenceTrustError,
)
from marketplace.application.auth_trust_anchor_manifest import (
    AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS,
    AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES,
    AUTH_TRUST_ANCHOR_MANIFEST_TYPE,
    AUTH_TRUST_ANCHOR_MANIFEST_VERSION,
    AuthenticationTrustAnchorManifestError,
    MarketplaceAuthenticationEvidenceTrustAnchorManifest,
    PROFILE_NAME,
    decode_marketplace_authentication_trust_anchor_manifest,
    encode_marketplace_authentication_trust_anchor_manifest,
    materialize_marketplace_authentication_evidence_trust_anchor_snapshot,
)
from marketplace.application.auth_verification_method_evidence import (
    encode_marketplace_auth_verification_public_key,
)


AUTHORITY = "https://authority.example/auth"
PUBLIC_KEY = bytes(range(32))
PUBLIC_KEY_TEXT = encode_marketplace_auth_verification_public_key(PUBLIC_KEY)


def _manifest_bytes(
    *,
    authority: str = AUTHORITY,
    public_key_text: str = PUBLIC_KEY_TEXT,
) -> bytes:
    return (
        '{"anchors":[{"authority":"'
        + authority
        + '","publicKey":"'
        + public_key_text
        + '"}],"type":'
        + '"MarketplaceAuthenticationEvidenceTrustAnchorManifest",'
        + '"version":1}'
    ).encode("utf-8")


class M17AuthTrustAnchorManifestTests(unittest.TestCase):
    def test_profile_type_version_and_bounds_are_frozen(self):
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_TRUST_ANCHOR_MANIFEST_V1",
        )
        self.assertEqual(
            AUTH_TRUST_ANCHOR_MANIFEST_TYPE,
            "MarketplaceAuthenticationEvidenceTrustAnchorManifest",
        )
        self.assertEqual(AUTH_TRUST_ANCHOR_MANIFEST_VERSION, 1)
        self.assertEqual(AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES, 256 * 1024)
        self.assertEqual(AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS, 64)

    def test_canonical_manifest_round_trips_exactly(self):
        raw = _manifest_bytes()
        manifest = decode_marketplace_authentication_trust_anchor_manifest(raw)
        self.assertEqual(len(manifest.anchors), 1)
        self.assertEqual(manifest.anchors[0].authority, AUTHORITY)
        self.assertEqual(manifest.anchors[0].public_key, PUBLIC_KEY)
        self.assertEqual(
            encode_marketplace_authentication_trust_anchor_manifest(manifest),
            raw,
        )

    def test_noncanonical_json_is_rejected(self):
        canonical = _manifest_bytes().decode("utf-8")
        variants = (
            canonical.replace('{"anchors"', '{ "anchors"', 1),
            canonical.replace(',"type"', ', "type"', 1),
        )
        for raw in variants:
            with self.subTest(raw=raw):
                with self.assertRaises(AuthenticationTrustAnchorManifestError):
                    decode_marketplace_authentication_trust_anchor_manifest(
                        raw.encode("utf-8")
                    )

    def test_bom_duplicate_keys_unknown_keys_and_nonfinite_values_reject(self):
        cases = (
            b"\xef\xbb\xbf" + _manifest_bytes(),
            (
                '{"anchors":[{"authority":"'
                + AUTHORITY
                + '","authority":"'
                + AUTHORITY
                + '","publicKey":"'
                + PUBLIC_KEY_TEXT
                + '"}],"type":'
                + '"MarketplaceAuthenticationEvidenceTrustAnchorManifest",'
                + '"version":1}'
            ).encode("utf-8"),
            _manifest_bytes()[:-1] + b',"extra":1}',
            _manifest_bytes()[:-1] + b',"extra":NaN}',
        )
        for raw in cases:
            with self.subTest(raw=raw[:40]):
                with self.assertRaises(AuthenticationTrustAnchorManifestError):
                    decode_marketplace_authentication_trust_anchor_manifest(raw)

    def test_non_bytes_empty_and_oversized_input_reject(self):
        for raw in (
            bytearray(_manifest_bytes()),
            b"",
            b"x" * (AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES + 1),
        ):
            with self.subTest(kind=type(raw).__name__, size=len(raw)):
                with self.assertRaises(AuthenticationTrustAnchorManifestError):
                    decode_marketplace_authentication_trust_anchor_manifest(raw)

    def test_anchor_count_is_exactly_one_to_sixty_four(self):
        empty = (
            b'{"anchors":[],"type":'
            b'"MarketplaceAuthenticationEvidenceTrustAnchorManifest",'
            b'"version":1}'
        )
        with self.assertRaises(AuthenticationTrustAnchorManifestError):
            decode_marketplace_authentication_trust_anchor_manifest(empty)

        anchors = [
            AuthenticationEvidenceTrustAnchor(
                authority=f"https://authority.example/{index}",
                public_key=PUBLIC_KEY,
            )
            for index in range(AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS)
        ]
        manifest = MarketplaceAuthenticationEvidenceTrustAnchorManifest(
            anchors=tuple(anchors)
        )
        encoded = encode_marketplace_authentication_trust_anchor_manifest(manifest)
        self.assertEqual(
            len(
                decode_marketplace_authentication_trust_anchor_manifest(
                    encoded
                ).anchors
            ),
            AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS,
        )
        with self.assertRaises(AuthenticationTrustAnchorManifestError):
            MarketplaceAuthenticationEvidenceTrustAnchorManifest(
                anchors=tuple(
                    anchors
                    + [
                        AuthenticationEvidenceTrustAnchor(
                            authority="https://authority.example/overflow",
                            public_key=PUBLIC_KEY,
                        )
                    ]
                )
            )

    def test_duplicate_exact_authority_rejects_whole_manifest(self):
        anchor = AuthenticationEvidenceTrustAnchor(AUTHORITY, PUBLIC_KEY)
        with self.assertRaises(AuthenticationTrustAnchorManifestError):
            MarketplaceAuthenticationEvidenceTrustAnchorManifest(
                anchors=(anchor, anchor)
            )

    def test_authority_is_exact_and_whitespace_is_rejected(self):
        with self.assertRaises(AuthenticationTrustAnchorManifestError):
            decode_marketplace_authentication_trust_anchor_manifest(
                _manifest_bytes(authority="https://authority.example/has space")
            )
        safe = _manifest_bytes(authority="https://authority.example/safe")
        decoded = decode_marketplace_authentication_trust_anchor_manifest(safe)
        self.assertEqual(decoded.anchors[0].authority, "https://authority.example/safe")

    def test_public_key_must_use_exact_canonical_mkp1_carrier(self):
        malformed = (
            PUBLIC_KEY_TEXT[:-1] + "=",
            "mkp1_" + "A" * 42,
            "not-mkp1_" + PUBLIC_KEY_TEXT[5:],
        )
        for value in malformed:
            with self.subTest(value=value):
                with self.assertRaises(AuthenticationTrustAnchorManifestError):
                    decode_marketplace_authentication_trust_anchor_manifest(
                        _manifest_bytes(public_key_text=value)
                    )

    def test_any_malformed_anchor_rejects_atomically(self):
        raw = (
            '{"anchors":['
            '{"authority":"https://authority.example/one","publicKey":"'
            + PUBLIC_KEY_TEXT
            + '"},'
            '{"authority":"https://authority.example/two","publicKey":"mkp1_bad"}'
            '],"type":'
            '"MarketplaceAuthenticationEvidenceTrustAnchorManifest",'
            '"version":1}'
        ).encode("utf-8")
        with self.assertRaises(AuthenticationTrustAnchorManifestError):
            materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
                raw
            )

    def test_materialization_returns_existing_immutable_m17_5m_snapshot(self):
        raw = _manifest_bytes()
        snapshot = (
            materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
                raw
            )
        )
        self.assertEqual(
            snapshot.authentication_evidence_trust_key_bytes(AUTHORITY),
            PUBLIC_KEY,
        )
        with self.assertRaises(AuthenticationEvidenceTrustError):
            snapshot.authentication_evidence_trust_key_bytes(
                "https://authority.example/other"
            )
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            snapshot._anchors = {}  # type: ignore[misc]

    def test_exact_authority_lookup_does_not_normalize_or_fallback(self):
        snapshot = (
            materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
                _manifest_bytes()
            )
        )
        for other in (
            "https://AUTHORITY.example/auth",
            AUTHORITY + "/",
            "https://authority.example/other",
        ):
            with self.subTest(other=other):
                with self.assertRaises(AuthenticationEvidenceTrustError):
                    snapshot.authentication_evidence_trust_key_bytes(other)

    def test_manifest_value_is_frozen(self):
        manifest = decode_marketplace_authentication_trust_anchor_manifest(
            _manifest_bytes()
        )
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            manifest.anchors = ()  # type: ignore[misc]

    def test_errors_are_stable_and_do_not_reflect_manifest_data(self):
        secretish_authority = "https://private.example/do-not-reflect"
        with self.assertRaises(AuthenticationTrustAnchorManifestError) as caught:
            decode_marketplace_authentication_trust_anchor_manifest(
                _manifest_bytes(
                    authority=secretish_authority,
                    public_key_text="mkp1_bad",
                )
            )
        self.assertEqual(
            str(caught.exception),
            "authentication trust-anchor manifest is invalid or unavailable",
        )
        self.assertNotIn(secretish_authority, str(caught.exception))


if __name__ == "__main__":
    unittest.main()