from __future__ import annotations

from pathlib import Path
import unittest

import marketplace.application as application
from marketplace.application.authoring import ProductListingAuthoringFields


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "authoring.py"


class M17StructuredProductAuthoringArtifactTests(unittest.TestCase):
    def test_public_application_exports_are_present(self):
        for name in (
            "MarketplaceProductListingAuthoringService",
            "ProductListingAuthoringError",
            "ProductListingAuthoringFields",
            "ProductListingRecordBuilder",
        ):
            self.assertIn(name, application.__all__)
            self.assertTrue(hasattr(application, name))

    def test_fields_contract_is_frozen_and_slotted(self):
        params = ProductListingAuthoringFields.__dataclass_params__
        self.assertTrue(params.frozen)
        self.assertFalse(hasattr(self._fields(), "__dict__"))

    def _fields(self):
        return ProductListingAuthoringFields(
            seller_principal="did:example:seller",
            subject_uri="urn:sku:artifact",
            title="Artifact",
            description="Structured authoring artifact test.",
            consideration_coefficient=1,
            consideration_scale=0,
            currency_code="USD",
            quantity_coefficient=1,
            quantity_scale=0,
            unit_uri="https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/unit/item",
            latitude_e6=0,
            longitude_e6=0,
        )

    def test_source_remains_runtime_and_reference_inert(self):
        text = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "marketplace.reference",
            "psycopg",
            "uvicorn",
            "socket",
            "subprocess",
            "os.environ",
            "open(",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
