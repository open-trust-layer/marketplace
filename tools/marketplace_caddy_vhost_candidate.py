"""Source-only, exact-host Caddy candidate for a separately approved private Web alpha.

Import, default invocation and candidate rendering perform no filesystem, network,
credential, subprocess, service or configuration mutation. This module never
deploys or validates live TLS, a proxy, a database or the production app.
"""
from __future__ import annotations

import sys
from typing import Final, Sequence


CANONICAL_HOST: Final = "marketplace.open-trust-layer.org"
CANONICAL_ORIGIN: Final = "https://marketplace.open-trust-layer.org/"
EXACT_RENDER_OPT_IN: Final = "RENDER_REVIEW_ONLY_MARKETPLACE_CADDY_CANDIDATE_V1"
MIN_PRIVATE_PORT: Final = 20000
MAX_PRIVATE_PORT: Final = 60999

INERT_STATUS: Final = "status=INERT_CADDY_CANDIDATE_NOT_RENDERED"
BLOCKED_STATUS: Final = "status=BLOCKED_CADDY_CANDIDATE_ARGUMENT_INVALID"


class CaddyCandidateError(ValueError):
    """Non-reflective validation failure for an inert review artifact."""


def _validate_private_port(value: object) -> int:
    # Require exactly five canonical ASCII decimal characters to prevent
    # configuration injection, signed/zero-prefixed variants and bool/int coercion.
    if (
        type(value) is not str
        or len(value) != 5
        or not value.isascii()
        or not value.isdecimal()
    ):
        raise CaddyCandidateError("CADDY_CANDIDATE_PORT_INVALID")
    port = int(value)
    if not (MIN_PRIVATE_PORT <= port <= MAX_PRIVATE_PORT):
        raise CaddyCandidateError("CADDY_CANDIDATE_PORT_INVALID")
    return port


def render_review_only_caddy_candidate(*, upstream_port: str) -> str:
    """Return a non-deploying Caddyfile fragment for human review only."""
    port = _validate_private_port(upstream_port)
    return (
        "# REVIEW ONLY — not a production deployment or activation receipt.\n"
        "# Operator must verify the selected localhost port, isolated production\n"
        "# application, source provenance, vhost imports, ACME/TLS and rollback.\n"
        f"{CANONICAL_HOST} {{\n"
        f"    reverse_proxy 127.0.0.1:{port}\n"
        "}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = tuple(sys.argv[1:] if argv is None else argv)
    if not args:
        print(INERT_STATUS)
        return 0
    if (
        len(args) != 4
        or args[0] != "--render-candidate"
        or args[1] != EXACT_RENDER_OPT_IN
        or args[2] != "--upstream-port"
    ):
        print(BLOCKED_STATUS)
        return 2
    try:
        candidate = render_review_only_caddy_candidate(upstream_port=args[3])
    except (CaddyCandidateError, TypeError, ValueError):
        print(BLOCKED_STATUS)
        return 2
    sys.stdout.write(candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
