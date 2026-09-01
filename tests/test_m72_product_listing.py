from __future__ import annotations

import unittest

from marketplace.application.listing import (
    ACTION_SELL,
    CORE_PROFILE,
    LOCATION_WGS84_E6,
    PRODUCT_LISTING_PROFILE,
    TERM_CONSIDERATION,
    TERM_DESCRIPTION,
    TERM_LOCATION,
    TERM_QUANTITY,
    TERM_TITLE,
    TYPE_INTENT,
    UNIT_ITEM,
    ExactDecimal,
    ProductListingDraft,
    build_product_listing_mapping,
)


class M72ProductListingTests(unittest.TestCase):
    def _draft(self, **changes) -> ProductListingDraft:
        values = {
            "seller_principal": "did:example:alice",
            "subject_uri": "urn:example:product:bicycle-1",
            "title": "City bicycle",
            "description": "Reliable commuter bicycle",
            "consideration": ExactDecimal.from_minor_units(12_500, scale=2),
            "currency_code": "EUR",
            "quantity": ExactDecimal(1, 0),
            "unit_uri": UNIT_ITEM,
            "latitude_e6": 52_520_000,
            "longitude_e6": 13_405_000,
        }
        values.update(changes)
        return ProductListingDraft(**values)

    def test_exact_decimal_canonicalizes_minor_units(self):
        self.assertEqual(
            ExactDecimal.from_minor_units(12_500, scale=2).as_mapping(),
            {"coefficient": 125, "scale": 0},
        )
        self.assertEqual(
            ExactDecimal.from_minor_units(12_345, scale=2).as_mapping(),
            {"coefficient": 12_345, "scale": 2},
        )
        self.assertEqual(ExactDecimal(0, 7).as_mapping(), {"coefficient": 0, "scale": 0})

    def test_builder_maps_human_fields_into_reviewed_market_intent_structures(self):
        mapping = build_product_listing_mapping(self._draft())

        self.assertEqual(mapping["envelope_version"], 1)
        self.assertEqual(mapping["type"], TYPE_INTENT)
        self.assertEqual(mapping["profiles"], [CORE_PROFILE, PRODUCT_LISTING_PROFILE])
        content = mapping["content"]
        self.assertEqual(content["issuer"], {"principal": "did:example:alice"})
        self.assertEqual(content["subjects"], [{"uri": "urn:example:product:bicycle-1"}])
        self.assertEqual(content["action"], {"id": ACTION_SELL})
        self.assertNotIn("title", content)
        self.assertNotIn("description", content)
        self.assertNotIn("price", content)
        self.assertNotIn("quantity", content)
        self.assertNotIn("location", content)

        terms = content["terms"]
        self.assertEqual(terms[TERM_TITLE], "City bicycle")
        self.assertEqual(terms[TERM_DESCRIPTION], "Reliable commuter bicycle")
        self.assertEqual(
            terms[TERM_CONSIDERATION],
            {"kind": "monetary", "amount": {"coefficient": 125, "scale": 0}, "currency_code": "EUR"},
        )
        self.assertEqual(
            terms[TERM_QUANTITY],
            {"value": {"coefficient": 1, "scale": 0}, "unit": UNIT_ITEM},
        )
        self.assertEqual(
            terms[TERM_LOCATION],
            {
                "scheme": LOCATION_WGS84_E6,
                "value": {"latitude_e6": 52_520_000, "longitude_e6": 13_405_000},
            },
        )
    def test_builder_rejects_invalid_human_listing_inputs(self):
        invalid = (
            {"title": "x" * 121},
            {"description": "x" * 4097},
            {"currency_code": "eur"},
            {"quantity": ExactDecimal(0, 0)},
            {"unit_uri": "item"},
            {"latitude_e6": True},
            {"latitude_e6": 90_000_001},
            {"longitude_e6": -180_000_001},
        )
        for changes in invalid:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    build_product_listing_mapping(self._draft(**changes))

    def test_builder_returns_detached_fresh_container_graph(self):
        draft = self._draft()
        first = build_product_listing_mapping(draft)
        second = build_product_listing_mapping(draft)

        self.assertIsNot(first, second)
        self.assertIsNot(first["content"], second["content"])
        self.assertIsNot(first["content"]["terms"], second["content"]["terms"])
        first["content"]["terms"][TERM_TITLE] = "mutated"
        self.assertEqual(second["content"]["terms"][TERM_TITLE], "City bicycle")


if __name__ == "__main__":
    unittest.main()
