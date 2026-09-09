import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_asgi_composition.py"
DOC = ROOT / "docs" / "m17-5r-auth-asgi-composition.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests" / "test_package_artifact_gate.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
CONTROL_POINTS = (
    APPLICATION / "asgi.py",
    APPLICATION / "launch.py",
    APPLICATION / "runtime_server.py",
    APPLICATION / "uvicorn_provider.py",
)


class MarketplaceAuthenticatedAsgiCompositionArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ASGI_COMPOSITION_V1"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_has_only_reviewed_composition_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("MarketplaceAuthenticatedHttpComposition", source)
        self.assertIn("MarketplaceAuthenticationRuntimeInputs", source)
        self.assertIn("MarketplaceSessionEstablishmentAsgiHttpAdapter", source)
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
            "private_key",
            "sign(",
            "MarketplaceApplicationLaunchPlan",
            "MarketplaceAsgiServerProvider",
            "MarketplaceUvicornServerProvider",
            "run_marketplace_application_foreground",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_composition_performs_zero_runtime_or_request_calls(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        compose = functions["compose_marketplace_authenticated_asgi"]
        calls: set[str] = set()
        for node in ast.walk(compose):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertIn("MarketplaceSessionEstablishmentAsgiHttpAdapter", calls)
        self.assertNotIn("challenge_bytes", calls)
        self.assertNotIn("session_token_bytes", calls)
        self.assertNotIn("now", calls)
        self.assertNotIn("handle", calls)
        self.assertNotIn("initialize", calls)
        self.assertNotIn("run", calls)

    def test_runtime_entry_points_do_not_select_profile(self) -> None:
        for path in CONTROL_POINTS:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("auth_asgi_composition", text)
                self.assertNotIn("compose_marketplace_authenticated_asgi", text)

    def test_package_gate_requires_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_asgi_composition.py"',
            gate,
        )
        package_test = PACKAGE_TEST.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_asgi_composition.py"',
            package_test,
        )
        self.assertIn(
            "test_missing_auth_asgi_composition_member_is_rejected",
            package_test,
        )

    def test_document_records_exact_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ASGI_COMPOSITION_V1",
            "exact six-file scope",
            "zero credential-material calls",
            "zero wall-clock reads",
            "zero request handling",
            "no launch",
            "no runtime",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
