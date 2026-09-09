from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/application/auth_startup_provisioning.py"
DOC = ROOT / "docs/m17-5s-auth-startup-provisioning.md"
PACKAGE_GATE = ROOT / "tools/package_artifact_gate.py"


class MarketplaceAuthenticationStartupProvisioningArtifactTests(
    unittest.TestCase
):
    def source(self) -> str:
        return SOURCE.read_text(encoding="utf-8")

    def tree(self) -> ast.Module:
        return ast.parse(self.source())

    def test_exact_profile_fixed_names_and_bounded_reads(self) -> None:
        source = self.source()
        self.assertIn(
            (
                'PROFILE_NAME: Final = '
                '"MARKETPLACE_APPLICATION_AUTH_STARTUP_PROVISIONING_V1"'
            ),
            source,
        )
        self.assertIn('"trust-anchor-manifest.json"', source)
        self.assertIn('"verification-method-claims.json"', source)
        self.assertIn('"verification-method-attestation.bin"', source)
        self.assertIn("handle.read(maximum + 1)", source)
        self.assertIn("AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES", source)
        self.assertIn("AUTH_EVIDENCE_CLAIMS_MAX_BYTES", source)
        self.assertIn("AUTH_EVIDENCE_ATTESTATION_MAX_BYTES", source)

    def test_loader_has_exact_three_bounded_read_calls(self) -> None:
        tree = self.tree()
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name
            == "load_marketplace_authentication_startup_provisioning"
        )
        calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_read_bounded"
        ]
        self.assertEqual(len(calls), 3)
        maxima = [
            call.args[2].id
            for call in calls
            if isinstance(call.args[2], ast.Name)
        ]
        self.assertEqual(
            maxima,
            [
                "AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES",
                "AUTH_EVIDENCE_CLAIMS_MAX_BYTES",
                "AUTH_EVIDENCE_ATTESTATION_MAX_BYTES",
            ],
        )

    def test_only_read_binary_open_is_present(self) -> None:
        opens = [
            node
            for node in ast.walk(self.tree())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ]
        self.assertEqual(len(opens), 1)
        self.assertEqual(len(opens[0].args), 2)
        self.assertIsInstance(opens[0].args[1], ast.Constant)
        self.assertEqual(opens[0].args[1].value, "rb")

    def test_import_boundary_excludes_activation_and_provider_surfaces(self) -> None:
        modules: set[str] = set()
        for node in ast.walk(self.tree()):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
        forbidden = (
            "subprocess",
            "socket",
            "urllib",
            "http",
            "sqlite3",
            "asyncio",
            "launch",
            "runtime_server",
            "provider",
            "auth_static_composition",
            "auth_http_composition",
            "auth_runtime_inputs",
            "auth_asgi_composition",
            "asgi",
        )
        for module in modules:
            with self.subTest(module=module):
                self.assertFalse(any(name in module for name in forbidden))

    def test_source_never_calls_deferred_authentication_capabilities(self) -> None:
        source = self.source()
        for marker in (
            "compose_marketplace_static_authentication",
            "compose_marketplace_authenticated_http",
            "compose_marketplace_authentication_runtime_inputs",
            "compose_marketplace_authenticated_asgi",
            "challenge_bytes(",
            "session_token_bytes(",
            "clock.now(",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_path_safety_and_identity_guards_are_explicit(self) -> None:
        source = self.source()
        required = (
            "os.path.isabs(directory)",
            "os.path.normpath(directory) != directory",
            "os.path.realpath(directory, strict=True)",
            "os.path.commonpath((directory, real))",
            "stat.S_ISREG(info.st_mode)",
            "stat.S_ISLNK(info.st_mode)",
            "st_file_attributes",
            "_same_path_handle_identity(expected, opened)",
            "after_read != opened",
            "after_path != expected",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_runtime_and_auth_entrypoints_do_not_select_m17_5s(self) -> None:
        paths = (
            "src/marketplace/application/auth_static_composition.py",
            "src/marketplace/application/auth_http_composition.py",
            "src/marketplace/application/auth_runtime_inputs.py",
            "src/marketplace/application/auth_asgi_composition.py",
            "src/marketplace/application/asgi.py",
            "src/marketplace/application/launch.py",
            "src/marketplace/application/runtime_server.py",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertNotIn("auth_startup_provisioning", text)

    def test_package_gate_and_documented_boundary_are_present(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_startup_provisioning.py"',
            gate,
        )
        document = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_STARTUP_PROVISIONING_V1",
            "exactly three fixed",
            "max + 1",
            "symlink/reparse",
            "unstable file identity",
            "no trust verification",
            "no launch",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, document)


if __name__ == "__main__":
    unittest.main()
