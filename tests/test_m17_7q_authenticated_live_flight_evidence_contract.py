from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "m17-7q-authenticated-live-flight-evidence-contract.md"
READINESS = ROOT / "MARKETPLACE_FLIGHT_READINESS_REPORT.md"
MVP = ROOT / "MARKETPLACE_MVP_ACCEPTANCE.md"


class MarketplaceAuthenticatedLiveFlightEvidenceContractTests(unittest.TestCase):
    def test_contract_records_real_o_and_p_live_findings_without_claiming_completion(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_AUTHENTICATED_LIVE_FLIGHT_EVIDENCE_CONTRACT_V1",
            "AGREEMENT_ASSENT_CLOCK_INVALID",
            "AUTH_REQUIRED",
            "M17.7O",
            "M17.7P",
            "partially exercised",
            "not yet live-runtime accepted",
            "A fresh post-P browser repeat remains required",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_final_evidence_is_exact_non_secret_and_completion_specific(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        for marker in (
            "127.0.0.1",
            "EVIDENCE_SUFFICIENT_FOR_PROFILE",
            "Publish Agreement",
            "Claim delivery complete",
            "seller-delivery",
            "CLAIMED_COMPLETE_PERFORMANCE",
            "completion evidence Record Identity",
            "STORED",
            "DUPLICATE",
            "local change sequence",
            "not universal truth",
            "not payment or settlement",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_secret_and_authority_boundaries_remain_explicit(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        for marker in (
            "must not contain",
            "Bearer/session-token text",
            "browser private keys",
            "PostgreSQL DSN text",
            "no server execution",
            "no browser automation dependency",
            "public-network exposure",
            "payment or settlement authority",
            "production credential handling",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_readiness_and_mvp_docs_keep_post_p_runtime_gate_open(self) -> None:
        readiness = READINESS.read_text(encoding="utf-8")
        mvp = MVP.read_text(encoding="utf-8")
        for marker in (
            "M17.7O",
            "M17.7P",
            "live-runtime partially exercised",
            "post-P",
        ):
            with self.subTest(document="readiness", marker=marker):
                self.assertIn(marker, readiness)
        for marker in (
            "M17.7O",
            "M17.7P",
            "live-runtime partially exercised",
            "post-P",
        ):
            with self.subTest(document="mvp", marker=marker):
                self.assertIn(marker, mvp)

    def test_q_is_acceptance_contract_only(self) -> None:
        self.assertEqual(list((ROOT / "src").rglob("*m17_7q*")), [])
        self.assertEqual(list((ROOT / "tools").glob("*m17_7q*")), [])
        self.assertEqual(list((ROOT / "web").glob("*m17_7q*")), [])


if __name__ == "__main__":
    unittest.main()
