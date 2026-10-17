"""Security/regression tests for inert private-alpha Caddy review candidate."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import marketplace_caddy_vhost_candidate as candidate


ROOT = Path(__file__).resolve().parents[1]


class MarketplaceCaddyVhostCandidateTests(unittest.TestCase):
    def _invoke(self, *args: str) -> tuple[int, str]:
        output = StringIO()
        with redirect_stdout(output):
            code = candidate.main(args)
        return code, output.getvalue()

    def test_default_is_inert_and_does_not_render_configuration(self) -> None:
        with patch.object(
            candidate,
            "render_review_only_caddy_candidate",
            side_effect=AssertionError("must not render"),
        ):
            code, stdout = self._invoke()
        self.assertEqual(code, 0)
        self.assertEqual(stdout, candidate.INERT_STATUS + "\n")
        self.assertNotIn("reverse_proxy", stdout)

    def test_exact_opt_in_produces_one_host_scoped_private_upstream(self) -> None:
        port = "24081"
        code, stdout = self._invoke(
            "--render-candidate",
            candidate.EXACT_RENDER_OPT_IN,
            "--upstream-port",
            port,
        )
        self.assertEqual(code, 0)
        self.assertIn("REVIEW ONLY", stdout)
        self.assertEqual(stdout.count("marketplace.open-trust-layer.org {"), 1)
        self.assertEqual(stdout.count("reverse_proxy"), 1)
        self.assertIn("reverse_proxy 127.0.0.1:24081", stdout)
        self.assertTrue(stdout.endswith("}\n"))
        self.assertNotIn("open-trust-layer.org {", stdout.replace(
            "marketplace.open-trust-layer.org {", ""
        ))
        for bad in (
            "0.0.0.0", "tls internal", "tls_insecure_skip_verify",
            "auto_https off", "http://marketplace", "handle_path",
            "localhost:18080", "respond 200", ":443 {",
        ):
            with self.subTest(bad=bad):
                self.assertNotIn(bad, stdout)

    def test_bad_opt_in_and_input_never_reflect_untrusted_values(self) -> None:
        adversarial = (
            ("--render-candidate", "bad-secret-value", "--upstream-port", "24081"),
            ("--upstream-port", "24081"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "5432"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "024081"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "24081\n:443"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "２４０８１"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "１"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "61111"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "19999"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "2000X"),
            ("--render-candidate", candidate.EXACT_RENDER_OPT_IN, "--upstream-port", "24081", "--extra"),
        )
        for args in adversarial:
            with self.subTest(args=args):
                code, stdout = self._invoke(*args)
                self.assertEqual(code, 2)
                self.assertEqual(stdout, candidate.BLOCKED_STATUS + "\n")

    def test_rejects_nonstring_and_boundary_ports(self) -> None:
        for value in (None, True, 24081, "", "00000", "60999x", " 24081", "24081 ", "0x5e11"):
            with self.subTest(value=value):
                with self.assertRaises(candidate.CaddyCandidateError):
                    candidate.render_review_only_caddy_candidate(upstream_port=value)
        for port in ("20000", "60999"):
            with self.subTest(port=port):
                fragment = candidate.render_review_only_caddy_candidate(upstream_port=port)
                self.assertIn("reverse_proxy 127.0.0.1:" + port, fragment)

    def test_static_safety_boundary_and_selected_vps_agree(self) -> None:
        plan = (ROOT / "docs" / "private-web-alpha-deployment-plan.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "marketplace-caddy-review-candidate.md").read_text(encoding="utf-8")
        source = (ROOT / "tools" / "marketplace_caddy_vhost_candidate.py").read_text(encoding="utf-8")
        self.assertIn(candidate.CANONICAL_ORIGIN, plan)
        self.assertIn(candidate.CANONICAL_ORIGIN, guide)
        self.assertIn("open-trust-layer.org VPS", plan)
        self.assertIn("operator", guide.lower())
        self.assertIn("not deploy", guide.lower())
        self.assertIn("existing vhosts", guide.lower())
        self.assertIn("TLS", guide)
        for forbidden in (
            "import socket", "import subprocess", "import requests",
            "import urllib", "os.system(", "Popen(", "systemctl ",
            "caddy reload", "caddy run", "Restart-Service",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
