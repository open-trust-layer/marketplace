"""Keep Marketplace acceptance job budget compatible with the admission queue.

This is source-only; it does not execute or modify the shared Windows broker.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "conformance.yml"


class MarketplaceCIQueueTimeoutBudgetTests(unittest.TestCase):
    def test_windows_runner_job_has_bounded_budget_above_observed_queue(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("runs-on: [self-hosted, Windows, X64, marketplace-ci]", text)
        matches = re.findall(r"(?m)^    timeout-minutes: ([0-9]+)$", text)
        self.assertEqual(len(matches), 1, "exactly one acceptance job timeout required")
        budget_minutes = int(matches[0])
        # Two consecutive runs were cancelled after 30m while the capacity
        # admission hook legitimately remained queued beyond 35m.
        # Leave room for full acceptance without allowing indefinite jobs.
        self.assertGreaterEqual(budget_minutes, 60)
        self.assertLessEqual(budget_minutes, 70)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("Check out pinned Open Layer Protocol", text)
        self.assertIn("Run Marketplace acceptance gate", text)


if __name__ == "__main__":
    unittest.main()
