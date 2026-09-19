from __future__ import annotations

import unittest

from olp.transport import encode_ojve

from marketplace.reference.agreement_assent_http_v1 import (
    AgreementAssentHttpTransportError,
    decode_agreement_assent_signature,
    encode_agreement_assent_signing_input,
)


class AgreementAssentHttpTransportTests(unittest.TestCase):
    def test_signing_input_uses_canonical_ojve_bytes(self):
        self.assertEqual(
            encode_agreement_assent_signing_input(b"abc"),
            {"$olp": "bytes", "v": "YWJj"},
        )

    def test_exact_64_byte_signature_round_trips(self):
        signature = bytes(range(64))
        self.assertEqual(
            decode_agreement_assent_signature(encode_ojve(signature)),
            signature,
        )

    def test_padded_or_noncanonical_signature_carrier_is_rejected(self):
        with self.assertRaises(AgreementAssentHttpTransportError) as caught:
            decode_agreement_assent_signature(
                {"$olp": "bytes", "v": "AA=="}
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_SIGNATURE_ENCODING_INVALID",
        )

    def test_wrong_signature_length_is_rejected(self):
        with self.assertRaises(AgreementAssentHttpTransportError) as caught:
            decode_agreement_assent_signature(encode_ojve(b"\x00" * 63))
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_SIGNATURE_ENCODING_INVALID",
        )

    def test_signing_input_bounds_are_enforced(self):
        for value in (b"", b"x" * 4097):
            with self.subTest(length=len(value)):
                with self.assertRaises(AgreementAssentHttpTransportError):
                    encode_agreement_assent_signing_input(value)


if __name__ == "__main__":
    unittest.main()
