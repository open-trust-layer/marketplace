from __future__ import annotations

import unittest

from marketplace.application.listing import UNIT_ITEM, ExactDecimal, ProductListingDraft
from marketplace.application.web_map import (
    DEFAULT_OFFLINE_MAP_FIXTURE,
    MAX_RENDERED_LISTINGS,
    project_wgs84_e6,
    render_product_listing_page,
)


class M73OfflineWebMapTests(unittest.TestCase):
    def _draft(self, **changes) -> ProductListingDraft:
        values = {
            "seller_principal": "did:example:alice",
            "subject_uri": "urn:example:product:bicycle-1",
            "title": "City bicycle",
            "description": "Reliable commuter bicycle",
            "consideration": ExactDecimal(12_345, 2),
            "currency_code": "EUR",
            "quantity": ExactDecimal(1, 0),
            "unit_uri": UNIT_ITEM,
            "latitude_e6": 52_520_000,
            "longitude_e6": 13_405_000,
        }
        values.update(changes)
        return ProductListingDraft(**values)

    def test_projection_is_integer_bounded_and_deterministic(self):
        fixture = DEFAULT_OFFLINE_MAP_FIXTURE
        self.assertEqual(project_wgs84_e6(-90_000_000, -180_000_000, fixture), (0, 359))
        self.assertEqual(project_wgs84_e6(90_000_000, 180_000_000, fixture), (719, 0))
        self.assertEqual(
            project_wgs84_e6(52_520_000, 13_405_000, fixture),
            project_wgs84_e6(52_520_000, 13_405_000, fixture),
        )

    def test_page_is_static_offline_html_with_inline_svg(self):
        listings = (self._draft(),)
        first = render_product_listing_page(listings)
        second = render_product_listing_page(listings)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("<!doctype html>"))
        self.assertIn("<svg", first)
        self.assertIn("City bicycle", first)
        self.assertIn("123.45 EUR", first)
        self.assertIn("52.520000, 13.405000", first)
        self.assertIn("Offline deterministic coordinate view", first)
        self.assertIn("issuer-attributed, not verified", first)
        for forbidden in ("<script", "<iframe", "<link", "<img", " src=", " href="):
            self.assertNotIn(forbidden, first.lower())

    def test_page_escapes_all_human_text_before_html_projection(self):
        listing = self._draft(
            title='<script>alert("x")</script>',
            description='A & B < C > D "quoted"',
        )
        page = render_product_listing_page((listing,))

        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", page)
        self.assertIn("A &amp; B &lt; C &gt; D &quot;quoted&quot;", page)

    def test_page_rejects_non_tuple_and_listing_overflow_without_enumeration(self):
        touched: list[str] = []

        class HostileIterable:
            def __iter__(self):
                touched.append("iter")
                raise AssertionError("hostile iterable MUST NOT be enumerated")

        with self.assertRaises(TypeError):
            render_product_listing_page(HostileIterable())  # type: ignore[arg-type]
        self.assertEqual(touched, [])

        many = tuple(self._draft(subject_uri=f"urn:example:product:{index}") for index in range(MAX_RENDERED_LISTINGS + 1))
        with self.assertRaises(ValueError):
            render_product_listing_page(many)

    def test_render_revalidates_draft_before_reading_human_values(self):
        listing = self._draft()
        touched: list[str] = []

        class Hostile:
            def __str__(self):
                touched.append("str")
                raise AssertionError("hostile listing field MUST NOT render")

        object.__setattr__(listing, "title", Hostile())
        with self.assertRaises(ValueError):
            render_product_listing_page((listing,))
        self.assertEqual(touched, [])

    def test_empty_page_is_explicit_nonadverse_local_absence(self):
        page = render_product_listing_page(())
        self.assertIn("No local listings in this bounded view.", page)
        self.assertIn("not global nonexistence", page)

    def test_projection_rejects_non_exact_or_out_of_range_coordinates(self):
        for latitude, longitude in (
            (True, 0),
            (0, False),
            (90_000_001, 0),
            (0, 180_000_001),
        ):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValueError):
                    project_wgs84_e6(latitude, longitude, DEFAULT_OFFLINE_MAP_FIXTURE)


if __name__ == "__main__":
    unittest.main()
