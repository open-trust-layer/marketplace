"""Manual one-shot M78 local UI loopback acceptance harness.

Import, help, validation, and dry-run are network-inert. Real Python socket
selection occurs only after the exact M78 execution opt-in token is validated.
This tool is not a service, daemon, deployment entry point, or browser launcher.
"""
from __future__ import annotations

import argparse
import sys

from marketplace.reference.local_ui_loopback_v1 import (
    LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
    LocalUiLoopbackError,
    plan_local_ui_loopback_once,
    serve_local_ui_loopback_once,
)


def _real_socket_constructor():
    import socket

    return socket.socket


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Explicit one-shot loopback host for the reviewed M77 local UI adapter. "
            "Dry-run is network-inert; execution requires the exact M78 opt-in token."
        )
    )
    parser.add_argument("--port", type=int, required=True, help="IPv4 loopback port 1024..65535")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate plan only; no socket selection")
    mode.add_argument(
        "--execute-one-local-ui-loopback-session",
        metavar="TOKEN",
        help="TOKEN must equal the exact documented M78 one-shot execution opt-in",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        plan = plan_local_ui_loopback_once(args.port)
    except LocalUiLoopbackError as exc:
        print(exc.code, file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"M78_DRY_RUN_READY host={plan.host} port={plan.port} one_shot=true network_invoked=false")
        return 0

    token = args.execute_one_local_ui_loopback_session
    if type(token) is not str or token != LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN:
        print("M78_EXECUTION_OPT_IN_REQUIRED", file=sys.stderr)
        return 2
    try:
        constructor = _real_socket_constructor()
    except Exception:
        print("M78_SOCKET_SELECTION_FAILED", file=sys.stderr)
        return 1

    try:
        result = serve_local_ui_loopback_once(
            port=plan.port,
            execution_opt_in=token,
            socket_constructor=constructor,
        )
    except LocalUiLoopbackError as exc:
        print(exc.code, file=sys.stderr)
        return 1

    print(
        "M78_ONE_SHOT_LOCAL_UI_LOOPBACK_COMPLETE "
        f"status={result.status_code} bytes_received={result.bytes_received} bytes_sent={result.bytes_sent} "
        "external_authorization_established=false deployment_authorized=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
