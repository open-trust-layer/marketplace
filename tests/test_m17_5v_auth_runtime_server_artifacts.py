import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py"
DOC = ROOT / "docs" / "m17-5v-auth-runtime-server.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests" / "test_package_artifact_gate.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
LEGACY_CONTROL_POINTS = (
    APPLICATION / "runtime_server.py",
    APPLICATION / "uvicorn_provider.py",
    APPLICATION / "auth_launch.py",
    APPLICATION / "auth_startup_composition.py",
    APPLICATION / "__init__.py",
)
AUTHENTICATED_LOCALHOST_BOOTSTRAP = ROOT / "tools" / "marketplace_localhost.py"


class MarketplaceAuthenticatedRuntimeServerArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = '
            '"MARKETPLACE_APPLICATION_AUTH_FOREGROUND_RUNTIME_V1"',
            source,
        )
        self.assertIn(
            '"EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_selects_no_concrete_provider_or_external_runtime(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for required in (
            "MarketplaceAuthenticatedLoopbackLaunchPlan",
            "MarketplaceAsgiServerProvider",
            "MarketplaceSessionEstablishmentAsgiHttpAdapter",
            "LOOPBACK_LAUNCH_HOST",
            "MIN_LAUNCH_PORT",
            "MAX_LAUNCH_PORT",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "uvicorn_provider",
            "UvicornLoopbackServerProvider",
            "import_module",
            "import uvicorn",
            "import socket",
            "from socket",
            "subprocess",
            "threading",
            "multiprocessing",
            "asyncio",
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
            "run_marketplace_application_foreground",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_public_execution_order_is_token_plan_provider_then_one_run(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "run_marketplace_authenticated_application_foreground"
        )
        statements = list(function.body)
        if (
            statements
            and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Constant)
            and isinstance(statements[0].value.value, str)
        ):
            statements = statements[1:]
        self.assertGreaterEqual(len(statements), 4)
        first, second, third = statements[:3]
        self.assertIsInstance(first, ast.Expr)
        self.assertIsInstance(second, ast.Expr)
        self.assertIsInstance(third, ast.Assign)
        self.assertEqual(first.value.func.id, "_validate_execute_token")
        self.assertEqual(second.value.func.id, "_validate_plan")
        self.assertEqual(third.value.func.id, "_provider_run")
        calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run"
        ]
        self.assertEqual(len(calls), 1)

    def test_source_contains_no_runtime_consumers_beyond_injected_run(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        for forbidden in (
            "now",
            "challenge_bytes",
            "session_token_bytes",
            "initialize",
            "handle",
            "bind",
            "listen",
            "accept",
            "connect",
            "create_task",
            "Popen",
        ):
            self.assertNotIn(forbidden, calls)

    def test_existing_runtime_control_points_do_not_select_v(self) -> None:
        for path in LEGACY_CONTROL_POINTS:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("auth_runtime_server", text)
                self.assertNotIn(
                    "run_marketplace_authenticated_application_foreground",
                    text,
                )

    def test_m17_5y_bootstrap_selects_v_only_through_explicit_authenticated_mode(self) -> None:
        text = AUTHENTICATED_LOCALHOST_BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("auth_runtime_server", text)
        self.assertIn("run_marketplace_authenticated_application_foreground", text)
        self.assertIn(
            '"EXECUTE_AUTHENTICATED_MARKETPLACE_LOCALHOST_MVP_V1"',
            text,
        )
        self.assertIn(
            '"EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER"',
            text,
        )
        self.assertIn('"--execute-authenticated-localhost"', text)

        tree = ast.parse(text)
        top_level_modules: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_level_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_level_modules.add(node.module)
        self.assertNotIn(
            "marketplace.application.auth_runtime_server",
            top_level_modules,
        )

    def test_package_gate_requires_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        package_test = PACKAGE_TEST.read_text(encoding="utf-8")
        required = '"marketplace/application/auth_runtime_server.py"'
        self.assertIn(required, gate)
        self.assertIn(required, package_test)
        self.assertIn(
            "test_missing_auth_runtime_server_member_is_rejected",
            package_test,
        )

    def test_document_records_exact_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_FOREGROUND_RUNTIME_V1",
            "exact six-file scope",
            "fake providers only",
            "token before provider",
            "exactly once",
            "no concrete provider selection",
            "no socket",
            "no application initialization",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()