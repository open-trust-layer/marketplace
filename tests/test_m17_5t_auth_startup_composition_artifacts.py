import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py"
DOC = ROOT / "docs" / "m17-5t-auth-startup-composition.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests" / "test_package_artifact_gate.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
CONTROL_POINTS = (
    APPLICATION / "auth_startup_provisioning.py",
    APPLICATION / "auth_runtime_inputs.py",
    APPLICATION / "auth_static_composition.py",
    APPLICATION / "auth_http_composition.py",
    APPLICATION / "auth_asgi_composition.py",
    APPLICATION / "asgi.py",
    APPLICATION / "launch.py",
    APPLICATION / "runtime_server.py",
    APPLICATION / "uvicorn_provider.py",
)


class MarketplaceAuthenticatedStartupCompositionArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = '
            '"MARKETPLACE_APPLICATION_AUTH_STARTUP_COMPOSITION_V1"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_is_only_reviewed_in_memory_composition(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "MarketplaceAuthenticationStartupProvisioning",
            "MarketplaceAuthenticationRuntimeInputs",
            "compose_marketplace_static_authentication",
            "compose_marketplace_authenticated_http",
            "compose_marketplace_authenticated_asgi",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "import os",
            "from os",
            "pathlib",
            "Path(",
            "open(",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "private_key",
            "sign(",
            "load_marketplace_authentication_startup_provisioning",
            "compose_marketplace_authentication_runtime_inputs",
            "MarketplaceApplicationLaunchPlan",
            "build_marketplace_application_launch_plan",
            "MarketplaceAsgiServerProvider",
            "MarketplaceUvicornServerProvider",
            "run_marketplace_application_foreground",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_composer_has_exact_one_clock_and_o_p_r_calls(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        compose = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "compose_marketplace_authenticated_startup"
        )
        calls: list[str] = []
        for node in ast.walk(compose):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
        self.assertEqual(calls.count("now"), 1)
        self.assertEqual(calls.count("compose_marketplace_static_authentication"), 1)
        self.assertEqual(calls.count("compose_marketplace_authenticated_http"), 1)
        self.assertEqual(calls.count("compose_marketplace_authenticated_asgi"), 1)
        for forbidden in (
            "challenge_bytes",
            "session_token_bytes",
            "decode_record_json",
            "record_principal",
            "handle",
            "initialize",
            "run",
        ):
            self.assertNotIn(forbidden, calls)

    def test_clock_and_o_p_r_stage_order_is_explicit(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        markers = (
            "at_time = runtime_inputs.clock.now()",
            "authentication = compose_marketplace_static_authentication(",
            "http = compose_marketplace_authenticated_http(",
            "asgi = compose_marketplace_authenticated_asgi(",
        )
        positions = [source.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_predecessors_and_runtime_entry_points_do_not_select_t(self) -> None:
        for path in CONTROL_POINTS:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("auth_startup_composition", text)
                self.assertNotIn("compose_marketplace_authenticated_startup", text)

    def test_package_gate_requires_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        package_test = PACKAGE_TEST.read_text(encoding="utf-8")
        required = '"marketplace/application/auth_startup_composition.py"'
        self.assertIn(required, gate)
        self.assertIn(required, package_test)
        self.assertIn(
            "test_missing_auth_startup_composition_member_is_rejected",
            package_test,
        )

    def test_document_records_exact_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_STARTUP_COMPOSITION_V1",
            "exact six-file scope",
            "exactly one clock read",
            "zero credential-material calls",
            "zero request handling",
            "no launch",
            "no runtime",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()