import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_launch.py"
DOC = ROOT / "docs" / "m17-5u-auth-launch.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests" / "test_package_artifact_gate.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
CONTROL_POINTS = (
    APPLICATION / "auth_startup_composition.py",
    APPLICATION / "launch.py",
    APPLICATION / "runtime_server.py",
    APPLICATION / "uvicorn_provider.py",
    APPLICATION / "asgi.py",
)


class MarketplaceAuthenticatedLaunchArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = '
            '"MARKETPLACE_APPLICATION_AUTH_LOOPBACK_LAUNCH_PLAN_V1"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_is_inert_authenticated_launch_metadata_only(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "MarketplaceAuthenticatedStartupComposition",
            "MarketplaceSessionEstablishmentAsgiHttpAdapter",
            "LOOPBACK_LAUNCH_HOST",
            "MIN_LAUNCH_PORT",
            "MAX_LAUNCH_PORT",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "import socket",
            "from socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "os.environ",
            "getenv",
            "private_key",
            "sign(",
            "load_marketplace_authentication_startup_provisioning",
            "compose_marketplace_authenticated_startup",
            "build_marketplace_application_launch_plan",
            "MarketplaceAsgiServerProvider",
            "MarketplaceUvicornServerProvider",
            "run_marketplace_application_foreground",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_builder_invokes_no_consuming_or_execution_call(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        builder = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "build_marketplace_authenticated_loopback_launch_plan"
        )
        calls = []
        for node in ast.walk(builder):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        for forbidden in (
            "now",
            "challenge_bytes",
            "session_token_bytes",
            "handle",
            "initialize",
            "run",
            "bind",
            "listen",
            "connect",
        ):
            self.assertNotIn(forbidden, calls)

    def test_predecessors_and_runtime_entry_points_do_not_select_u(self) -> None:
        for path in CONTROL_POINTS:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("auth_launch", text)
                self.assertNotIn(
                    "build_marketplace_authenticated_loopback_launch_plan",
                    text,
                )

    def test_package_gate_requires_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        package_test = PACKAGE_TEST.read_text(encoding="utf-8")
        required = '"marketplace/application/auth_launch.py"'
        self.assertIn(required, gate)
        self.assertIn(required, package_test)
        self.assertIn("test_missing_auth_launch_member_is_rejected", package_test)

    def test_document_records_exact_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_LOOPBACK_LAUNCH_PLAN_V1",
            "exact six-file scope",
            "127.0.0.1",
            "zero clock reads",
            "zero credential-material calls",
            "no socket bind",
            "no runtime",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
