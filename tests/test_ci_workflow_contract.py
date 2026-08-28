from pathlib import Path
import unittest


class SelfHostedCIWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls.workflow = (repo_root / ".github" / "workflows" / "conformance.yml").read_text(
            encoding="utf-8"
        )

    def test_preserves_acceptance_identity_and_gate(self) -> None:
        self.assertIn("name: Marketplace conformance", self.workflow)
        self.assertIn("  acceptance:\n", self.workflow)
        self.assertIn(
            "tools/conformance_gate.py --olp-root ../olp --timeout 90",
            self.workflow,
        )

    def test_targets_only_marketplace_self_hosted_runner(self) -> None:
        self.assertIn(
            "runs-on: [self-hosted, Windows, X64, marketplace-ci]",
            self.workflow,
        )
        self.assertNotIn("ubuntu-latest", self.workflow)
        self.assertNotIn("actions/setup-python", self.workflow)
        self.assertNotIn("pull_request_target", self.workflow)

    def test_uses_verified_runtime_and_unconditional_cleanup(self) -> None:
        self.assertIn(
            "C:\\CI\\marketplace-toolcache\\Python\\3.12.10\\x64\\python.exe",
            self.workflow,
        )
        self.assertIn("if: ${{ always() }}", self.workflow)
        self.assertIn("marketplace-ci-venv", self.workflow)
        self.assertIn("pip-cache", self.workflow)

    def test_keeps_minimal_token_permissions_and_pinned_checkout(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        checkout_sha = "3d3c42e5aac5ba805825da76410c181273ba90b1"
        self.assertEqual(self.workflow.count(f"actions/checkout@{checkout_sha}"), 2)


if __name__ == "__main__":
    unittest.main()
