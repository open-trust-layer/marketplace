from __future__ import annotations

import unittest

from marketplace.reference.federation_v1 import validate_transport_envelope
from marketplace.reference.transport_json_v1 import (
    MarketplaceTransportJsonError,
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)

MESSAGE_TYPE = (
    "https://open-trust-layer.github.io/marketplace/semantics/v1/"
    "federation/message/snapshot-result-v1"
)


class TransportJsonV1Tests(unittest.TestCase):
    def assert_codec_error(self, code: str, body: bytes) -> None:
        with self.assertRaises(MarketplaceTransportJsonError) as caught:
            decode_transport_envelope_json(body)
        self.assertEqual(caught.exception.code, code)

    def test_reference_codec_round_trips_m8_string_key_payload_deterministically(self):
        envelope = (
            "OLP-TRANSPORT",
            1,
            MESSAGE_TYPE,
            {
                "version": 1,
                "source": "https://source.example",
                "operation": "https://example.com/operation",
                "record_ids": (),
            },
        )
        encoded_a = encode_transport_envelope_json(envelope)
        encoded_b = encode_transport_envelope_json(envelope)
        self.assertEqual(encoded_a, encoded_b)
        self.assertIsInstance(encoded_a, bytes)
        self.assertNotIn(b" ", encoded_a)

        decoded = decode_transport_envelope_json(encoded_a)
        self.assertEqual(decoded[0:3], envelope[0:3])
        self.assertIsInstance(decoded[3], dict)
        self.assertEqual(decoded[3]["version"], 1)
        self.assertEqual(decoded[3]["source"], "https://source.example")

        validated = validate_transport_envelope(decoded, MESSAGE_TYPE)
        self.assertEqual(validated["message_type"], MESSAGE_TYPE)
        self.assertFalse(validated["transport_defines_record_identity"])
        self.assertFalse(validated["transport_authentication_is_object_proof"])

    def test_duplicate_json_name_is_rejected_before_olp_interpretation(self):
        body = (
            b'{"olp":1,"type":"https://example.com/message",'
            b'"payload":{"$olp":"map","$olp":"map","v":[]}}'
        )
        self.assert_codec_error("DUPLICATE_JSON_NAME", body)

    def test_duplicate_top_level_name_is_rejected(self):
        body = (
            b'{"olp":1,"olp":1,"type":"https://example.com/message",'
            b'"payload":{"$olp":"map","v":[]}}'
        )
        self.assert_codec_error("DUPLICATE_JSON_NAME", body)

    def test_utf8_bom_and_invalid_utf8_are_rejected(self):
        self.assert_codec_error("JSON_BOM_FORBIDDEN", b"\xef\xbb\xbf{}")
        self.assert_codec_error("INVALID_UTF8", b"\xff")

    def test_nonfinite_json_number_is_rejected(self):
        body = (
            b'{"olp":1,"type":"https://example.com/message",'
            b'"payload":{"$olp":"map","v":[["value",NaN]]}}'
        )
        self.assert_codec_error("INVALID_JSON_NUMBER", body)

    def test_non_string_payload_map_key_is_rejected_at_m8_host_boundary(self):
        body = (
            b'{"olp":1,"type":"https://example.com/message",'
            b'"payload":{"$olp":"map","v":[[1,"value"]]}}'
        )
        self.assert_codec_error("INVALID_OLP_ENVELOPE", body)

    def test_malformed_top_level_and_invalid_envelope_are_rejected(self):
        self.assert_codec_error("INVALID_JSON_ENVELOPE", b"[]")
        self.assert_codec_error(
            "INVALID_OLP_ENVELOPE",
            b'{"olp":2,"type":"https://example.com/message","payload":null}',
        )

    def test_encoder_rejects_non_envelope_and_wrong_marker_or_version(self):
        for value in (
            (),
            ("WRONG", 1, MESSAGE_TYPE, {}),
            ("OLP-TRANSPORT", 2, MESSAGE_TYPE, {}),
        ):
            with self.subTest(value=value):
                with self.assertRaises(MarketplaceTransportJsonError) as caught:
                    encode_transport_envelope_json(value)
                self.assertEqual(caught.exception.code, "INVALID_ABSTRACT_ENVELOPE")


if __name__ == "__main__":
    unittest.main()
