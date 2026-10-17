"""Source-only regression for the private Web alpha decision boundary."""
from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "private-web-alpha-deployment-plan.md"
MOON = ROOT / "moon.manifest.yaml"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class PrivateWebAlphaDeploymentPlanTests(unittest.TestCase):
    def test_proposed_alpha_is_not_claimed_as_deployed(self) -> None:
        doc = normalized(DOC)
        for marker in (
            "source-only",
            "invitation-only HTTPS Web alpha",
            "Payments, settlement, public self-signup",
            "OFF",
            "not a production service entry point",
            "is a real reservation",
            "not a runtime PASS",
            "separate operator deployment approval",
            "This document/test change creates no compute",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)
        self.assertNotIn("production deployment completed", doc.lower())

    def test_require_real_product_flight_and_safe_evidence(self) -> None:
        doc = normalized(DOC)
        for marker in (
            "Issue #525",
            "manually closed",
            "release gate remains **BLOCKED**",
            "127.0.0.1",
            "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1",
            "Publish Agreement",
            "seller-delivery",
            "CLAIMED_COMPLETE_PERFORMANCE",
            "independent",
            "Operator-generated **non-secret**",
            "backup **and restore**",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_host_decision_and_security_boundaries_are_explicit(self) -> None:
        doc = normalized(DOC)
        for marker in (
            "Authoritative execution host",
            "Canonical alpha FQDN",
            "Persistent database and secret boundary",
            "Operations ownership",
            "Invitation policy",
            "production ASGI",
            "X-Forwarded-",
            "rate limits",
            "version-linked",
            "G. Limited public beta",
            "Payments remain disabled",
            "separate public-access authorization",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)

    def test_actual_runtime_is_still_local_and_manifest_is_workspace_only(self) -> None:
        launch = LOCALHOST.read_text(encoding="utf-8")
        self.assertIn("127.0.0.1", launch)
        self.assertIn("not a production deployment", launch.lower())
        manifest = json.loads(MOON.read_text(encoding="utf-8"))
        self.assertEqual(manifest["health"]["kind"], "workspace")
        self.assertEqual(manifest["environment"], "development")
        self.assertEqual(manifest["actions"], [])


if __name__ == "__main__":
    unittest.main()
