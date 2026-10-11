"""Aggregate existing inert Marketplace evaluator checks into one redacted receipt.

Local Git metadata, package distribution metadata, optional dependency module
discovery, environment-variable presence, and directory existence only.
No credential file opens, dependency installs, imports of optional packages,
database connections, sockets, browser launches or runtime initialization.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Callable, Mapping

from tools.marketplace_authenticated_flight_prerequisites import assess_prerequisites
from tools.marketplace_evaluator_dependency_pins import assess_dependency_pins
from tools.marketplace_evaluator_source_provenance import assess_source_provenance


# Allow only reviewed diagnostic codes from the three existing checkers.
_SOURCE_CODES = frozenset({
    "EXPECTED_SHA_INVALID",
    *(f"{prefix}_{suffix}" for prefix in ("MARKETPLACE", "OLP") for suffix in (
        "ROOT_INVALID", "REPOSITORY_UNAVAILABLE", "REVISION_MISMATCH",
        "TREE_DIRTY", "INDEX_UNVERIFIED", "INDEX_FLAGS_UNVERIFIED",
    )),
})
_DEPENDENCY_CODES = frozenset({
    "PINSET_UNAVAILABLE_OR_INVALID",
    "POSTGRES_DEPENDENCY_PIN_UNVERIFIED",
    "LOCAL_SERVER_DEPENDENCY_PIN_UNVERIFIED",
    "AUTH_VERIFIER_DEPENDENCY_PIN_UNVERIFIED",
})
_PREREQUISITE_CODES = frozenset({
    "PYTHON_UNSUPPORTED",
    "POSTGRES_DSN_ABSENT_OR_INVALID_LENGTH",
    "PROVISIONING_DIRECTORY_ABSENT",
    "PINNED_OLP_SOURCE_DIRECTORY_ABSENT",
    "POSTGRES_CLIENT_ABSENT",
    "LOCAL_SERVER_ABSENT",
    "AUTH_VERIFIER_ABSENT",
})


@dataclass(frozen=True)
class OfflineReadiness:
    source_codes: tuple[str, ...]
    dependency_codes: tuple[str, ...]
    prerequisite_codes: tuple[str, ...]

    @property
    def all_present_unverified(self) -> bool:
        return not (self.source_codes or self.dependency_codes or self.prerequisite_codes)


def _checked_codes(
    check: Callable[[], object],
    *,
    allowed: frozenset[str],
    fallback: str,
) -> tuple[str, ...]:
    """Fail closed and emit no imported exception messages or unforeseen codes."""
    try:
        result = check()
        if type(result) not in (tuple, list):
            return (fallback,)
        if any(type(code) is not str or code not in allowed for code in result):
            return (fallback,)
        return tuple(sorted(set(result)))
    except Exception:
        return (fallback,)


def assess_offline_readiness(
    *,
    marketplace_root: str,
    marketplace_sha: str,
    olp_root: str,
    olp_sha: str,
    provisioning_directory: str | None,
    environment: Mapping[str, str],
    source_check: Callable[..., object] = assess_source_provenance,
    dependency_check: Callable[..., object] = assess_dependency_pins,
    prerequisite_check: Callable[..., object] = assess_prerequisites,
) -> OfflineReadiness:
    """Independently evaluate all source-only gates, regardless of failures."""
    source_codes = _checked_codes(
        lambda: source_check(
            marketplace_root=marketplace_root,
            marketplace_sha=marketplace_sha,
            olp_root=olp_root,
            olp_sha=olp_sha,
        ),
        allowed=_SOURCE_CODES,
        fallback="SOURCE_CHECK_UNAVAILABLE",
    )
    dependency_codes = _checked_codes(
        lambda: dependency_check(marketplace_root=marketplace_root),
        allowed=_DEPENDENCY_CODES,
        fallback="DEPENDENCY_CHECK_UNAVAILABLE",
    )
    prerequisite_codes = _checked_codes(
        lambda: prerequisite_check(
            provisioning_directory=provisioning_directory,
            olp_source_directory=str(Path(olp_root) / "src"),
            environment=environment,
        ),
        allowed=_PREREQUISITE_CODES,
        fallback="PREREQUISITE_CHECK_UNAVAILABLE",
    )
    return OfflineReadiness(source_codes, dependency_codes, prerequisite_codes)


def render_receipt(receipt: OfflineReadiness) -> str:
    """Emit fixed-marker lines only; never stringify paths or supplied objects."""
    status = "OFFLINE_CHECKS_PRESENT_UNVERIFIED" if receipt.all_present_unverified else "BLOCKED"
    lines = [f"status={status}"]
    for key, codes in (
        ("source_provenance", receipt.source_codes),
        ("dependency_pins", receipt.dependency_codes),
        ("prerequisites", receipt.prerequisite_codes),
    ):
        lines.append(f"{key}={'PRESENT_UNVERIFIED' if not codes else 'BLOCKED:' + ','.join(codes)}")
    lines.append(
        "network_invoked=false pip_invoked=false optional_packages_imported=false"
    )
    lines.append(
        "auth_provisioning_opened=false postgres_connection_invoked=false "
        "server_invoked=false browser_invoked=false"
    )
    lines.append("credentials_emitted=false runtime_acceptance=false")
    return "\n".join(lines)


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=FAIL code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedArgumentParser(
        description="Read-only, offline Marketplace evaluator readiness summary"
    )
    parser.add_argument("--marketplace-root", required=True)
    parser.add_argument("--marketplace-sha", required=True)
    parser.add_argument("--olp-root", required=True)
    parser.add_argument("--olp-sha", required=True)
    parser.add_argument("--provisioning-directory")
    args = parser.parse_args(argv)

    result = assess_offline_readiness(
        marketplace_root=args.marketplace_root,
        marketplace_sha=args.marketplace_sha,
        olp_root=args.olp_root,
        olp_sha=args.olp_sha,
        provisioning_directory=args.provisioning_directory,
        environment=os.environ,
    )
    print(render_receipt(result))
    return 0 if result.all_present_unverified else 1


if __name__ == "__main__":
    raise SystemExit(main())
