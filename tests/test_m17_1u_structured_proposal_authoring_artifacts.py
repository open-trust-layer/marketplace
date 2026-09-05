from __future__ import annotations

from pathlib import Path
import unittest

import marketplace.application as application


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "proposal_authoring.py"


class M17StructuredProposalAuthoringArtifactTests(unittest.TestCase):
    def test_public_application_exports_are_present(self):
        for name in (
            "MarketplaceProposalAuthoringService",
            "ProposalAuthoringError",
            "ProposalRecordBuilder",
        ):
            self.assertIn(name, application.__all__)
            self.assertTrue(hasattr(application, name))

    def test_source_reuses_m17_1t_and_existing_application_api(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("review_buyer_request_proposal_draft", text)
        self.assertIn("respond_to_intent", text)
        self.assertNotIn("create_intent(", text)

    def test_source_remains_runtime_reference_and_transport_inert(self):
        text = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "marketplace.reference",
            "olp",
            "psycopg",
            "uvicorn",
            "socket",
            "subprocess",
            "os.environ",
            "open(",
            "http",
            "android",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
