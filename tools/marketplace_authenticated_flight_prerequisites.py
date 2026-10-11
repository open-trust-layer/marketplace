"""Inert prerequisite presence check for a future authenticated Marketplace flight.

This check never opens authentication provisioning or connects to PostgreSQL.
Presence is not correctness, identity verification, CI provenance or live acceptance.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import sys
from typing import Callable, Mapping


DSN_ENV = "MARKETPLACE_POSTGRES_DSN"
MAX_DSN_CHARS = 8192
REQUIRED_MODULES = (
    ("psycopg", "POSTGRES_CLIENT_ABSENT"),
    ("uvicorn", "LOCAL_SERVER_ABSENT"),
    ("cryptography", "AUTH_VERIFIER_ABSENT"),
)


def _absolute_directory_present(raw: str | None) -> bool:
    if type(raw) is not str or not raw or "\x00" in raw:
        return False
    try:
        path = Path(raw)
        return path.is_absolute() and path.is_dir()
    except (OSError, ValueError):
        return False


def assess_prerequisites(
    *,
    provisioning_directory: str | None,
    olp_source_directory: str | None,
    environment: Mapping[str, str],
    module_finder: Callable[[str], object] = importlib.util.find_spec,
) -> tuple[str, ...]:
    """Return sorted non-secret codes; do not examine any credential contents."""
    missing: list[str] = []
    if sys.version_info < (3, 11):
        missing.append("PYTHON_UNSUPPORTED")
    dsn = environment.get(DSN_ENV)
    if type(dsn) is not str or not dsn.strip() or len(dsn) > MAX_DSN_CHARS:
        missing.append("POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH")
    if not _absolute_directory_present(provisioning_directory):
        missing.append("PROVISIONING_DIRECTORY_ABSENT")
    if not _absolute_directory_present(olp_source_directory):
        missing.append("PINNED_OLP_SOURCE_DIRECTORY_ABSENT")
    for name, code in REQUIRED_MODULES:
        try:
            available = module_finder(name) is not None
        except (ImportError, ValueError, AttributeError):
            available = False
        if not available:
            missing.append(code)
    return tuple(sorted(missing))


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        # Do not reflect malformed CLI arguments (which can contain local paths).
        self.exit(2, "status=FAIL code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedArgumentParser(description="Offline Marketplace flight prerequisite presence check")
    parser.add_argument("--provisioning-directory")
    parser.add_argument("--olp-src")
    args = parser.parse_args(argv)
    missing = assess_prerequisites(
        provisioning_directory=args.provisioning_directory,
        olp_source_directory=args.olp_src,
        environment=os.environ,
    )
    if missing:
        print(f"status=BLOCKED codes={','.join(missing)}")
        code = 1
    else:
        print("status=PREREQUISITES_PRESENT_UNVERIFIED")
        code = 0
    print("postgres_connection_invoked=false server_invoked=false browser_invoked=false")
    print("authentication_provisioning_opened=false credentials_emitted=false")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
