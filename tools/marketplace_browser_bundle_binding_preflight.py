"""Verify live browser *public* keys match the signed local test identities.

Offline only: no browser/CDP access, private keys, DSN, database, network or server.
Callers obtain public carriers from two preserved, same-origin browser contexts.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import sys
import time

from marketplace.application.auth_evidence_trust_ed25519 import (
    MarketplaceEd25519AuthenticationEvidenceTrustVerifier,
)
from marketplace.application.auth_startup_provisioning import (
    load_marketplace_authentication_startup_provisioning,
)
from marketplace.application.auth_trust_anchor_manifest import (
    materialize_marketplace_authentication_evidence_trust_anchor_snapshot,
)
from marketplace.application.auth_verification_method_evidence import (
    VerifiedAuthenticationVerificationMethodEvidence,
    decode_marketplace_authentication_verification_method_evidence_claims,
    parse_marketplace_auth_verification_public_key,
)
from tools.marketplace_authentication_lease_preflight import (
    ProvisioningLeasePreflightError,
    check_provisioning_lease,
)
from tools.marketplace_local_two_party_provisioning import (
    AUTHORITY,
    BUYER_METHOD,
    BUYER_PRINCIPAL,
    SELLER_METHOD,
    SELLER_PRINCIPAL,
)

_PUBLIC_PREFIX = "mkpk1_"
_EVIDENCE_PREFIX = "mkp1_"


class BrowserBundleBindingError(RuntimeError):
    """Stable diagnostic; never reflect key values or local file contents."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _parse_browser_public_carrier(value: object) -> bytes:
    if type(value) is not str or not value.startswith(_PUBLIC_PREFIX):
        raise BrowserBundleBindingError("BROWSER_PUBLIC_KEY_INVALID")
    try:
        return parse_marketplace_auth_verification_public_key(
            _EVIDENCE_PREFIX + value[len(_PUBLIC_PREFIX):]
        )
    except Exception:
        raise BrowserBundleBindingError("BROWSER_PUBLIC_KEY_INVALID") from None


def check_browser_bundle_binding(
    *,
    directory: str,
    seller_browser_public_key: str,
    buyer_browser_public_key: str,
    at_time: int,
    minimum_remaining_seconds: int = 1800,
) -> int:
    """Return effective lease after verifying *both exact signed key bindings*.

    A signature-valid bundle with stale/swapped browser keys MUST fail. This is
    not evidence that a browser possesses a private key or has logged in.
    """
    # M17.7P acceptance requires at least 30 minutes remaining. This
    # specific handoff check must not allow a zero-second override.
    if type(minimum_remaining_seconds) is not int or not 1800 <= minimum_remaining_seconds <= 86400:
        raise BrowserBundleBindingError("MINIMUM_REMAINING_INVALID")
    seller_key = _parse_browser_public_carrier(seller_browser_public_key)
    buyer_key = _parse_browser_public_carrier(buyer_browser_public_key)
    if hmac.compare_digest(seller_key, buyer_key):
        raise BrowserBundleBindingError("BROWSER_KEYS_NOT_DISTINCT")
    try:
        remaining, count = check_provisioning_lease(
            directory,
            at_time=at_time,
            minimum_remaining_seconds=minimum_remaining_seconds,
            minimum_distinct_principals=2,
        )
    except ProvisioningLeasePreflightError as exc:
        raise BrowserBundleBindingError(exc.code) from None
    if count != 2:
        raise BrowserBundleBindingError("TEST_BUNDLE_PROFILE_INVALID")

    # The bundle is loaded again as a canonical bounded snapshot, so the
    # exact claims being compared must independently verify cryptographically.
    # Never infer trust from an earlier, separately read path.
    try:
        material = load_marketplace_authentication_startup_provisioning(
            directory=directory
        )
        envelope = material.verification_method_evidence
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            envelope.claims_json
        )
        anchors = materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
            material.trust_anchor_manifest
        )
        verifier = MarketplaceEd25519AuthenticationEvidenceTrustVerifier(
            trust_anchors=anchors
        )
        verified = verifier.verify_authentication_verification_method_evidence(
            envelope
        )
        if (
            type(verified) is not VerifiedAuthenticationVerificationMethodEvidence
            or verified.accepted is not True
            or verified.authority != claims.authority
            or verified.claims_sha256 != hashlib.sha256(envelope.claims_json).digest()
        ):
            raise BrowserBundleBindingError("PROVISIONING_INVALID")
    except BrowserBundleBindingError:
        raise
    except Exception:
        raise BrowserBundleBindingError("PROVISIONING_INVALID") from None

    if (
        claims.authority != AUTHORITY
        or len(claims.entries) != 2
        or type(at_time) is not int
        or type(minimum_remaining_seconds) is not int
        or at_time < claims.issued_at
        or claims.expires_at - at_time < minimum_remaining_seconds
    ):
        raise BrowserBundleBindingError("TEST_BUNDLE_PROFILE_INVALID")

    expected = {
        (SELLER_PRINCIPAL, SELLER_METHOD): seller_key,
        (BUYER_PRINCIPAL, BUYER_METHOD): buyer_key,
    }
    actual = {
        (entry.controller_principal, entry.verification_method): entry
        for entry in claims.entries
    }
    if set(actual) != set(expected):
        raise BrowserBundleBindingError("TEST_BUNDLE_PROFILE_INVALID")
    for identity, expected_key in expected.items():
        entry = actual[identity]
        start = max(
            claims.issued_at,
            entry.valid_from if entry.valid_from is not None else claims.issued_at,
        )
        end = min(
            claims.expires_at,
            entry.valid_until if entry.valid_until is not None else claims.expires_at,
        )
        if not start <= at_time or end - at_time < minimum_remaining_seconds:
            raise BrowserBundleBindingError("IDENTITY_LEASE_TOO_SHORT")
        if not hmac.compare_digest(entry.public_key, expected_key):
            raise BrowserBundleBindingError("BROWSER_KEY_BINDING_MISMATCH")
        remaining = min(remaining, end - at_time)
    return remaining


class _RedactedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=BLOCKED code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedParser(
        description="Check signed local test identities against two live browser public carriers."
    )
    parser.add_argument("--authentication-provisioning-directory", required=True)
    parser.add_argument("--seller-browser-public-key", required=True)
    parser.add_argument("--buyer-browser-public-key", required=True)
    parser.add_argument("--minimum-remaining-seconds", type=int, default=1800)
    args = parser.parse_args(argv)
    try:
        remaining = check_browser_bundle_binding(
            directory=args.authentication_provisioning_directory,
            seller_browser_public_key=args.seller_browser_public_key,
            buyer_browser_public_key=args.buyer_browser_public_key,
            at_time=int(time.time()),
            minimum_remaining_seconds=args.minimum_remaining_seconds,
        )
    except BrowserBundleBindingError as exc:
        print("status=BLOCKED code=" + exc.code, file=sys.stderr)
        return 1
    print(
        "status=BROWSER_BINDING_VERIFIED "
        f"lease_remaining_seconds={remaining} identities=2 "
        "signature_verified=true public_keys_bound=true "
        "private_keys_opened=false browser_invoked=false "
        "postgres_invoked=false server_invoked=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
