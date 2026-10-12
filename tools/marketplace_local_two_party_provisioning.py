"""Explicit local-only, short-lived, two-party Marketplace signed test provisioning.

Consumes two *public* Ed25519 browser key carriers; never obtains or writes
browser private keys. Generates a one-use in-memory test trust signer and
writes only its public manifest, canonical claims, and attestation. No
database, server, browser, network or production provisioning is invoked.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time

from marketplace.application.auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
    build_marketplace_authentication_evidence_trust_transcript,
)
from marketplace.application.auth_startup_provisioning import (
    TRUST_ANCHOR_MANIFEST_FILENAME,
    VERIFICATION_METHOD_CLAIMS_FILENAME,
    VERIFICATION_METHOD_ATTESTATION_FILENAME,
)
from marketplace.application.auth_trust_anchor_manifest import (
    MarketplaceAuthenticationEvidenceTrustAnchorManifest,
    encode_marketplace_authentication_trust_anchor_manifest,
)
from marketplace.application.auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceClaim,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    parse_marketplace_auth_verification_public_key,
    encode_marketplace_authentication_verification_method_evidence_claims,
)
from tools.marketplace_authentication_lease_preflight import check_provisioning_lease

EXECUTION_OPT_IN = "EXECUTE_MARKETPLACE_LOCAL_TWO_PARTY_TEST_PROVISIONING_V1"
SELLER_PRINCIPAL = "did:example:marketplace-local-evaluator-seller"
BUYER_PRINCIPAL = "did:example:marketplace-local-evaluator-buyer"
SELLER_METHOD = SELLER_PRINCIPAL + "#key-1"
BUYER_METHOD = BUYER_PRINCIPAL + "#key-1"
AUTHORITY = "https://authority.example/marketplace-local-evaluator"
MIN_LEASE_SECONDS = 1800
MAX_LEASE_SECONDS = 86400
BROWSER_PREFIX = "mkpk1_"
EVIDENCE_PREFIX = "mkp1_"


class LocalProvisioningError(RuntimeError):
    """Stable, non-reflective operator diagnostic."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _browser_public_key(value: str) -> bytes:
    if type(value) is not str or not value.startswith(BROWSER_PREFIX):
        raise LocalProvisioningError("PUBLIC_KEY_INVALID")
    try:
        return parse_marketplace_auth_verification_public_key(
            EVIDENCE_PREFIX + value[len(BROWSER_PREFIX):]
        )
    except Exception:
        raise LocalProvisioningError("PUBLIC_KEY_INVALID") from None


def _fresh_destination(value: str) -> Path:
    if type(value) is not str or not value or "\x00" in value or len(value) > 4096:
        raise LocalProvisioningError("DESTINATION_INVALID")
    path = Path(value)
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise LocalProvisioningError("DESTINATION_INVALID")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise LocalProvisioningError("DESTINATION_INVALID")
    # Never create runtime trust material inside a Git worktree.
    if any((ancestor / ".git").exists() for ancestor in path.parents):
        raise LocalProvisioningError("DESTINATION_INVALID")
    return path


def _write_exclusive(directory: Path, name: str, content: bytes) -> None:
    fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        raise LocalProvisioningError("OUTPUT_UNAVAILABLE") from None


def create_local_two_party_provisioning(
    *,
    directory: str,
    seller_public_key: str,
    buyer_public_key: str,
    lease_seconds: int = 7200,
    now: int | None = None,
) -> None:
    """Create an isolated, signed test bundle; never persist a private key."""
    if type(lease_seconds) is not int or not MIN_LEASE_SECONDS <= lease_seconds <= MAX_LEASE_SECONDS:
        raise LocalProvisioningError("LEASE_INVALID")
    if now is None:
        now = int(time.time())
    if type(now) is not int or now < 0:
        raise LocalProvisioningError("TIME_INVALID")
    destination = _fresh_destination(directory)
    seller_key = _browser_public_key(seller_public_key)
    buyer_key = _browser_public_key(buyer_public_key)
    if seller_key == buyer_key:
        raise LocalProvisioningError("PARTY_KEYS_NOT_DISTINCT")

    # Import optional cryptographic provider only inside the explicit execution.
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        signer = Ed25519PrivateKey.generate()
        signing_public = signer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        manifest = encode_marketplace_authentication_trust_anchor_manifest(
            MarketplaceAuthenticationEvidenceTrustAnchorManifest(anchors=(
                AuthenticationEvidenceTrustAnchor(AUTHORITY, signing_public),
            ))
        )
        claims = encode_marketplace_authentication_verification_method_evidence_claims(
            MarketplaceAuthenticationVerificationMethodEvidenceClaims(
                authority=AUTHORITY,
                issued_at=now,
                expires_at=now + lease_seconds,
                entries=(
                    AuthenticationVerificationMethodEvidenceClaim(
                        verification_method=SELLER_METHOD,
                        controller_principal=SELLER_PRINCIPAL,
                        public_key=seller_key,
                        valid_from=now,
                        valid_until=now + lease_seconds,
                    ),
                    AuthenticationVerificationMethodEvidenceClaim(
                        verification_method=BUYER_METHOD,
                        controller_principal=BUYER_PRINCIPAL,
                        public_key=buyer_key,
                        valid_from=now,
                        valid_until=now + lease_seconds,
                    ),
                ),
            )
        )
        import hashlib
        attestation = signer.sign(build_marketplace_authentication_evidence_trust_transcript(
            authority=AUTHORITY, claims_sha256=hashlib.sha256(claims).digest()
        ))
        # The trust signer's private key is not serialized, returned or saved.
        del signer
    except Exception:
        raise LocalProvisioningError("SIGNING_UNAVAILABLE") from None

    try:
        destination.mkdir(mode=0o700)
        _write_exclusive(destination, TRUST_ANCHOR_MANIFEST_FILENAME, manifest)
        _write_exclusive(destination, VERIFICATION_METHOD_CLAIMS_FILENAME, claims)
        _write_exclusive(destination, VERIFICATION_METHOD_ATTESTATION_FILENAME, attestation)
        remaining, identities = check_provisioning_lease(
            str(destination), at_time=now,
            minimum_remaining_seconds=MIN_LEASE_SECONDS,
            minimum_distinct_principals=2,
        )
        if identities != 2 or remaining != lease_seconds:
            raise LocalProvisioningError("POSTWRITE_VERIFICATION_FAILED")
    except LocalProvisioningError:
        raise
    except FileExistsError:
        raise LocalProvisioningError("DESTINATION_INVALID") from None
    except Exception:
        raise LocalProvisioningError("OUTPUT_UNAVAILABLE") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicitly create ephemeral signed *local test* trust evidence from two browser public keys."
    )
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--seller-browser-public-key", required=True)
    parser.add_argument("--buyer-browser-public-key", required=True)
    parser.add_argument("--lease-seconds", type=int, default=7200)
    parser.add_argument("--execute-local-test-provisioning", required=True)
    args = parser.parse_args(argv)
    if args.execute_local_test_provisioning != EXECUTION_OPT_IN:
        print("status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED", file=sys.stderr)
        return 1
    try:
        create_local_two_party_provisioning(
            directory=args.output_directory,
            seller_public_key=args.seller_browser_public_key,
            buyer_public_key=args.buyer_browser_public_key,
            lease_seconds=args.lease_seconds,
        )
    except LocalProvisioningError as exc:
        print("status=BLOCKED code=" + exc.code, file=sys.stderr)
        return 1
    print(
        "status=LOCAL_TWO_PARTY_TEST_PROVISIONING_CREATED "
        "identities=2 signature_verified=true private_keys_written=false "
        "database_invoked=false server_invoked=false browser_invoked=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
