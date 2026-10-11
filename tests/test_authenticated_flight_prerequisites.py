"""Inert, privacy-preserving checks for #525 evaluator prerequisites."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.marketplace_authenticated_flight_prerequisites import (
    DSN_ENV,
    MAX_DSN_CHARS,
    assess_prerequisites,
    main,
)


class AuthenticatedFlightPrerequisitesTests(unittest.TestCase):
    def test_present_prerequisites_are_unverified_not_runtime_accepted(self) -> None:
        with TemporaryDirectory() as directory:
            checked = assess_prerequisites(
                provisioning_directory=directory,
                olp_source_directory=directory,
                environment={DSN_ENV: "synthetic non-live DSN"},
                module_finder=lambda _module: object(),
            )
        self.assertEqual(checked, ())

    def test_missing_prerequisites_use_sorted_nonsecret_codes(self) -> None:
        missing = assess_prerequisites(
            provisioning_directory=None,
            olp_source_directory=None,
            environment={},
            module_finder=lambda _module: None,
        )
        self.assertEqual(
            missing,
            (
                "AUTH_VERIFIER_ABSENT",
                "LOCAL_SERVER_ABSENT",
                "PINNED_OLP_SOURCE_DIRECTORY_ABSENT",
                "POSTGRES_CLIENT_ABSENT",
                "POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH",
                "PROVISIONING_DIRECTORY_ABSENT",
            ),
        )

    def test_dsn_presence_only_never_echoes_values(self) -> None:
        with TemporaryDirectory() as directory:
            for value in ("", "  ", "x" * (MAX_DSN_CHARS + 1)):
                with self.subTest(length=len(value)):
                    result = assess_prerequisites(
                        provisioning_directory=directory,
                        olp_source_directory=directory,
                        environment={DSN_ENV: value},
                        module_finder=lambda _name: object(),
                    )
                    self.assertEqual(result, ("POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH",))
                    self.assertNotIn(value or "private", ",".join(result))

    def test_paths_must_be_existing_absolute_directories(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            filename = root / "provisioning.file"
            filename.write_text("synthetic", encoding="utf-8")
            for invalid in (None, "", "relative", str(filename), str(root / "absent"), "nul\x00path"):
                with self.subTest(value=repr(invalid)):
                    result = assess_prerequisites(
                        provisioning_directory=invalid,
                        olp_source_directory=directory,
                        environment={DSN_ENV: "synthetic"},
                        module_finder=lambda _name: object(),
                    )
                    self.assertIn("PROVISIONING_DIRECTORY_ABSENT", result)
                    self.assertNotIn(str(root), ",".join(result))

    def test_module_discovery_exception_is_nonsecret_absent(self) -> None:
        with TemporaryDirectory() as directory:
            def broken_finder(_name: str) -> object:
                raise ImportError("private module environment detail")

            result = assess_prerequisites(
                provisioning_directory=directory,
                olp_source_directory=directory,
                environment={DSN_ENV: "synthetic"},
                module_finder=broken_finder,
            )
        self.assertEqual(
            result, ("AUTH_VERIFIER_ABSENT", "LOCAL_SERVER_ABSENT", "POSTGRES_CLIENT_ABSENT")
        )

    def test_cli_status_is_inert_and_redacted(self) -> None:
        output = io.StringIO()
        with patch(
            "tools.marketplace_authenticated_flight_prerequisites.assess_prerequisites",
            return_value=("POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH",),
        ), redirect_stdout(output):
            result = main(["--provisioning-directory", "private/path", "--olp-src", "private/olp"])
        self.assertEqual(result, 1)
        self.assertIn("status=BLOCKED codes=POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH", output.getvalue())
        self.assertIn("postgres_connection_invoked=false", output.getvalue())
        self.assertIn("browser_invoked=false", output.getvalue())
        self.assertIn("credentials_emitted=false", output.getvalue())
        self.assertNotIn("private/", output.getvalue())

        output = io.StringIO()
        with patch(
            "tools.marketplace_authenticated_flight_prerequisites.assess_prerequisites",
            return_value=(),
        ), redirect_stdout(output):
            self.assertEqual(main([]), 0)
        self.assertIn("status=PREREQUISITES_PRESENT_UNVERIFIED", output.getvalue())
        self.assertNotIn("status=PASS", output.getvalue())

    def test_invalid_cli_arguments_do_not_reflect_paths(self) -> None:
        error_output = io.StringIO()
        with redirect_stderr(error_output):
            with self.assertRaises(SystemExit) as exit_state:
                main(["--unknown", "secret/path"])
        self.assertEqual(exit_state.exception.code, 2)
        self.assertEqual(error_output.getvalue(), "status=FAIL code=ARGUMENT_INVALID\n")


if __name__ == "__main__":
    unittest.main()
