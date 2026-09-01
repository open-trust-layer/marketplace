from __future__ import annotations

import unittest

from marketplace.application.listing import UNIT_ITEM, ExactDecimal, ProductListingDraft
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.web_map_v1 import render_product_listing_record_page


class M73OfflineWebMapIntegrationTests(unittest.TestCase):
    def _draft(self, *, title: str, latitude_e6: int, longitude_e6: int) -> ProductListingDraft:
        return ProductListingDraft(
            seller_principal="did:example:alice",
            subject_uri=f"urn:example:product:{title.lower().replace(' ', '-')}",
            title=title,
            description=f"Offline fixture listing for {title}",
            consideration=ExactDecimal(12_345, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=latitude_e6,
            longitude_e6=longitude_e6,
        )

    def test_genuine_m72_records_render_through_reviewed_extractor(self):
        records = (
            build_product_listing_record(self._draft(title="Berlin bicycle", latitude_e6=52_520_000, longitude_e6=13_405_000)),
            build_product_listing_record(self._draft(title="Lisbon bicycle", latitude_e6=38_722_300, longitude_e6=-9_139_300)),
        )
        page = render_product_listing_record_page(records)
        self.assertIn("Berlin bicycle", page)
        self.assertIn("Lisbon bicycle", page)
        self.assertIn("52.520000, 13.405000", page)
        self.assertIn("38.722300, -9.139300", page)
        self.assertEqual(page.count('class="marker"'), 2)

    def test_record_bridge_rejects_non_tuple_without_enumeration(self):
        touched: list[str] = []

        class HostileIterable:
            def __iter__(self):
                touched.append("iter")
                raise AssertionError("hostile record iterable MUST NOT be enumerated")

        with self.assertRaises(TypeError):
            render_product_listing_record_page(HostileIterable())  # type: ignore[arg-type]
        self.assertEqual(touched, [])


if __name__ == "__main__":
    unittest.main()
