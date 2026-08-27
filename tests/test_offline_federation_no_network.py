from __future__ import annotations

import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    Path("src/marketplace/runtime/federation.py"),
    Path("src/marketplace/reference/federation_v1.py"),
)
FORBIDDEN_IMPORT_ROOTS = {
    "aiohttp",
    "ftplib",
    "http",
    "httpx",
    "requests",
    "smtplib",
    "socket",
    "ssl",
    "subprocess",
    "urllib",
    "websockets",
}
FORBIDDEN_DYNAMIC_CALLS = {"__import__", "eval", "exec"}


class OfflineFederationNoNetworkTests(unittest.TestCase):
    def test_m24_federation_modules_have_no_concrete_network_or_process_imports(self):
        for relative in TARGETS:
            source = (REPO_ROOT / relative).read_text(encoding="utf-8-sig")
            tree = ast.parse(source, filename=str(relative))
            imported_roots: set[str] = set()
            dynamic_calls: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".", 1)[0])
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_DYNAMIC_CALLS:
                        dynamic_calls.add(node.func.id)
            self.assertEqual(
                imported_roots & FORBIDDEN_IMPORT_ROOTS,
                set(),
                f"{relative} introduced a concrete network/process import",
            )
            self.assertEqual(
                dynamic_calls,
                set(),
                f"{relative} introduced dynamic execution/import",
            )

    def test_offline_service_exposes_only_prepare_validate_and_accept_operations(self):
        source = (REPO_ROOT / "src/marketplace/runtime/federation.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        service = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "OfflineFederationService"
        )
        methods = {
            node.name
            for node in service.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertEqual(methods, {"__init__", "prepare", "validate_page", "accept_page"})
        self.assertTrue({"send", "fetch", "connect", "request", "transmit"}.isdisjoint(methods))


if __name__ == "__main__":
    unittest.main()
