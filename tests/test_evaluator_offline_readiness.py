"""Composition and redaction tests for the source-only evaluator readiness tool."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from unittest.mock import patch
import unittest

from tools.marketplace_evaluator_offline_readiness import (
    OfflineReadiness,
    assess_offline_readiness,
    main,
    render_receipt,
)


MAIN_SHA = "a" * 40
OLP_SHA = "b" * 40


def _args() -> dict[str, object]:
    return {
        "marketplace_root": "/synthetic/local/marketplace",
        "marketplace_sha": MAIN_SHA,
        "olp_root": "/synthetic/local/olp",
        "olp_sha": OLP_SHA,
        "provisioning_directory": "/synthetic/nonsecret/auth",
        "environment": {"MARKETPLACE_POSTGRES_DSN": "private-never-print-DSN"},
    }


class OfflineReadinessTests(unittest.TestCase):
    def test_all_existing_checks_are_composed_with_exact_inputs(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def source_check(**kwargs: object) -> tuple[str, ...]:
            calls.append(("source", kwargs))
            return ()

        def dependency_check(**kwargs: object) -> tuple[str, ...]:
            calls.append(("dependency", kwargs))
            return ()

        def prerequisite_check(**kwargs: object) -> tuple[str, ...]:
            calls.append(("prerequisite", kwargs))
            return ()

        result = assess_offline_readiness(
            **_args(),
            source_check=source_check,
            dependency_check=dependency_check,
            prerequisite_check=prerequisite_check,
        )
        self.assertTrue(result.all_present_unverified)
        self.assertEqual([kind for kind, _ in calls], ["source", "dependency", "prerequisite"])
        self.assertEqual(calls[0][1]["marketplace_sha"], MAIN_SHA)
        self.assertEqual(calls[0][1]["olp_sha"], OLP_SHA)
        self.assertEqual(calls[1][1], {"marketplace_root": "/synthetic/local/marketplace"})
        self.assertEqual(calls[2][1]["olp_source_directory"], str(Path("/synthetic/local/olp") / "src"))
        self.assertEqual(calls[2][1]["provisioning_directory"], "/synthetic/nonsecret/auth")
        self.assertEqual(calls[2][1]["environment"], _args()["environment"])

    def test_mixed_failures_are_reported_without_false_success(self) -> None:
        result = assess_offline_readiness(
            **_args(),
            source_check=lambda **_kwargs: ("OLP_REVISION_MISMATCH",),
            dependency_check=lambda **_kwargs: ("POSTGRES_DEPENDENCY_PIN_UNVERIFIED",),
            prerequisite_check=lambda **_kwargs: ("PROVISIONING_DIRECTORY_ABSENT",),
        )
        self.assertFalse(result.all_present_unverified)
        rendered = render_receipt(result)
        self.assertIn("status=BLOCKED", rendered)
        self.assertIn("source_provenance=BLOCKED:OLP_REVISION_MISMATCH", rendered)
        self.assertIn("dependency_pins=BLOCKED:POSTGRES_DEPENDENCY_PIN_UNVERIFIED", rendered)
        self.assertIn("prerequisites=BLOCKED:PROVISIONING_DIRECTORY_ABSENT", rendered)
        self.assertIn("runtime_acceptance=false", rendered)
        self.assertNotIn("private-never-print", rendered)

    def test_exception_does_not_skip_other_checks_or_leak_exception(self) -> None:
        completed: list[str] = []

        def source_check(**_kwargs: object) -> object:
            raise RuntimeError("DSN=secret-token key=/private/path")

        def dependency_check(**_kwargs: object) -> tuple[str, ...]:
            completed.append("dependency")
            return ("LOCAL_SERVER_DEPENDENCY_PIN_UNVERIFIED",)

        def prerequisite_check(**_kwargs: object) -> tuple[str, ...]:
            completed.append("prerequisite")
            return ()

        result = assess_offline_readiness(
            **_args(),
            source_check=source_check,
            dependency_check=dependency_check,
            prerequisite_check=prerequisite_check,
        )
        self.assertEqual(completed, ["dependency", "prerequisite"])
        rendered = render_receipt(result)
        self.assertIn("source_provenance=BLOCKED:SOURCE_CHECK_UNAVAILABLE", rendered)
        self.assertIn("dependency_pins=BLOCKED:LOCAL_SERVER_DEPENDENCY_PIN_UNVERIFIED", rendered)
        self.assertNotIn("secret-token", rendered)
        self.assertNotIn("/private/path", rendered)

    def test_untrusted_diagnostic_strings_are_redacted(self) -> None:
        result = assess_offline_readiness(
            **_args(),
            source_check=lambda **_kwargs: ("MARKETPLACE_TREE_DIRTY", "/private/credentials"),
            dependency_check=lambda **_kwargs: ("cryptography==private",),
            prerequisite_check=lambda **_kwargs: "POSTGRES_CLIENT_ABSENT",
        )
        rendered = render_receipt(result)
        self.assertIn("SOURCE_CHECK_UNAVAILABLE", rendered)
        self.assertIn("DEPENDENCY_CHECK_UNAVAILABLE", rendered)
        self.assertIn("PREREQUISITE_CHECK_UNAVAILABLE", rendered)
        self.assertNotIn("/private/", rendered)
        self.assertNotIn("cryptography==", rendered)

    def test_duplicates_are_sorted_and_stable(self) -> None:
        result = assess_offline_readiness(
            **_args(),
            source_check=lambda **_kwargs: (),
            dependency_check=lambda **_kwargs: (
                "POSTGRES_DEPENDENCY_PIN_UNVERIFIED",
                "AUTH_VERIFIER_DEPENDENCY_PIN_UNVERIFIED",
                "POSTGRES_DEPENDENCY_PIN_UNVERIFIED",
            ),
            prerequisite_check=lambda **_kwargs: (),
        )
        self.assertEqual(result.dependency_codes, (
            "AUTH_VERIFIER_DEPENDENCY_PIN_UNVERIFIED",
            "POSTGRES_DEPENDENCY_PIN_UNVERIFIED",
        ))

    def test_render_present_never_suggests_runtime_accepted(self) -> None:
        receipt = OfflineReadiness((), (), ())
        output = render_receipt(receipt)
        self.assertIn("status=OFFLINE_CHECKS_PRESENT_UNVERIFIED", output)
        self.assertIn("source_provenance=PRESENT_UNVERIFIED", output)
        self.assertIn("dependency_pins=PRESENT_UNVERIFIED", output)
        self.assertIn("prerequisites=PRESENT_UNVERIFIED", output)
        self.assertIn("postgres_connection_invoked=false", output)
        self.assertIn("auth_provisioning_opened=false", output)
        self.assertNotIn("status=PASS", output)
        self.assertNotIn("status=READY", output)

    def test_cli_success_and_failure_exit_codes(self) -> None:
        argv = [
            "--marketplace-root", "/private/marketplace", "--marketplace-sha", MAIN_SHA,
            "--olp-root", "/private/olp", "--olp-sha", OLP_SHA,
        ]
        out = io.StringIO()
        with patch(
            "tools.marketplace_evaluator_offline_readiness.assess_offline_readiness",
            return_value=OfflineReadiness((), (), ()),
        ), redirect_stdout(out):
            self.assertEqual(main(argv), 0)
        self.assertNotIn("/private/", out.getvalue())
        self.assertIn("status=OFFLINE_CHECKS_PRESENT_UNVERIFIED", out.getvalue())

        out = io.StringIO()
        with patch(
            "tools.marketplace_evaluator_offline_readiness.assess_offline_readiness",
            return_value=OfflineReadiness(("EXPECTED_SHA_INVALID",), (), ()),
        ), redirect_stdout(out):
            self.assertEqual(main(argv), 1)
        self.assertIn("status=BLOCKED", out.getvalue())

    def test_cli_malformed_options_are_redacted(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as caught:
            main(["--bad-option", "private-token"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(err.getvalue(), "status=FAIL code=ARGUMENT_INVALID\n")


if __name__ == "__main__":
    unittest.main()
