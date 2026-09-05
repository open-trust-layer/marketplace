from __future__ import annotations

import json
from pathlib import Path
import unittest

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text

from marketplace.application.listing import (
    ExactDecimal,
    ProductListingDraft,
    TERM_CONSIDERATION,
    TERM_TITLE,
    UNIT_ITEM,
)
from marketplace.reference.application_record_json_v1 import (
    MarketplaceApplicationRecordJsonError,
    decode_marketplace_application_record_json,
    encode_marketplace_application_record_json,
)
from marketplace.reference.product_listing_v1 import build_product_listing_record


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "src" / "marketplace" / "reference" / "application_v1.py"
CODEC = ROOT / "src" / "marketplace" / "reference" / "application_record_json_v1.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
DOC = ROOT / "docs" / "m17-1z-reference-application-record-json.md"


def listing_record(*, coefficient: int = 125) -> RecordV1:
    return build_product_listing_record(
        ProductListingDraft(
            seller_principal="did:example:seller",
            subject_uri="urn:example:item:bicycle",
            title="Berlin bicycle",
            description="Reference application Record JSON test",
            consideration=ExactDecimal(coefficient, 0),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_520_000,
            longitude_e6=13_405_000,
        )
    )


class M17ReferenceApplicationRecordJsonTests(unittest.TestCase):
    def test_product_record_round_trip_is_deterministic_and_identity_preserving(self):
        record = listing_record()
        body = encode_marketplace_application_record_json(record)
        document = json.loads(body.decode("utf-8"))
        self.assertEqual(
            set(document),
            {
                "envelope_version",
                "type",
                "content",
                "semantic_bindings",
                "profiles",
                "relationships",
                "extensions",
            },
        )
        self.assertIs(type(document["content"]), dict)
        self.assertEqual(document["content"]["terms"][TERM_TITLE], "Berlin bicycle")

        decoded = decode_marketplace_application_record_json(body)
        self.assertIs(type(decoded), RecordV1)
        self.assertEqual(record_identity_text(decoded), record_identity_text(record))
        self.assertEqual(decoded, record)
        self.assertEqual(encode_marketplace_application_record_json(decoded), body)

    def test_unsafe_integer_uses_pinned_ojve_wrapper_and_round_trips_exactly(self):
        coefficient = (1 << 63) - 1
        record = listing_record(coefficient=coefficient)
        body = encode_marketplace_application_record_json(record)
        document = json.loads(body.decode("utf-8"))
        encoded_coefficient = document["content"]["terms"][TERM_CONSIDERATION]["amount"]["coefficient"]
        self.assertEqual(
            encoded_coefficient,
            {"$olp": "int", "v": str(coefficient)},
        )
        decoded = decode_marketplace_application_record_json(body)
        self.assertEqual(
            decoded.content["terms"][TERM_CONSIDERATION]["amount"]["coefficient"],
            coefficient,
        )
        self.assertEqual(record_identity_text(decoded), record_identity_text(record))

    def test_unwrapped_unsafe_integer_fails_closed(self):
        coefficient = (1 << 63) - 1
        body = encode_marketplace_application_record_json(listing_record(coefficient=coefficient))
        document = json.loads(body.decode("utf-8"))
        document["content"]["terms"][TERM_CONSIDERATION]["amount"]["coefficient"] = coefficient
        hostile = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        with self.assertRaises(MarketplaceApplicationRecordJsonError) as caught:
            decode_marketplace_application_record_json(hostile)
        self.assertEqual(caught.exception.code, "APPLICATION_RECORD_JSON_VALUE_INVALID")

    def test_duplicate_json_name_and_bom_fail_before_record_materialization(self):
        body = encode_marketplace_application_record_json(listing_record())
        duplicate = b'{"envelope_version":1,' + body[1:]
        with self.assertRaises(MarketplaceApplicationRecordJsonError) as caught:
            decode_marketplace_application_record_json(duplicate)
        self.assertEqual(caught.exception.code, "APPLICATION_RECORD_JSON_DUPLICATE_NAME")

        with self.assertRaises(MarketplaceApplicationRecordJsonError) as caught:
            decode_marketplace_application_record_json(b"\xef\xbb\xbf" + body)
        self.assertEqual(caught.exception.code, "APPLICATION_RECORD_JSON_BOM_FORBIDDEN")

    def test_decoder_accepts_record_defaults_without_creating_second_identity(self):
        record = listing_record()
        document = json.loads(encode_marketplace_application_record_json(record).decode("utf-8"))
        for key in ("semantic_bindings", "relationships", "extensions"):
            document.pop(key)
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        decoded = decode_marketplace_application_record_json(body)
        self.assertEqual(record_identity_text(decoded), record_identity_text(record))
        canonical = json.loads(encode_marketplace_application_record_json(decoded).decode("utf-8"))
        self.assertEqual(canonical["semantic_bindings"], {})
        self.assertEqual(canonical["relationships"], [])
        self.assertEqual(canonical["extensions"], {})

    def test_reference_factory_fixes_raw_record_json_profile(self):
        text = FACTORY.read_text(encoding="utf-8-sig")
        self.assertIn(
            "decode_record_json=decode_marketplace_application_record_json",
            text,
        )
        self.assertIn(
            "encode_record_json=encode_marketplace_application_record_json",
            text,
        )
        signature = text.split(
            "def build_reference_marketplace_application_launch_plan(", 1
        )[1].split(") -> MarketplaceApplicationLaunchPlan:", 1)[0]
        self.assertNotIn("decode_record_json", signature)
        self.assertNotIn("encode_record_json", signature)

    def test_codec_and_application_boundary_remain_runtime_inert(self):
        text = CODEC.read_text(encoding="utf-8-sig")
        for forbidden in (
            "PostgresApplicationStateStore",
            "connection_factory=",
            "UvicornLoopbackServerProvider",
            "socket.",
            "subprocess",
            "os.environ",
            "getenv(",
            "Path(",
            "open(",
        ):
            self.assertNotIn(forbidden, text)
        for path in APPLICATION.glob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            self.assertNotIn("marketplace.reference", source, path.name)
            self.assertNotIn("from ..reference", source, path.name)
            self.assertNotIn("from marketplace.reference", source, path.name)

    def test_document_records_profile_and_governance_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8-sig")
        for marker in (
            "application Record JSON v1",
            "pinned OLP OJVE-1",
            "normal string-keyed maps",
            "no PostgreSQL connection",
            "no runtime activation",
            "merge remains a separate exact-head governance boundary",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
