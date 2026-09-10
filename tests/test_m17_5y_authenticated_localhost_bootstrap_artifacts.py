from __future__ import annotations

import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/marketplace_localhost.py"


class MarketplaceAuthenticatedLocalhostBootstrapArtifactTests(unittest.TestCase):
    def test_authentication_stack_remains_lazy_and_old_live_providers_remain_lazy(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        top_level_modules: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_level_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_level_modules.add(node.module)

        forbidden = {
            "os",
            "psycopg",
            "uvicorn",
            "socket",
            "marketplace.application.auth_startup_provisioning",
            "marketplace.application.auth_runtime_inputs",
            "marketplace.application.auth_runtime_server",
            "marketplace.reference.auth_postgres_application_v1",
        }
        self.assertTrue(forbidden.isdisjoint(top_level_modules))

    def test_exact_m17_5y_surface_and_reviewed_chain_are_present(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'AUTHENTICATED_LOCALHOST_EXECUTION_OPT_IN: Final = (',
            source,
        )
        self.assertIn(
            '"EXECUTE_AUTHENTICATED_MARKETPLACE_LOCALHOST_MVP_V1"',
            source,
        )
        self.assertIn('"--execute-authenticated-localhost"', source)
        self.assertIn('"--authentication-provisioning-directory"', source)
        self.assertIn(
            '"load_marketplace_authentication_startup_provisioning"',
            source,
        )
        self.assertIn(
            '"compose_marketplace_authentication_runtime_inputs"',
            source,
        )
        self.assertIn(
            '"build_reference_authenticated_postgres_marketplace_launch_plan"',
            source,
        )
        self.assertIn(
            '"run_marketplace_authenticated_application_foreground"',
            source,
        )
        self.assertIn(
            '"EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER"',
            source,
        )
        self.assertIn('validator = getattr(runtime_module, "_validate_plan")', source)
        self.assertIn("_read_postgres_dsn(getenv)", source)
        self.assertIn("_load_web_assets(asset_reader)", source)
        self.assertIn("_build_psycopg_connection_factory(dsn)", source)
        self.assertIn("_real_uvicorn_provider()", source)

    def test_no_new_background_public_bind_or_file_mutation_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        blocked_imports = {
            "socket",
            "subprocess",
            "threading",
            "multiprocessing",
            "asyncio",
            "concurrent",
            "webbrowser",
        }
        blocked_calls = {
            "write_text",
            "write_bytes",
            "unlink",
            "mkdir",
            "rmdir",
            "rename",
            "replace",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(
                    all(alias.name.split(".")[0] not in blocked_imports for alias in node.names)
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], blocked_imports)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, blocked_calls)
            self.assertNotIsInstance(node, (ast.While, ast.AsyncFor))

        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('LOCALHOST_HOST: Final = "127.0.0.1"', source)
        self.assertNotIn("0.0.0.0", source)
        self.assertNotIn('LOCALHOST_HOST: Final = "::1"', source)

    def test_existing_m17_2b_contract_strings_are_retained(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'LOCALHOST_EXECUTION_OPT_IN: Final = "EXECUTE_MARKETPLACE_LOCALHOST_MVP_V1"',
            source,
        )
        self.assertIn("M17_2B_DRY_RUN_READY", source)
        self.assertIn("M17_2B_LOCALHOST_FOREGROUND_COMPLETE", source)
        self.assertIn("run_marketplace_application_foreground", source)
        self.assertIn("EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER", source)


if __name__ == "__main__":
    unittest.main()
