from __future__ import annotations

import unittest

from marketplace.reference.transport_json_v1 import (
    MarketplaceTransportJsonError,
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)


MESSAGE_TYPE = "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/snapshot-request-v1"


class ReferenceTransportJsonTests(unittest.TestCase):
    def envelope(self):
        return (
            "OLP-TRANSPORT",
            1,
            MESSAGE_TYPE,
            {
                "version": 1,
                "cursor": b"opaque",
                "large": (1 << 53) + 1,
            },
        )

    def assert_codec_error(self, code: str, fn, *args):
        with self.assertRaises(MarketplaceTransportJsonError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def test_encode_is_deterministic_and_round_trips_through_pinned_olp_envelope(self):
        first = encode_transport_envelope_json(self.envelope())
        second = encode_transport_envelope_json(self.envelope())
        self.assertEqual(first, second)
        self.assertNotIn(b" ", first)
        decoded = decode_transport_envelope_json(first)
        self.assertEqual(decoded, self.envelope())

    def test_invalid_abstract_marker_or_version_is_rejected_before_olp(self):
        self.assert_codec_error(
            "INVALID_ABSTRACT_ENVELOPE",
            encode_transport_envelope_json,
            ("WRONG", 1, MESSAGE_TYPE, {}),
        )
        self.assert_codec_error(
            "INVALID_ABSTRACT_ENVELOPE",
            encode_transport_envelope_json,
            ("OLP-TRANSPORT", 2, MESSAGE_TYPE, {}),
        )

    def test_duplicate_json_names_are_rejected_at_nested_depth(self):
        body = (
            b'{"olp":1,"type":"'
            + MESSAGE_TYPE.encode("ascii")
            + b'","payload":{"$olp":"map","v":[["x",{"$olp":"map","v":[]}]],"$olp":"map"}}'
        )
        self.assert_codec_error("DUPLICATE_JSON_NAME", decode_transport_envelope_json, body)

    def test_malformed_utf8_bom_and_non_object_top_level_are_rejected(self):
        self.assert_codec_error("INVALID_UTF8", decode_transport_envelope_json, b'"\xff"')
        self.assert_codec_error("JSON_BOM_FORBIDDEN", decode_transport_envelope_json, b"\xef\xbb\xbf{}")
        self.assert_codec_error("INVALID_JSON_ENVELOPE", decode_transport_envelope_json, b"[]")

    def test_nonfinite_json_number_is_rejected_before_olp_processing(self):
        body = (
            b'{"olp":1,"type":"'
            + MESSAGE_TYPE.encode("ascii")
            + b'","payload":NaN}'
        )
        self.assert_codec_error("INVALID_JSON_NUMBER", decode_transport_envelope_json, body)

    def test_unknown_or_malformed_olp_envelope_remains_an_olp_boundary_failure(self):
        self.assert_codec_error(
            "INVALID_OLP_ENVELOPE",
            decode_transport_envelope_json,
            b'{"olp":1,"type":"not-an-absolute-extension","payload":null}',
        )


if __name__ == "__main__":
    unittest.main()
