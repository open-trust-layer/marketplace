"""Inert fixed-host Caddy Unix-upstream review snippet, never deployed.

Prints no configuration unless an exact review-only token is supplied.
No Caddy, filesystem, DNS, subprocess, network, TLS or service actions.
"""
from __future__ import annotations

import sys
from typing import Final, Sequence


CANONICAL_HOST: Final = "marketplace.open-trust-layer.org"
REVIEW_UNIX_SOCKET_PATH: Final = "/run/moon-marketplace/marketplace-edge.sock"
REVIEW_UNIX_UPSTREAM: Final = "unix//run/moon-marketplace/marketplace-edge.sock"
EXACT_RENDER_TOKEN: Final = "RENDER_ONLY_MARKETPLACE_CADDY_UNIX_REVIEW_V1"
INERT_STATUS: Final = "status=INERT_CADDY_UNIX_REVIEW_NOT_RENDERED"
INVALID_STATUS: Final = "status=BLOCKED_CADDY_UNIX_REVIEW_ARGUMENT_INVALID"


def render_caddy_unix_review_candidate() -> str:
    """Render exactly one deterministic, illustrative, NOT deployable Caddyfile block."""
    return (
        "# REVIEW ONLY: do not deploy, import, reload, or activate from this output.\n"
        "# Illustrative socket path is NOT a provisioned or reserved live path.\n"
        "# Verify Caddy identity, Unix permissions, actual HTTP framing, HTTPS/SNI,\n"
        "# existing vhosts, full authenticated ASGI app, DB, backups and rollback.\n"
        f"{CANONICAL_HOST} {{\n"
        f"    reverse_proxy {REVIEW_UNIX_UPSTREAM} {{\n"
        "        header_up -Forwarded\n"
        "        header_up -X-Real-IP\n"
        "        header_up -X-Original-*\n"
        "        header_up -X-Rewrite-URL\n"
        "        header_up -X-Scheme\n"
        "        header_up -X-Forwarded-Port\n"
        "        header_up -X-Forwarded-Prefix\n"
        "        header_up -X-Forwarded-Scheme\n"
        "        header_up -X-Forwarded-Server\n"
        "        transport http {\n"
        "            versions 1.1\n"
        "            keepalive off\n"
        "            dial_timeout 2s\n"
        "            response_header_timeout 6s\n"
        "            compression off\n"
        "        }\n"
        "    }\n"
        "}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = tuple(sys.argv[1:] if argv is None else argv)
    if not args:
        print(INERT_STATUS)
        return 0
    if args != ("--render-candidate", EXACT_RENDER_TOKEN):
        print(INVALID_STATUS)
        return 2
    sys.stdout.write(render_caddy_unix_review_candidate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
