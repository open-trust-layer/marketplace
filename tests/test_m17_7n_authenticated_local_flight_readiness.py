from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
REPORT = ROOT / "MARKETPLACE_FLIGHT_READINESS_REPORT.md"
ACCEPTANCE = ROOT / "MARKETPLACE_MVP_ACCEPTANCE.md"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "m17-7n-authenticated-local-flight-readiness.md"


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class M177NAuthenticatedLocalFlightReadinessTests(unittest.TestCase):
    def test_readme_distinguishes_source_acceptance_from_live_runtime(self) -> None:
        text = normalized(README)
        self.assertIn(
            "Authenticated product-path status:",
            text,
        )
        self.assertIn(
            "merged source and full-conformance acceptance",
            text,
        )
        self.assertIn(
            "real PostgreSQL-backed localhost server + browser run remains a separate, not-yet-executed runtime acceptance gate",
            text,
        )
        self.assertIn("**Production status:** not deployed.", text)

    def test_flight_report_removes_stale_web_gap_and_records_exact_remaining_gate(self) -> None:
        text = normalized(REPORT)
        self.assertNotIn(
            "The active Web UI currently reaches listing and Proposal authoring but does not yet expose the full Accept -> Agreement -> Complete journey.",
            text,
        )
        for marker in (
            "Accept -> Agreement -> Complete",
            "M17.7M proves the final Bearer/session-aware ASGI overlay",
            "in-process/source acceptance",
            "One operator-authorized authenticated loopback run",
            "source/CI flight-ready but not yet live-runtime accepted",
            "M17.7M merged at",
            "7e356b7259b4736772e15da434f9a237b5c88b63",
            "run **#946** succeeded",
            "no claim is made here that the PostgreSQL-backed authenticated localhost server and a real browser have yet been executed together",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_acceptance_guide_matches_exact_reviewed_cli_contract(self) -> None:
        doc = normalized(ACCEPTANCE)
        source = LOCALHOST.read_text(encoding="utf-8")
        for marker in (
            "--preflight-fulfillment-completion-localhost",
            "--execute-fulfillment-completion-localhost",
            "--authentication-provisioning-directory",
            "EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1",
            "MARKETPLACE_POSTGRES_DSN",
            "FULFILLMENT_COMPLETION_AUTHENTICATED_LOCALHOST_PREFLIGHT_READY",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
                self.assertIn(marker, source)

        self.assertIn(
            "host=127.0.0.1 port=18080 postgres_connection_invoked=false database_initialized=false coordination_initialized=false server_invoked=false",
            doc,
        )

    def test_live_evaluator_lane_remains_explicitly_unexecuted_by_repo_acceptance(self) -> None:
        text = normalized(ACCEPTANCE)
        for marker in (
            "the repository does not claim that this real PostgreSQL-backed browser lane has already been executed",
            "separate operator authorization for live runtime execution",
            "source/CI accepted, live-runtime pending",
            "completion is attributable evidence, not universal truth, payment, or settlement",
            "loopback-only and no public deployment was involved",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_milestone_document_freezes_truth_and_non_authority(self) -> None:
        text = normalized(DOC)
        for marker in (
            "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_READINESS_V1",
            "documentation/acceptance-contract only",
            "source/CI accepted, **live-runtime pending**",
            "exact-head full conformance run **#946** succeeded",
            "separate operator runtime authorization",
            "performs no PostgreSQL connection or initialization",
            "documentation-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_n_is_documentation_contract_only(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
        self.assertEqual(
            modules,
            {"__future__", "ast", "pathlib", "unittest"},
        )
        self.assertEqual(
            list((ROOT / "src").rglob("*m17_7n*")),
            [],
        )
        self.assertEqual(
            list((ROOT / "tools").glob("*m17_7n*")),
            [],
        )


if __name__ == "__main__":
    unittest.main()
