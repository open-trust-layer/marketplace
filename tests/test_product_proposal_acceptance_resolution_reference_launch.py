from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "src" / "marketplace" / "reference" / "auth_application_v1.py"
DOC_PATH = ROOT / "docs" / "product-proposal-acceptance-resolution-reference-launch.md"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class ProductProposalAcceptanceResolutionReferenceLaunchTests(unittest.TestCase):
    def test_exact_resolver_is_constructed_once_and_injected_once(self) -> None:
        calls = [
            node
            for node in ast.walk(TREE)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        ]
        names = [node.func.id for node in calls]
        self.assertEqual(
            names.count("MarketplaceProposalAcceptanceResolutionService"),
            1,
        )
        compose = next(
            node
            for node in calls
            if node.func.id == "compose_marketplace_authenticated_startup"
        )
        keyword_names = {keyword.arg for keyword in compose.keywords}
        self.assertIn("proposal_acceptance_resolution", keyword_names)

    def test_resolver_uses_same_state_and_pinned_reference_semantics(self) -> None:
        for marker in (
            "state=application_plan.composition.state",
            "is_proposal_record=is_marketplace_proposal_record",
            "proposal_parent_ids=marketplace_response_parent_ids",
            "extract_product_listing=extract_product_listing",
            "record_principal=marketplace_record_issuer_principal",
            "build_acceptance_record=build_proposal_acceptance_record",
            "acceptance_proposal_id=proposal_acceptance_proposal_id",
            "record_identity=proposal_acceptance_record_id",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, SOURCE)

    def test_reference_selection_does_not_execute_resolution_or_runtime(self) -> None:
        for forbidden in (
            ".resolve(",
            ".peek(",
            ".initialize(",
            "run_marketplace_authenticated_application_foreground",
            "UvicornLoopbackServerProvider",
            "psycopg",
            "socket",
            "subprocess",
            "getenv",
            "Path(",
            "open(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, SOURCE)

    def test_document_records_inert_shared_state_boundary(self) -> None:
        self.assertTrue(DOC_PATH.is_file())
        document = DOC_PATH.read_text(encoding="utf-8")
        for marker in (
            "same reviewed application state",
            "exact same `MarketplaceApplicationStateService` instance",
            "does not call `resolve(...)`",
            "does not execute authenticated localhost",
            "No deployment",
            "source-only",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, document)


if __name__ == "__main__":
    unittest.main()
