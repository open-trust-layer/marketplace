"""Offline provenance verifier tests: exact revisions, clean roots, redacted failure."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.marketplace_evaluator_source_provenance import (
    _git,
    assess_source_provenance,
    inspect_source,
    main,
)

MAIN_SHA = "a" * 40
OLP_SHA = "b" * 40


class FakeGit:
    def __init__(self, root: Path, *, head: str = MAIN_SHA,
                 status: str = "", index: str = "H tracked.py\x00",
                 failing_command: str | None = None):
        self.root = root.resolve()
        self.head = head
        self.status = status
        self.index = index
        self.failing_command = failing_command
        self.calls: list[list[str]] = []

    def __call__(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(arguments)
        if "--show-toplevel" in arguments:
            command = "root"
            output = str(self.root) + "\n"
        elif "--verify" in arguments:
            command = "head"
            output = self.head + "\n"
        elif "--porcelain=v1" in arguments:
            command = "status"
            output = self.status
        elif "ls-files" in arguments:
            command = "index"
            output = self.index
        else:
            raise AssertionError("unexpected Git command")
        return subprocess.CompletedProcess(
            args=arguments,
            returncode=1 if command == self.failing_command else 0,
            stdout=output,
        )


class MarketplaceEvaluatorSourceProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_exact_clean_checkout_is_matched_not_runtime_accepted(self) -> None:
        fake = FakeGit(self.root)
        self.assertIsNone(inspect_source(self.root, MAIN_SHA, prefix="MARKETPLACE", git_runner=fake))
        self.assertEqual(len(fake.calls), 4)
        self.assertIn("--show-toplevel", fake.calls[0])
        self.assertIn("--verify", fake.calls[1])
        self.assertIn("--untracked-files=all", fake.calls[2])
        self.assertIn("--ignore-submodules=none", fake.calls[2])
        self.assertIn("ls-files", fake.calls[3])
        self.assertIn("-v", fake.calls[3])
        self.assertIn("-z", fake.calls[3])

    def test_git_command_suppresses_optional_locks_and_shell(self) -> None:
        with patch(
            "tools.marketplace_evaluator_source_provenance.subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
        ) as call:
            _git(["-C", str(self.root), "status", "--porcelain=v1"])
        argv = call.call_args.args[0]
        self.assertEqual(argv[:2], ["git", "--no-optional-locks"])
        self.assertIn("core.fsmonitor=false", argv)
        self.assertIn("core.untrackedCache=false", argv)
        self.assertEqual(call.call_args.kwargs["timeout"], 10)
        self.assertEqual(call.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(call.call_args.kwargs["stdout"], subprocess.PIPE)
        self.assertNotIn("shell", call.call_args.kwargs)

    def test_hidden_index_flags_fail_even_with_clean_git_status(self) -> None:
        for index in (
            "S hidden.py\x00",
            "h hidden.py\x00",
            "s hidden.py\x00",
            "H normal.py\x00S hidden.py\x00",
            "M unresolved.py\x00",
        ):
            with self.subTest(tag=index[0]):
                fake = FakeGit(self.root, index=index, status="")
                self.assertEqual(
                    inspect_source(self.root, MAIN_SHA, prefix="MARKETPLACE", git_runner=fake),
                    "MARKETPLACE_INDEX_FLAGS_UNVERIFIED",
                )
                self.assertEqual(len(fake.calls), 4)

    def test_index_records_require_complete_nul_terminated_output(self) -> None:
        for index in ("", "H tracked.py", "H tracked.py\x00H extra.py"):
            with self.subTest(index=repr(index)):
                fake = FakeGit(self.root, index=index)
                self.assertEqual(
                    inspect_source(self.root, MAIN_SHA, prefix="OLP", git_runner=fake),
                    "OLP_INDEX_UNVERIFIED",
                )

    def test_clean_index_with_special_filename_remains_valid(self) -> None:
        fake = FakeGit(self.root, index="H name with whitespace\nand newline\x00")
        self.assertIsNone(
            inspect_source(self.root, MAIN_SHA, prefix="MARKETPLACE", git_runner=fake)
        )

    def test_commit_drift_fails_before_dirty_check(self) -> None:
        fake = FakeGit(self.root, head=OLP_SHA)
        self.assertEqual(
            inspect_source(self.root, MAIN_SHA, prefix="MARKETPLACE", git_runner=fake),
            "MARKETPLACE_REVISION_MISMATCH",
        )
        self.assertEqual(len(fake.calls), 2)

    def test_dirty_tracked_untracked_or_submodule_status_fails(self) -> None:
        for line in (" M web/app.js\n", "?? private-evidence.json\n", " m olp\n"):
            with self.subTest(kind=line[:2]):
                fake = FakeGit(self.root, status=line)
                self.assertEqual(
                    inspect_source(self.root, MAIN_SHA, prefix="MARKETPLACE", git_runner=fake),
                    "MARKETPLACE_TREE_DIRTY",
                )
                self.assertNotIn("private-evidence", "MARKETPLACE_TREE_DIRTY")

    def test_nonroot_git_directory_and_absent_directory_fail_closed(self) -> None:
        other = self.root / "nested"
        other.mkdir()
        fake = FakeGit(self.root)
        self.assertEqual(
            inspect_source(other, MAIN_SHA, prefix="MARKETPLACE", git_runner=fake),
            "MARKETPLACE_ROOT_INVALID",
        )
        self.assertEqual(
            inspect_source(self.root / "absent", MAIN_SHA, prefix="OLP", git_runner=fake),
            "OLP_ROOT_INVALID",
        )
        self.assertEqual(
            inspect_source("relative", MAIN_SHA, prefix="OLP", git_runner=fake),
            "OLP_ROOT_INVALID",
        )

    def test_git_failure_and_timeout_never_echo_input(self) -> None:
        for failed_step in ("root", "head", "status", "index"):
            with self.subTest(step=failed_step):
                fake = FakeGit(self.root, failing_command=failed_step)
                self.assertEqual(
                    inspect_source(self.root, MAIN_SHA, prefix="OLP", git_runner=fake),
                    "OLP_REPOSITORY_UNAVAILABLE",
                )
        def unavailable(_arguments: list[str]) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(["git", "secret/path"], 10)
        self.assertEqual(
            inspect_source(self.root, MAIN_SHA, prefix="OLP", git_runner=unavailable),
            "OLP_REPOSITORY_UNAVAILABLE",
        )

    def test_invalid_sha_rejected_before_git_call(self) -> None:
        for bad in ("", "bad", "a" * 39, "G" * 40, "a" * 40 + "\n"):
            with self.subTest(sha=repr(bad)):
                fake = FakeGit(self.root)
                self.assertEqual(
                    inspect_source(self.root, bad, prefix="MARKETPLACE", git_runner=fake),
                    "EXPECTED_SHA_INVALID",
                )
                self.assertEqual(fake.calls, [])

    def test_both_roots_report_stable_sorted_codes(self) -> None:
        errors = assess_source_provenance(
            marketplace_root=self.root,
            marketplace_sha=MAIN_SHA,
            olp_root=self.root,
            olp_sha=OLP_SHA,
            git_runner=FakeGit(self.root, head=MAIN_SHA, status="?? local/path\n"),
        )
        self.assertEqual(errors, ("MARKETPLACE_TREE_DIRTY", "OLP_REVISION_MISMATCH"))

    def test_cli_has_nonsecret_boundaries_and_no_false_live_pass(self) -> None:
        out = io.StringIO()
        with patch(
            "tools.marketplace_evaluator_source_provenance.assess_source_provenance",
            return_value=(),
        ), redirect_stdout(out):
            result = main([
                "--marketplace-root", str(self.root), "--marketplace-sha", MAIN_SHA,
                "--olp-root", str(self.root), "--olp-sha", OLP_SHA,
            ])
        self.assertEqual(result, 0)
        self.assertIn("status=SOURCE_PROVENANCE_MATCHED_OFFLINE", out.getvalue())
        self.assertIn("runtime_acceptance=false", out.getvalue())
        self.assertNotIn(str(self.root), out.getvalue())
        self.assertNotIn("status=PASS", out.getvalue())

        out = io.StringIO()
        with patch(
            "tools.marketplace_evaluator_source_provenance.assess_source_provenance",
            return_value=("OLP_TREE_DIRTY",),
        ), redirect_stdout(out):
            self.assertEqual(main([
                "--marketplace-root", str(self.root), "--marketplace-sha", MAIN_SHA,
                "--olp-root", str(self.root), "--olp-sha", OLP_SHA,
            ]), 1)
        self.assertIn("status=BLOCKED codes=OLP_TREE_DIRTY", out.getvalue())
        self.assertNotIn(str(self.root), out.getvalue())

    def test_invalid_cli_arguments_do_not_reflect_paths(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            with self.assertRaises(SystemExit) as caught:
                main(["--unrecognized", "secret/path"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(err.getvalue(), "status=FAIL code=ARGUMENT_INVALID\n")


if __name__ == "__main__":
    unittest.main()
