from __future__ import annotations

from pathlib import Path
import unittest

import marketplace.application as application
from marketplace.application.proposal import BuyerRequestProposalDraft


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "proposal.py"
REFERENCE_SOURCE = ROOT / "src" / "marketplace" / "reference" / "proposal_v1.py"


class M17StructuredProposalArtifactTests(unittest.TestCase):
    def test_application_exports_and_frozen_slotted_contract(self):
        for name in ("BuyerRequestProposalDraft", "MAX_PROPOSAL_PARENT_RECORD_ID_CHARS"):
            self.assertIn(name, application.__all__)
            self.assertTrue(hasattr(application, name))
        params = BuyerRequestProposalDraft.__dataclass_params__
        self.assertTrue(params.frozen)
        draft = BuyerRequestProposalDraft(
            buyer_principal="did:example:buyer",
            subject_uri="urn:sku:artifact",
            action_uri="https://example.test/actions/buy",
            parent_record_id="r1_" + "A" * 43,
        )
        self.assertFalse(hasattr(draft, "__dict__"))

    def test_application_source_stays_olp_reference_runtime_and_io_inert(self):
        text = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "marketplace.reference",
            "from olp",
            "import olp",
            "psycopg",
            "uvicorn",
            "socket",
            "subprocess",
            "os.environ",
            "open(",
        ):
            self.assertNotIn(forbidden, text)

    def test_reference_builder_does_not_define_buy_taxonomy_or_side_effects(self):
        text = REFERENCE_SOURCE.read_text(encoding="utf-8").lower()
        self.assertNotIn("action_buy", text)
        self.assertNotIn("/action/buy", text)
        for forbidden in (
            "psycopg",
            "uvicorn",
            "socket",
            "subprocess",
            "os.environ",
            "requests.",
            "httpx",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
