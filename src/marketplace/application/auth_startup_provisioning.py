"""M17.5S bounded local authentication startup provisioning intake."""
from __future__ import annotations

from dataclasses import dataclass
import os
import stat
from typing import Final

from .auth_trust_anchor_manifest import (
    AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES,
    decode_marketplace_authentication_trust_anchor_manifest,
)
from .auth_verification_method_evidence import (
    AUTH_EVIDENCE_ATTESTATION_MAX_BYTES,
    AUTH_EVIDENCE_CLAIMS_MAX_BYTES,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    decode_marketplace_authentication_verification_method_evidence_claims,
)

PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_STARTUP_PROVISIONING_V1"
TRUST_ANCHOR_MANIFEST_FILENAME: Final = "trust-anchor-manifest.json"
VERIFICATION_METHOD_CLAIMS_FILENAME: Final = "verification-method-claims.json"
VERIFICATION_METHOD_ATTESTATION_FILENAME: Final = "verification-method-attestation.bin"
_ERROR_MESSAGE: Final = "authentication startup provisioning is invalid or unavailable"
_REPARSE_POINT: Final = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class MarketplaceAuthenticationStartupProvisioningError(ValueError):
    """Stable fail-closed local provisioning error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticationStartupProvisioningError() from None


def _is_reparse(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & _REPARSE_POINT)


def _identity(info: os.stat_result) -> tuple[int, ...]:
    # Windows path and handle stat APIs can disagree on ctime for one file.
    ctime_ns = 0 if os.name == "nt" else info.st_ctime_ns
    return (
        info.st_dev,
        info.st_ino,
        stat.S_IFMT(info.st_mode),
        info.st_size,
        info.st_mtime_ns,
        ctime_ns,
        getattr(info, "st_nlink", 0),
        getattr(info, "st_file_attributes", 0),
    )


def _canonical_directory(directory: object) -> tuple[str, tuple[int, ...]]:
    if type(directory) is not str or not directory or "\x00" in directory:
        _fail()
    if not os.path.isabs(directory) or os.path.normpath(directory) != directory:
        _fail()
    if os.name == "nt" and directory.startswith(("\\\\", "//")):
        _fail()
    try:
        real = os.path.realpath(directory, strict=True)
        info = os.lstat(directory)
    except (OSError, ValueError, TypeError):
        _fail()
    if os.path.normcase(real) != os.path.normcase(directory):
        _fail()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        _fail()
    if _is_reparse(info):
        _fail()
    return directory, _identity(info)


def _safe_child(directory: str, filename: str) -> tuple[str, tuple[int, ...]]:
    path = os.path.join(directory, filename)
    if os.path.dirname(path) != directory:
        _fail()
    try:
        real = os.path.realpath(path, strict=True)
        if os.path.commonpath((directory, real)) != directory:
            _fail()
        info = os.lstat(path)
    except (OSError, ValueError, TypeError):
        _fail()
    if os.path.normcase(real) != os.path.normcase(path):
        _fail()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        _fail()
    if _is_reparse(info):
        _fail()
    return path, _identity(info)


def _read_bounded(path: str, expected: tuple[int, ...], maximum: int) -> bytes:
    try:
        with open(path, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if _identity(opened) != expected:
                _fail()
            raw = handle.read(maximum + 1)
            after_read = os.fstat(handle.fileno())
        after_path = os.lstat(path)
        real_after = os.path.realpath(path, strict=True)
    except MarketplaceAuthenticationStartupProvisioningError:
        raise
    except Exception:
        _fail()
    if _identity(after_read) != expected or _identity(after_path) != expected:
        _fail()
    if os.path.normcase(real_after) != os.path.normcase(path):
        _fail()
    if not raw or len(raw) > maximum:
        _fail()
    return raw


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationStartupProvisioning:
    """Immutable exact public authentication provisioning bytes."""

    trust_anchor_manifest: bytes
    verification_method_evidence: (
        MarketplaceAuthenticationVerificationMethodEvidenceEnvelope
    )

    def __post_init__(self) -> None:
        if type(self.trust_anchor_manifest) is not bytes:
            _fail()
        if (
            type(self.verification_method_evidence)
            is not MarketplaceAuthenticationVerificationMethodEvidenceEnvelope
        ):
            _fail()
        try:
            decode_marketplace_authentication_trust_anchor_manifest(
                self.trust_anchor_manifest
            )
            decode_marketplace_authentication_verification_method_evidence_claims(
                self.verification_method_evidence.claims_json
            )
        except Exception:
            _fail()


def load_marketplace_authentication_startup_provisioning(
    *, directory: str
) -> MarketplaceAuthenticationStartupProvisioning:
    """Load exactly three bounded canonical local authentication inputs once."""

    directory, directory_identity = _canonical_directory(directory)
    try:
        manifest_path, manifest_identity = _safe_child(
            directory, TRUST_ANCHOR_MANIFEST_FILENAME
        )
        claims_path, claims_identity = _safe_child(
            directory, VERIFICATION_METHOD_CLAIMS_FILENAME
        )
        attestation_path, attestation_identity = _safe_child(
            directory, VERIFICATION_METHOD_ATTESTATION_FILENAME
        )
        manifest = _read_bounded(
            manifest_path,
            manifest_identity,
            AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES,
        )
        claims = _read_bounded(
            claims_path,
            claims_identity,
            AUTH_EVIDENCE_CLAIMS_MAX_BYTES,
        )
        attestation = _read_bounded(
            attestation_path,
            attestation_identity,
            AUTH_EVIDENCE_ATTESTATION_MAX_BYTES,
        )
        directory_after = os.lstat(directory)
        if _identity(directory_after) != directory_identity:
            _fail()
        real_directory = os.path.realpath(directory, strict=True)
        if os.path.normcase(real_directory) != os.path.normcase(directory):
            _fail()
        decode_marketplace_authentication_trust_anchor_manifest(manifest)
        decode_marketplace_authentication_verification_method_evidence_claims(claims)
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=claims,
            attestation=attestation,
        )
        return MarketplaceAuthenticationStartupProvisioning(
            trust_anchor_manifest=manifest,
            verification_method_evidence=envelope,
        )
    except MarketplaceAuthenticationStartupProvisioningError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticationStartupProvisioning",
    "MarketplaceAuthenticationStartupProvisioningError",
    "PROFILE_NAME",
    "TRUST_ANCHOR_MANIFEST_FILENAME",
    "VERIFICATION_METHOD_ATTESTATION_FILENAME",
    "VERIFICATION_METHOD_CLAIMS_FILENAME",
    "load_marketplace_authentication_startup_provisioning",
]
