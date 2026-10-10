"""Read-only, non-secret validity check for local Marketplace auth provisioning.

The existing bounded canonical loader and Ed25519 verifier remain authoritative.
No key generation, database access, server execution or network activity.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
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
    materialize_marketplace_authentication_verification_method_snapshot,
)

MAX_MINIMUM_REMAINING_SECONDS = 86_400


class ProvisioningLeasePreflightError(RuntimeError):
    """Stable diagnostic that never incorporates private input or exception text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def check_provisioning_lease(
    directory: str,
    *,
    at_time: int,
    minimum_remaining_seconds: int = 1_800,
) -> tuple[int, int]:
    """Return (shortest usable identity lease, identity count) after verification.

    Expiry categories are emitted *only* after canonical parsing and signature
    verification. A cryptographically invalid bundle must not be described as
    merely expired, even if its untrusted claims contain an expired timestamp.
    """
    if (
        type(directory) is not str
        or not directory
        or len(directory) > 4_096
        or not Path(directory).is_absolute()
    ):
        raise ProvisioningLeasePreflightError("PROVISIONING_DIRECTORY_INVALID")
    if type(at_time) is not int or at_time < 0:
        raise ProvisioningLeasePreflightError("TIME_INVALID")
    if (
        type(minimum_remaining_seconds) is not int
        or not 0 <= minimum_remaining_seconds <= MAX_MINIMUM_REMAINING_SECONDS
    ):
        raise ProvisioningLeasePreflightError("MINIMUM_REMAINING_INVALID")

    try:
        provisioning = load_marketplace_authentication_startup_provisioning(
            directory=directory,
        )
        envelope = provisioning.verification_method_evidence
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            envelope.claims_json,
        )
        anchor_snapshot = materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
            provisioning.trust_anchor_manifest,
        )
        verifier = MarketplaceEd25519AuthenticationEvidenceTrustVerifier(
            trust_anchors=anchor_snapshot,
        )
        verified = verifier.verify_authentication_verification_method_evidence(
            envelope,
        )
        if (
            type(verified) is not VerifiedAuthenticationVerificationMethodEvidence
            or verified.accepted is not True
            or verified.authority != claims.authority
            or verified.claims_sha256 != hashlib.sha256(envelope.claims_json).digest()
        ):
            raise ProvisioningLeasePreflightError("PROVISIONING_INVALID")
    except ProvisioningLeasePreflightError:
        raise
    except Exception:
        raise ProvisioningLeasePreflightError("PROVISIONING_INVALID") from None

    if at_time < claims.issued_at:
        raise ProvisioningLeasePreflightError("LEASE_NOT_YET_VALID")
    if at_time >= claims.expires_at:
        raise ProvisioningLeasePreflightError("LEASE_EXPIRED")
    remaining = claims.expires_at - at_time
    if remaining < minimum_remaining_seconds:
        raise ProvisioningLeasePreflightError("LEASE_TOO_SHORT")

    # Exercise the reviewed projection first. Its entries can have shorter
    # signed validity windows than the global evidence lease, so a bundle-level
    # PASS alone cannot prove that both seller and buyer can authenticate.
    try:
        snapshot = materialize_marketplace_authentication_verification_method_snapshot(
            envelope=envelope,
            trust_verifier=verifier,
            at_time=at_time,
        )
    except Exception:
        raise ProvisioningLeasePreflightError("PROVISIONING_INVALID") from None

    effective_remaining = remaining
    for entry in claims.entries:
        start = max(
            claims.issued_at,
            entry.valid_from if entry.valid_from is not None else claims.issued_at,
        )
        end = min(
            claims.expires_at,
            entry.valid_until if entry.valid_until is not None else claims.expires_at,
        )
        if at_time < start:
            raise ProvisioningLeasePreflightError("IDENTITY_NOT_YET_VALID")
        if at_time >= end:
            raise ProvisioningLeasePreflightError("IDENTITY_EXPIRED")
        # The exact reviewed principal-binding verifier must agree at this
        # sampled time. Never print the principal or method on failure.
        try:
            bound = snapshot.verify(
                principal=entry.controller_principal,
                verification_method=entry.verification_method,
                at_time=at_time,
            )
        except Exception:
            raise ProvisioningLeasePreflightError("PROVISIONING_INVALID") from None
        if bound is not True:
            raise ProvisioningLeasePreflightError("PROVISIONING_INVALID")
        if end - at_time < minimum_remaining_seconds:
            raise ProvisioningLeasePreflightError("IDENTITY_LEASE_TOO_SHORT")
        effective_remaining = min(effective_remaining, end - at_time)
    return effective_remaining, len(claims.entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check canonical signed local Marketplace authentication lease without executing the runtime.",
    )
    parser.add_argument("--authentication-provisioning-directory", required=True)
    parser.add_argument("--minimum-remaining-seconds", type=int, default=1_800)
    args = parser.parse_args(argv)
    try:
        remaining, identities = check_provisioning_lease(
            args.authentication_provisioning_directory,
            at_time=int(time.time()),
            minimum_remaining_seconds=args.minimum_remaining_seconds,
        )
    except ProvisioningLeasePreflightError as exc:
        print(f"status=FAIL code={exc.code}", file=sys.stderr)
        return 1
    print(
        f"status=PASS lease_remaining_seconds={remaining} identities={identities} "
        "signature_verified=true server_invoked=false postgres_invoked=false",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
