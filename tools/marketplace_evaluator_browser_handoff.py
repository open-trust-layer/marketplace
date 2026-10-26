"""Operator-console browser public-key verification before local runtime handoff.

No secrets, keys, or provisioning bytes are transmitted to GitHub. Browser
public carriers are typed into the original Windows operator console, never
passed in argv or printed back. Does not start a server or contact PostgreSQL.
"""
from __future__ import annotations

import argparse
import getpass
import sys
import time

from tools.marketplace_browser_bundle_binding_preflight import (
    BrowserBundleBindingError,
    check_browser_bundle_binding,
)


class _RedactedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=BLOCKED code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedParser(description="Manual same-origin browser-binding handoff")
    parser.add_argument("--authentication-provisioning-directory", required=True)
    parser.add_argument("--inert", action="store_true")
    args = parser.parse_args(argv)
    if args.inert:
        print(
            "status=INERT_BROWSER_HANDOFF_READY keys_read=false "
            "postgres_invoked=false server_invoked=false"
        )
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("status=BLOCKED code=LOCAL_INTERACTIVE_CONSOLE_REQUIRED")
        return 1

    seller = buyer = None
    try:
        seller = getpass.getpass("Paste SELLER browser mkpk1_ public carrier (hidden input): ")
        buyer = getpass.getpass("Paste BUYER browser mkpk1_ public carrier (hidden input): ")
        remaining = check_browser_bundle_binding(
            directory=args.authentication_provisioning_directory,
            seller_browser_public_key=seller,
            buyer_browser_public_key=buyer,
            at_time=int(time.time()),
            minimum_remaining_seconds=1800,
        )
    except BrowserBundleBindingError as exc:
        # The verifier exposes fixed safe categories, never the input values.
        print("status=BLOCKED code=" + exc.code)
        return 1
    except Exception:
        print("status=BLOCKED code=BROWSER_HANDOFF_FAILED")
        return 1
    finally:
        # Python immutable string erasure cannot be guaranteed.
        del seller, buyer

    print(
        "status=BROWSER_BINDING_VERIFIED "
        f"lease_remaining_seconds={remaining} identities=2 "
        "signature_verified=true public_keys_bound=true "
        "private_keys_opened=false postgres_invoked=false server_invoked=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
