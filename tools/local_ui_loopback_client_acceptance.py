"""Manual one-shot M79 local UI loopback client acceptance harness.

Import, help, validation, and dry-run are network-inert. Real Python socket
selection occurs only after the exact M79 client execution opt-in is validated.
The tool sends one deterministic benign GET or POST to an already-running M78
one-shot host; it does not launch or orchestrate the server or a browser.
"""
from __future__ import annotations

import argparse
import sys
from urllib.parse import urlencode

from marketplace.reference.local_ui_http_v1 import LocalUiHttpRequest
from marketplace.reference.local_ui_loopback_client_v1 import (
    LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
    LocalUiLoopbackClientError,
    plan_local_ui_loopback_client_once,
    run_local_ui_loopback_client_once,
)


_POST_FIELDS = {
    "seller_principal": "did:example:m79-seller",
    "subject_uri": "urn:example:product:m79-bicycle",
    "title": "M79 acceptance bicycle",
    "description": "Deterministic local acceptance fixture.",
    "consideration": "125.00",
    "currency_code": "EUR",
    "quantity": "1",
    "unit_uri": "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/unit/item",
    "latitude": "52.520000",
    "longitude": "13.405000",
    "buyer_principal": "did:example:m79-buyer",
    "buyer_action_uri": "https://example.test/actions/buy",
}


def _real_socket_constructor():
    import socket

    return socket.socket


def _request(profile: str) -> LocalUiHttpRequest:
    if profile == "get":
        return LocalUiHttpRequest("GET", "/", None, b"")
    body = urlencode(_POST_FIELDS).encode("ascii")
    return LocalUiHttpRequest(
        "POST",
        "/local-buy-sell",
        "application/x-www-form-urlencoded",
        body,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-shot loopback client for an already-running reviewed M78 local UI host. "
            "Dry-run is network-inert; execution requires the exact M79 client opt-in token."
        )
    )
    parser.add_argument("--port", type=int, required=True, help="IPv4 loopback port 1024..65535")
    parser.add_argument("--request", choices=("get", "post"), required=True, help="deterministic request profile")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate plan only; no socket selection")
    mode.add_argument(
        "--execute-one-local-ui-loopback-client",
        metavar="TOKEN",
        help="TOKEN must equal the exact documented M79 one-shot client execution opt-in",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    request = _request(args.request)
    try:
        plan = plan_local_ui_loopback_client_once(args.port, request)
    except LocalUiLoopbackClientError as exc:
        print(exc.code, file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            "M79_DRY_RUN_READY "
            f"host={plan.host} port={plan.port} method={plan.request_method} target={plan.request_target} "
            "one_shot=true network_invoked=false"
        )
        return 0

    token = args.execute_one_local_ui_loopback_client
    if type(token) is not str or token != LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN:
        print("M79_CLIENT_EXECUTION_OPT_IN_REQUIRED", file=sys.stderr)
        return 2
    try:
        constructor = _real_socket_constructor()
    except Exception:
        print("M79_SOCKET_SELECTION_FAILED", file=sys.stderr)
        return 1

    try:
        result = run_local_ui_loopback_client_once(
            port=plan.port,
            request=request,
            execution_opt_in=token,
            socket_constructor=constructor,
        )
    except LocalUiLoopbackClientError as exc:
        print(exc.code, file=sys.stderr)
        return 1

    print(
        "M79_ONE_SHOT_LOCAL_UI_LOOPBACK_CLIENT_COMPLETE "
        f"status={result.status_code} bytes_sent={result.bytes_sent} bytes_received={result.bytes_received} "
        "external_authorization_established=false deployment_authorized=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
