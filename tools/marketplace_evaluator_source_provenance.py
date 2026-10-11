"""Offline, redacted Git source provenance check for a Marketplace evaluator.

This tool reads local Git metadata only. It does not fetch, modify the
checkout, run application code, connect to PostgreSQL or start a browser.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
from typing import Callable, Final


_SHA: Final = re.compile(r"^[0-9a-f]{40}$")
_GIT_TIMEOUT_SECONDS: Final = 10


def _git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    # Never use a shell or surface raw stdout/stderr. Do not refresh the index
    # or activate a filesystem-monitor process during a read-only inspection.
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
         "-c", "core.untrackedCache=false", *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=_GIT_TIMEOUT_SECONDS,
    )


def inspect_source(
    root: str | Path,
    expected_sha: str,
    *,
    prefix: str,
    git_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] = _git,
) -> str | None:
    """Return a stable error code, or None for an exact and clean local tree."""
    if type(expected_sha) is not str or _SHA.fullmatch(expected_sha) is None:
        return "EXPECTED_SHA_INVALID"
    try:
        path = Path(root)
        if not path.is_absolute() or not path.is_dir():
            return f"{prefix}_ROOT_INVALID"
        resolved = path.resolve(strict=True)
        command = ["-C", str(resolved)]
        top = git_runner([*command, "rev-parse", "--show-toplevel"])
        if top.returncode != 0 or not top.stdout.strip():
            return f"{prefix}_REPOSITORY_UNAVAILABLE"
        if Path(top.stdout.strip()).resolve(strict=True) != resolved:
            return f"{prefix}_ROOT_INVALID"

        head = git_runner([*command, "rev-parse", "--verify", "HEAD"])
        if head.returncode != 0 or _SHA.fullmatch(head.stdout.strip()) is None:
            return f"{prefix}_REPOSITORY_UNAVAILABLE"
        if head.stdout.strip() != expected_sha:
            return f"{prefix}_REVISION_MISMATCH"

        dirty = git_runner([
            *command, "status", "--porcelain=v1",
            "--untracked-files=all", "--ignore-submodules=none",
        ])
        if dirty.returncode != 0:
            return f"{prefix}_REPOSITORY_UNAVAILABLE"
        if dirty.stdout:
            return f"{prefix}_TREE_DIRTY"

        # Git status can report a falsely clean tree when local index flags
        # suppress checking modified working-tree files. Reject those flags
        # (and any unexpected index state), rather than accept hidden changes.
        # -z keeps filenames opaque and unambiguous; none are ever printed.
        entries = git_runner([*command, "ls-files", "-v", "-z"])
        if entries.returncode != 0:
            return f"{prefix}_REPOSITORY_UNAVAILABLE"
        if not entries.stdout or not entries.stdout.endswith("\\x00"):
            return f"{prefix}_INDEX_UNVERIFIED"
        if any(
            not entry.startswith("H ")
            for entry in entries.stdout.split("\\x00") if entry
        ):
            return f"{prefix}_INDEX_FLAGS_UNVERIFIED"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return f"{prefix}_REPOSITORY_UNAVAILABLE"
    return None


def assess_source_provenance(
    *,
    marketplace_root: str | Path,
    marketplace_sha: str,
    olp_root: str | Path,
    olp_sha: str,
    git_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] = _git,
) -> tuple[str, ...]:
    """Check both independent local sources, never echoing paths or Git output."""
    errors = (
        inspect_source(marketplace_root, marketplace_sha, prefix="MARKETPLACE", git_runner=git_runner),
        inspect_source(olp_root, olp_sha, prefix="OLP", git_runner=git_runner),
    )
    return tuple(sorted(code for code in errors if code is not None))


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=FAIL code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedArgumentParser(description="Offline Marketplace/OLP source provenance")
    parser.add_argument("--marketplace-root", required=True)
    parser.add_argument("--marketplace-sha", required=True)
    parser.add_argument("--olp-root", required=True)
    parser.add_argument("--olp-sha", required=True)
    options = parser.parse_args(argv)
    errors = assess_source_provenance(
        marketplace_root=options.marketplace_root,
        marketplace_sha=options.marketplace_sha,
        olp_root=options.olp_root,
        olp_sha=options.olp_sha,
    )
    if errors:
        print(f"status=BLOCKED codes={','.join(errors)}")
    else:
        print("status=SOURCE_PROVENANCE_MATCHED_OFFLINE")
    print("network_invoked=false postgres_connection_invoked=false server_invoked=false browser_invoked=false")
    print("runtime_acceptance=false credentials_emitted=false")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
