from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "src/marketplace/reference/auth_application_v1.py"
DOC_PATH = ROOT / "docs/m17-5w-reference-auth-application.md"
PACKAGE_GATE = ROOT / "tools/package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests/test_package_artifact_gate.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class MarketplaceReferenceAuthenticatedLaunchArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        self.assertTrue(SOURCE_PATH.is_file())
        self.assertTrue(DOC_PATH.is_file())
        self.assertIn("MARKETPLACE_REFERENCE_AUTHENTICATED_LAUNCH_V1", SOURCE)

    def test_public_api_and_exact_input_surface(self) -> None:
        self.assertIn("MarketplaceReferenceAuthenticatedLaunchError", SOURCE)
        self.assertIn("build_reference_authenticated_marketplace_launch_plan", SOURCE)
        function = next(
            node for node in TREE.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "build_reference_authenticated_marketplace_launch_plan"
        )
        names = [argument.arg for argument in function.args.kwonlyargs]
        self.assertEqual(
            names,
            ["application_plan", "provisioning", "runtime_inputs"],
        )
        self.assertNotIn("decode_record_json", names)
        self.assertNotIn("record_principal", names)

    def test_exact_reference_callables_are_bound_in_source(self) -> None:
        self.assertIn("decode_marketplace_application_record_json", SOURCE)
        self.assertIn("marketplace_record_issuer_principal", SOURCE)
        calls = [node for node in ast.walk(TREE) if isinstance(node, ast.Call)]
        called_names = {
            node.func.id
            for node in calls
            if isinstance(node.func, ast.Name)
        }
        self.assertNotIn("decode_marketplace_application_record_json", called_names)
        self.assertNotIn("marketplace_record_issuer_principal", called_names)

    def test_exact_one_t_and_one_u_composition_call(self) -> None:
        calls = [node for node in ast.walk(TREE) if isinstance(node, ast.Call)]
        names = [
            node.func.id
            for node in calls
            if isinstance(node.func, ast.Name)
        ]
        self.assertEqual(names.count("compose_marketplace_authenticated_startup"), 1)
        self.assertEqual(
            names.count("build_marketplace_authenticated_loopback_launch_plan"), 1
        )

    def test_no_activation_or_external_io_symbols(self) -> None:
        forbidden = (
            "load_marketplace_authentication_startup_provisioning",
            "compose_marketplace_authentication_runtime_inputs",
            "run_marketplace_authenticated_application_foreground",
            "run_marketplace_application_foreground",
            "UvicornLoopbackServerProvider",
            "uvicorn",
            "psycopg",
            "socket",
            "subprocess",
            "threading",
            "multiprocessing",
            "asyncio",
            "os.environ",
            "getenv",
            "Path(",
            "open(",
            ".initialize(",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, SOURCE)

    def test_order_is_validation_then_t_then_u(self) -> None:
        validate = SOURCE.index("_validate_application_plan(application_plan)")
        provisioning = SOURCE.index("if type(provisioning)")
        runtime_inputs = SOURCE.index("if type(runtime_inputs)")
        compose_t = SOURCE.index("startup = compose_marketplace_authenticated_startup")
        compose_u = SOURCE.index("authenticated_plan = build_marketplace_authenticated")
        self.assertLess(validate, provisioning)
        self.assertLess(provisioning, runtime_inputs)
        self.assertLess(runtime_inputs, compose_t)
        self.assertLess(compose_t, compose_u)

    def test_predecessors_do_not_select_w(self) -> None:
        paths = (
            "src/marketplace/application/auth_startup_provisioning.py",
            "src/marketplace/application/auth_startup_composition.py",
            "src/marketplace/application/auth_launch.py",
            "src/marketplace/application/auth_runtime_server.py",
            "src/marketplace/reference/application_v1.py",
            "src/marketplace/reference/postgres_application_v1.py",
            "src/marketplace/application/launch.py",
            "src/marketplace/application/runtime_server.py",
            "src/marketplace/application/uvicorn_provider.py",
            "tools/marketplace_localhost.py",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertNotIn("auth_application_v1", text)
                self.assertNotIn(
                    "build_reference_authenticated_marketplace_launch_plan", text
                )

    def test_package_gate_requires_new_reference_module(self) -> None:
        member = "marketplace/reference/auth_application_v1.py"
        self.assertIn(member, PACKAGE_GATE.read_text(encoding="utf-8"))
        self.assertIn(member, PACKAGE_TEST.read_text(encoding="utf-8"))

    def test_document_records_authority_boundaries(self) -> None:
        document = DOC_PATH.read_text(encoding="utf-8")
        markers = (
            "MARKETPLACE_REFERENCE_AUTHENTICATED_LAUNCH_V1",
            "exactly once",
            "zero credential-material consumption",
            "No runtime activation",
            "exact six-file scope",
        )
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, document)


if __name__ == "__main__":
    unittest.main()
