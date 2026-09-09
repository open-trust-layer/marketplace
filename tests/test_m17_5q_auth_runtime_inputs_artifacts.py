from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_runtime_inputs.py"
DOC = ROOT / "docs" / "m17-5q-auth-runtime-inputs.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests" / "test_package_artifact_gate.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
CONTROL_POINTS = (
    APPLICATION / "auth_http_composition.py",
    APPLICATION / "auth_session_asgi.py",
    APPLICATION / "asgi.py",
    APPLICATION / "launch.py",
    APPLICATION / "runtime_server.py",
)


class MarketplaceAuthenticationRuntimeInputArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_RUNTIME_INPUTS_V1"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_has_no_provisioning_or_activation_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "import os",
            "from os",
            "os.environ",
            "pathlib",
            "Path(",
            "open(",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "random",
            "private_key",
            "sign(",
            "MarketplaceSessionEstablishmentAsgiHttpAdapter",
            "MarketplaceApplicationLaunchPlan",
            "MarketplaceAsgiServerProvider",
            "MarketplaceUvicornServerProvider",
            "run_marketplace_application_foreground",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_composition_performs_zero_runtime_input_calls(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        compose = functions["compose_marketplace_authentication_runtime_inputs"]
        calls: set[str] = set()
        for node in ast.walk(compose):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertIn("MarketplaceCredentialMaterialSource", calls)
        self.assertIn("MarketplaceAuthenticationUnixClock", calls)
        self.assertNotIn("_time_ns", calls)
        self.assertNotIn("challenge_bytes", calls)
        self.assertNotIn("session_token_bytes", calls)

    def test_activation_entry_points_do_not_select_profile(self) -> None:
        for path in CONTROL_POINTS:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("auth_runtime_inputs", text)
                self.assertNotIn(
                    "compose_marketplace_authentication_runtime_inputs",
                    text,
                )

    def test_package_gate_requires_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_runtime_inputs.py"',
            gate,
        )
        package_test = PACKAGE_TEST.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_runtime_inputs.py"',
            package_test,
        )
        self.assertIn(
            "test_missing_auth_runtime_inputs_member_is_rejected",
            package_test,
        )

    def test_document_records_exact_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_RUNTIME_INPUTS_V1",
            "exact six-file scope",
            "zero credential-material calls",
            "zero wall-clock reads",
            "whole Unix seconds",
            "no ASGI",
            "no runtime",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
