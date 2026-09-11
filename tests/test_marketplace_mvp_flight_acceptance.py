from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from tools.marketplace_mvp_flight_acceptance import (
    MarketplaceMvpFlightResult,
    run_marketplace_mvp_flight_acceptance,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "marketplace_mvp_flight_acceptance.py"


class MarketplaceMvpFlightAcceptanceTests(unittest.TestCase):
    def test_two_user_product_loop_reaches_verified_completion(self):
        result = run_marketplace_mvp_flight_acceptance()

        self.assertIs(type(result), MarketplaceMvpFlightResult)
        self.assertEqual(
            result.states,
            ("CREATED", "PUBLISHED", "DISCOVERED", "ACCEPTED", "COMPLETED"),
        )
        self.assertEqual(result.final_state, "COMPLETED")
        self.assertEqual(result.completed_at, "2026-09-11T18:00:02Z")
        self.assertTrue(result.seller_principal.startswith("urn:open-layer-marketplace:mvp:identity:"))
        self.assertTrue(result.buyer_principal.startswith("urn:open-layer-marketplace:mvp:identity:"))
        self.assertTrue(result.listing_integrity_verified)
        self.assertEqual(result.agreement_formation, "EVIDENCE_SUFFICIENT_FOR_PROFILE")
        self.assertEqual(result.fulfillment_conclusion, "FULFILLED_UNDER_METHOD")
        self.assertFalse(result.universal_truth)
        self.assertFalse(result.payment_or_settlement_evaluated)

        self.assertNotEqual(result.seller_principal, result.buyer_principal)
        self.assertEqual(len(result.audit_record_ids), 7)
        self.assertEqual(len(set(result.audit_record_ids)), 7)
        for record_id in result.audit_record_ids:
            self.assertTrue(record_id.startswith("r1_"))

    def test_flight_is_deterministic_and_result_is_immutable(self):
        first = run_marketplace_mvp_flight_acceptance()
        second = run_marketplace_mvp_flight_acceptance()
        self.assertEqual(first, second)

        with self.assertRaises(FrozenInstanceError):
            first.final_state = "CREATED"

    def test_tool_is_local_only_and_does_not_activate_external_capabilities(self):
        source = TOOL.read_text(encoding="utf-8")
        forbidden = (
            "psycopg",
            "requests.",
            "urllib.",
            "socket.",
            "subprocess.",
            "EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER",
            "run_marketplace_application_foreground",
        )
        for token in forbidden:
            self.assertNotIn(token, source)
        self.assertIn("payment_or_settlement_evaluated", source)


if __name__ == "__main__":
    unittest.main()
