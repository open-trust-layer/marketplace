"""Read-only installed dependency-pin verification for Marketplace evaluators.

Reads only the reviewed local pyproject metadata and installed distribution
metadata. Never imports optional dependencies, installs packages, reads
credentials, connects to PostgreSQL or starts a Marketplace runtime.
"""
from __future__ import annotations

import argparse
import importlib.metadata
from pathlib import Path
import re
import stat
import sys
import tomllib
from typing import Callable, Final


MAX_MANIFEST_BYTES: Final = 32 * 1024
_GROUPS: Final = (
    ("postgres", "POSTGRES_DEPENDENCY_PIN_UNVERIFIED"),
    ("local-server", "LOCAL_SERVER_DEPENDENCY_PIN_UNVERIFIED"),
    ("auth-verify", "AUTH_VERIFIER_DEPENDENCY_PIN_UNVERIFIED"),
)
_PIN_RE: Final = re.compile(
    r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"(?:\[(?P<extra>[A-Za-z0-9_-]+)\])?"
    r"==(?P<version>[0-9]+(?:\.[0-9]+){1,3})\Z"
)


class _PinsetUnavailable(Exception):
    """Internal error with no path, dependency or installed-version details."""


def _manifest_pins(root: Path) -> dict[str, tuple[tuple[str, str], ...]]:
    if not root.is_absolute() or not root.is_dir():
        raise _PinsetUnavailable
    path = root / "pyproject.toml"
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_MANIFEST_BYTES:
            raise _PinsetUnavailable
        with path.open("rb") as handle:
            raw = handle.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise _PinsetUnavailable
        manifest = tomllib.loads(raw.decode("utf-8"))
        groups = manifest["project"]["optional-dependencies"]
        if type(groups) is not dict:
            raise _PinsetUnavailable
        result: dict[str, tuple[tuple[str, str], ...]] = {}
        global_pins: dict[str, str] = {}
        for group, _code in _GROUPS:
            specs = groups.get(group)
            if type(specs) is not list or not specs:
                raise _PinsetUnavailable
            expected: list[tuple[str, str]] = []
            for spec in specs:
                if type(spec) is not str:
                    raise _PinsetUnavailable
                match = _PIN_RE.fullmatch(spec)
                if match is None:
                    raise _PinsetUnavailable
                name = re.sub(r"[-_.]+", "-", match["name"]).lower()
                version = match["version"]
                extra = match["extra"]
                if group == "postgres" and (name, extra) != ("psycopg", "binary"):
                    # An ordinary psycopg distribution is insufficient for
                    # the explicitly reviewed psycopg[binary] evaluator lane.
                    raise _PinsetUnavailable
                if extra is not None and (name, extra) != ("psycopg", "binary"):
                    raise _PinsetUnavailable
                for distribution in (
                    (name, f"{name}-binary") if extra == "binary" else (name,)
                ):
                    if distribution in global_pins:
                        raise _PinsetUnavailable
                    global_pins[distribution] = version
                    expected.append((distribution, version))
            result[group] = tuple(expected)
        return result
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, tomllib.TOMLDecodeError):
        raise _PinsetUnavailable from None


def assess_dependency_pins(
    *,
    marketplace_root: str | Path,
    version_finder: Callable[[str], str] = importlib.metadata.version,
) -> tuple[str, ...]:
    """Return non-secret category codes for missing or mismatched pins."""
    try:
        pins = _manifest_pins(Path(marketplace_root))
    except (_PinsetUnavailable, OSError, TypeError, ValueError):
        return ("PINSET_UNAVAILABLE_OR_INVALID",)

    missing: list[str] = []
    for group, code in _GROUPS:
        for name, required_version in pins[group]:
            try:
                installed = version_finder(name)
            except Exception:
                # Do not disclose distribution names, errors or installation paths.
                missing.append(code)
                break
            if type(installed) is not str or installed != required_version:
                missing.append(code)
                break
    return tuple(sorted(set(missing)))


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=FAIL code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedArgumentParser(
        description="Offline Marketplace evaluator dependency-pin metadata check"
    )
    parser.add_argument("--marketplace-root", required=True)
    args = parser.parse_args(argv)
    codes = assess_dependency_pins(marketplace_root=args.marketplace_root)
    if codes:
        print(f"status=BLOCKED codes={','.join(codes)}")
    else:
        print("status=DEPENDENCY_PINS_PRESENT_UNVERIFIED")
    print("pip_invoked=false external_dependencies_imported=false postgres_connection_invoked=false")
    print("server_invoked=false browser_invoked=false credentials_emitted=false runtime_acceptance=false")
    return 1 if codes else 0


if __name__ == "__main__":
    raise SystemExit(main())
