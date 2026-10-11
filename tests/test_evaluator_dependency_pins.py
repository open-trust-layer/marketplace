"""Inert evaluator dependency metadata checks, including binary extra pins."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.marketplace_evaluator_dependency_pins import (
    MAX_MANIFEST_BYTES,
    assess_dependency_pins,
    main,
)


GOOD_MANIFEST = """[project.optional-dependencies]
postgres = ["psycopg[binary]==3.3.5"]
local-server = ["uvicorn==0.52.4", "click==8.5.0", "h11==0.16.0"]
auth-verify = ["cryptography==50.0.1"]
"""
INSTALLED = {
    "psycopg": "3.3.5",
    "psycopg-binary": "3.3.5",
    "uvicorn": "0.52.4",
    "click": "8.5.0",
    "h11": "0.16.0",
    "cryptography": "50.0.1",
}


class EvaluatorDependencyPinTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.write_manifest(GOOD_MANIFEST)

    def write_manifest(self, value: str) -> None:
        (self.root / "pyproject.toml").write_text(value, encoding="utf-8")

    def test_exact_reviewed_dependencies_including_psycopg_binary(self) -> None:
        names: list[str] = []

        def resolver(name: str) -> str:
            names.append(name)
            return INSTALLED[name]

        self.assertEqual(
            assess_dependency_pins(marketplace_root=self.root, version_finder=resolver),
            (),
        )
        self.assertEqual(set(names), set(INSTALLED))

    def test_missing_and_mismatched_versions_fail_by_group_without_leaks(self) -> None:
        installed = dict(INSTALLED)
        installed["psycopg-binary"] = "3.3.4"
        installed["uvicorn"] = "0.51.0"
        del installed["cryptography"]

        def resolver(name: str) -> str:
            return installed[name]

        self.assertEqual(
            assess_dependency_pins(marketplace_root=self.root, version_finder=resolver),
            (
                "AUTH_VERIFIER_DEPENDENCY_PIN_UNVERIFIED",
                "LOCAL_SERVER_DEPENDENCY_PIN_UNVERIFIED",
                "POSTGRES_DEPENDENCY_PIN_UNVERIFIED",
            ),
        )

    def test_wrong_binary_extra_cannot_hide_behind_psycopg_metadata(self) -> None:
        def resolver(name: str) -> str:
            if name == "psycopg-binary":
                raise RuntimeError("private site-packages path")
            return INSTALLED[name]

        self.assertEqual(
            assess_dependency_pins(marketplace_root=self.root, version_finder=resolver),
            ("POSTGRES_DEPENDENCY_PIN_UNVERIFIED",),
        )

    def test_disallowed_or_unpinned_specs_fail_closed(self) -> None:
        bad_specs = (
            "psycopg[binary]>=3.3.5",
            "psycopg[secret]==3.3.5",
            "psycopg==3.3.5",
            "psycopg[binary]==3.3.5; platform_system=='Windows'",
            "psycopg[binary]==3.3.5\ntext",
        )
        for bad in bad_specs:
            with self.subTest(spec=bad):
                self.write_manifest(GOOD_MANIFEST.replace("psycopg[binary]==3.3.5", bad))
                self.assertEqual(
                    assess_dependency_pins(marketplace_root=self.root),
                    ("PINSET_UNAVAILABLE_OR_INVALID",),
                )

    def test_missing_empty_or_duplicate_group_fails_closed(self) -> None:
        for manifest in (
            GOOD_MANIFEST.replace("auth-verify = [\"cryptography==50.0.1\"]", ""),
            GOOD_MANIFEST.replace("auth-verify = [\"cryptography==50.0.1\"]", "auth-verify = []"),
            GOOD_MANIFEST.replace(
                "auth-verify = [\"cryptography==50.0.1\"]",
                "auth-verify = [\"uvicorn==0.52.4\"]",
            ),
        ):
            with self.subTest(manifest_len=len(manifest)):
                self.write_manifest(manifest)
                self.assertEqual(
                    assess_dependency_pins(marketplace_root=self.root),
                    ("PINSET_UNAVAILABLE_OR_INVALID",),
                )

    def test_manifest_malformed_too_large_absent_or_symlink_fails_closed(self) -> None:
        self.write_manifest("not-toml")
        self.assertEqual(assess_dependency_pins(marketplace_root=self.root), ("PINSET_UNAVAILABLE_OR_INVALID",))
        self.write_manifest("x" * (MAX_MANIFEST_BYTES + 1))
        self.assertEqual(assess_dependency_pins(marketplace_root=self.root), ("PINSET_UNAVAILABLE_OR_INVALID",))
        (self.root / "pyproject.toml").unlink()
        self.assertEqual(assess_dependency_pins(marketplace_root=self.root), ("PINSET_UNAVAILABLE_OR_INVALID",))
        (self.root / "actual.toml").write_text(GOOD_MANIFEST, encoding="utf-8")
        try:
            (self.root / "pyproject.toml").symlink_to(self.root / "actual.toml")
        except OSError:
            self.skipTest("filesystem cannot create symlinks")
        self.assertEqual(assess_dependency_pins(marketplace_root=self.root), ("PINSET_UNAVAILABLE_OR_INVALID",))

    def test_absolute_root_required(self) -> None:
        self.assertEqual(assess_dependency_pins(marketplace_root="relative"), ("PINSET_UNAVAILABLE_OR_INVALID",))
        self.assertEqual(assess_dependency_pins(marketplace_root=self.root / "missing"), ("PINSET_UNAVAILABLE_OR_INVALID",))
        self.assertEqual(assess_dependency_pins(marketplace_root=None), ("PINSET_UNAVAILABLE_OR_INVALID",))

    def test_cli_redacts_paths_and_does_not_claim_runtime_acceptance(self) -> None:
        out = io.StringIO()
        with patch(
            "tools.marketplace_evaluator_dependency_pins.assess_dependency_pins",
            return_value=(),
        ), redirect_stdout(out):
            self.assertEqual(main(["--marketplace-root", str(self.root)]), 0)
        self.assertIn("status=DEPENDENCY_PINS_PRESENT_UNVERIFIED", out.getvalue())
        self.assertIn("external_dependencies_imported=false", out.getvalue())
        self.assertIn("runtime_acceptance=false", out.getvalue())
        self.assertNotIn(str(self.root), out.getvalue())
        self.assertNotIn("status=PASS", out.getvalue())

        out = io.StringIO()
        with patch(
            "tools.marketplace_evaluator_dependency_pins.assess_dependency_pins",
            return_value=("POSTGRES_DEPENDENCY_PIN_UNVERIFIED",),
        ), redirect_stdout(out):
            self.assertEqual(main(["--marketplace-root", str(self.root)]), 1)
        self.assertIn("status=BLOCKED codes=POSTGRES_DEPENDENCY_PIN_UNVERIFIED", out.getvalue())
        self.assertNotIn(str(self.root), out.getvalue())

    def test_malformed_cli_argument_is_redacted(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            with self.assertRaises(SystemExit) as caught:
                main(["--unknown", "private/credentials"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(err.getvalue(), "status=FAIL code=ARGUMENT_INVALID\n")


if __name__ == "__main__":
    unittest.main()
