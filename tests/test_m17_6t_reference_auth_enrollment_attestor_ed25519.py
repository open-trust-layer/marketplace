from __future__ import annotations

import hashlib
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth_evidence_trust_ed25519 import (
    AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX,
    AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION,
    build_marketplace_authentication_evidence_trust_transcript,
)
from marketplace.reference.auth_enrollment_attestor_ed25519_v1 import (
    PROFILE_NAME,
    REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES,
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
    MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError,
)


PRIVATE_KEY = bytes(range(32))
AUTHORITY = "https://authority.example/enrollment"
CLAIMS_SHA256 = hashlib.sha256(b"synthetic enrollment claims").digest()
ERROR_MESSAGE = "reference authentication enrollment Ed25519 attestor failed"


def _transcript() -> bytes:
    return build_marketplace_authentication_evidence_trust_transcript(
        authority=AUTHORITY,
        claims_sha256=CLAIMS_SHA256,
    )


class RecordingPrivateKey:
    def __init__(self, result: object = b"\x5a" * 64, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[bytes] = []

    def sign(self, data: bytes) -> object:
        self.calls.append(data)
        if self.error is not None:
            raise self.error
        return self.result


class M176TReferenceAuthenticationEnrollmentEd25519AttestorTests(unittest.TestCase):
    def test_profile_key_size_and_valid_signature_are_frozen(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_ATTESTOR_V1",
        )
        self.assertEqual(REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES, 32)

        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=PRIVATE_KEY,
        )
        transcript = _transcript()
        signature = attestor.attest_authentication_enrollment(transcript)

        self.assertIs(type(signature), bytes)
        self.assertEqual(len(signature), 64)
        public_key = Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY).public_key()
        public_key.verify(signature, transcript)

    def test_constructor_requires_exact_32_byte_bytes_key(self) -> None:
        cases = (
            b"",
            b"x" * 31,
            b"x" * 33,
            bytearray(b"x" * 32),
            object(),
        )
        for value in cases:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError
                ) as caught:
                    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
                        private_key_bytes=value,  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_valid_transcript_is_signed_exactly_once_without_retry(self) -> None:
        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=PRIVATE_KEY,
        )
        signer = RecordingPrivateKey()
        attestor._private_key = signer  # type: ignore[assignment]
        transcript = _transcript()

        signature = attestor.attest_authentication_enrollment(transcript)

        self.assertEqual(signature, b"\x5a" * 64)
        self.assertEqual(signer.calls, [transcript])

    def test_invalid_transcripts_fail_before_signing(self) -> None:
        valid = _transcript()
        prefix_length = len(AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX)
        header_length = prefix_length + 4

        wrong_prefix = b"X" + valid[1:]
        wrong_separator = (
            valid[:prefix_length] + b"\x01" + valid[prefix_length + 1:]
        )
        wrong_version = (
            valid[:prefix_length + 1]
            + bytes(((AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION + 1) % 256,))
            + valid[prefix_length + 2:]
        )
        zero_authority = (
            valid[:prefix_length + 2]
            + b"\x00\x00"
            + valid[header_length:]
        )
        bad_utf8 = bytearray(valid)
        bad_utf8[header_length] = 0xFF
        cases = (
            bytearray(valid),
            valid[:-1],
            valid + b"\x00",
            wrong_prefix,
            wrong_separator,
            wrong_version,
            zero_authority,
            bytes(bad_utf8),
        )

        for value in cases:
            with self.subTest(value_type=type(value).__name__, size=len(value)):
                attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
                    private_key_bytes=PRIVATE_KEY,
                )
                signer = RecordingPrivateKey()
                attestor._private_key = signer  # type: ignore[assignment]
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError
                ) as caught:
                    attestor.attest_authentication_enrollment(
                        value  # type: ignore[arg-type]
                    )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertEqual(signer.calls, [])

    def test_signer_failure_and_malformed_signature_fail_stably(self) -> None:
        cases = (
            RecordingPrivateKey(result=b"x" * 63),
            RecordingPrivateKey(result=bytearray(b"x" * 64)),
            RecordingPrivateKey(error=RuntimeError("provider detail")),
        )
        for signer in cases:
            with self.subTest(result_type=type(signer.result).__name__):
                attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
                    private_key_bytes=PRIVATE_KEY,
                )
                attestor._private_key = signer  # type: ignore[assignment]
                with self.assertRaises(
                    MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError
                ) as caught:
                    attestor.attest_authentication_enrollment(_transcript())
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertEqual(len(signer.calls), 1)

    def test_public_surface_has_no_generic_sign_or_raw_private_key_export(self) -> None:
        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=PRIVATE_KEY,
        )
        self.assertFalse(hasattr(attestor, "sign"))
        self.assertFalse(hasattr(attestor, "private_key_bytes"))
        self.assertFalse(hasattr(attestor, "_private_key_bytes"))


if __name__ == "__main__":
    unittest.main()
