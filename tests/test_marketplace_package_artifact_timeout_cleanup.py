"""A wheel-build timeout must not leave its own child holding disposable files."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

from package_artifact_gate import ArtifactGateError, _run_bounded_build


class ArtifactBuildTreeCleanupTests(unittest.TestCase):
    def test_short_successful_build_completes(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            _run_bounded_build(
                [sys.executable, "-c", "print('OK')"],
                cwd=Path(name),
                env=os.environ,
                timeout=8,
                label="isolated test wheel",
            )

    def test_failed_build_still_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(ArtifactGateError) as caught:
                _run_bounded_build(
                    [sys.executable, "-c", "raise SystemExit(23)"],
                    cwd=Path(name),
                    env=os.environ,
                    timeout=8,
                    label="isolated test wheel",
                )
            self.assertEqual(caught.exception.code, "COMMAND_FAILED")

    def test_timeout_kills_own_child_tree_before_temporary_cleanup(self) -> None:
        # No production PIDs, existing processes, or repository files are used.
        # The grandchild holds a file open under the temporary build tree.
        # The old subprocess.run(timeout=...) left it running on Windows.
        with tempfile.TemporaryDirectory(prefix="marketplace-wheel-child-test-") as name:
            root = Path(name)
            held = root / "held.txt"
            ready = root / "ready.txt"
            grandchild = (
                "import pathlib,sys,time;"
                "f=open(sys.argv[1], 'w+b');"
                "f.write(b'held');f.flush();"
                "pathlib.Path(sys.argv[2]).write_text('ready');"
                "time.sleep(20)"
            )
            parent = (
                "import subprocess,sys,time;"
                "subprocess.Popen([sys.executable,'-c',sys.argv[3],sys.argv[1],sys.argv[2]],"
                " stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
                "time.sleep(20)"
            )
            with self.assertRaises(ArtifactGateError) as caught:
                _run_bounded_build(
                    [sys.executable, "-c", parent, str(held), str(ready), grandchild],
                    cwd=root,
                    env=os.environ,
                    timeout=3,
                    label="isolated wheel build timeout test",
                )
            self.assertEqual(caught.exception.code, "COMMAND_TIMEOUT")
            self.assertTrue(ready.exists(), "grandchild must have started before timeout")
        # Successfully deleting the temporary tree is part of the assertion:
        # no descendant can hold it locked after the time limit.


if __name__ == "__main__":
    unittest.main()
