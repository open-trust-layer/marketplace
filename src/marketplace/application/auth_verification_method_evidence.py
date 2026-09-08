"""M17.5L canonical authentication verification-method evidence intake.

This module validates caller-supplied canonical claims and projects only
trust-verifier-accepted public evidence into the immutable M17.5K snapshot.
It performs no acquisition, resolution, persistence, signing, or runtime selection.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Final, Protocol

from .auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    AuthenticationVerificationMethodSnapshotError,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_EVIDENCE_BUNDLE_V1"
AUTH_EVIDENCE_BUNDLE_TYPE: Final = "MarketplaceAuthenticationVerificationMethodEvidenceBundle"
AUTH_EVIDENCE_BUNDLE_VERSION: Final = 1
AUTH_EVIDENCE_CLAIMS_MAX_BYTES: Final = 512 * 1024
AUTH_EVIDENCE_ATTESTATION_MAX_BYTES: Final = 16 * 1024
AUTH_EVIDENCE_MAX_ENTRIES: Final = 256
AUTH_EVIDENCE_MAX_LEASE_SECONDS: Final = 24 * 60 * 60
AUTH_EVIDENCE_URI_MAX_BYTES: Final = 2048
AUTH_EVIDENCE_PUBLIC_KEY_BYTES: Final = 32
AUTH_EVIDENCE_PUBLIC_KEY_PREFIX: Final = "mkp1_"
AUTH_EVIDENCE_PUBLIC_KEY_PAYLOAD_CHARS: Final = 43
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\\s]+$")
_BASE64URL = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
_TOP_LEVEL_KEYS = frozenset({"authority", "entries", "expiresAt", "issuedAt", "type", "version"})
_ENTRY_KEYS = frozenset({"controllerPrincipal", "publicKey", "validFrom", "validUntil", "verificationMethod"})


class AuthenticationVerificationMethodEvidenceError(ValueError):
    """Stable fail-closed evidence-intake error without input reflection."""

    def __init__(self) -> None:
        super().__init__("authentication verification-method evidence is invalid or unavailable")


def _fail() -> None:
    raise AuthenticationVerificationMethodEvidenceError() from None


def _absolute_uri(value: object) -> str:
    if type(value) is not str or not value:
        _fail()
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        _fail()
    if len(encoded) > AUTH_EVIDENCE_URI_MAX_BYTES or _URI_RE.fullmatch(value) is None:
        _fail()
    return value


def _time(value: object) -> int:
    if type(value) is not int or value < 0:
        _fail()
    return value


def _optional_time(value: object) -> int | None:
    if value is None:
        return None
    return _time(value)


def encode_marketplace_auth_verification_public_key(public_key: object) -> str:
    if type(public_key) is not bytes or len(public_key) != AUTH_EVIDENCE_PUBLIC_KEY_BYTES:
        _fail()
    payload = base64.urlsafe_b64encode(public_key).rstrip(b"=").decode("ascii")
    if len(payload) != AUTH_EVIDENCE_PUBLIC_KEY_PAYLOAD_CHARS:
        _fail()
    return AUTH_EVIDENCE_PUBLIC_KEY_PREFIX + payload


def parse_marketplace_auth_verification_public_key(value: object) -> bytes:
    if type(value) is not str or not value.startswith(AUTH_EVIDENCE_PUBLIC_KEY_PREFIX):
        _fail()
    payload = value[len(AUTH_EVIDENCE_PUBLIC_KEY_PREFIX):]
    if len(payload) != AUTH_EVIDENCE_PUBLIC_KEY_PAYLOAD_CHARS or any(c not in _BASE64URL for c in payload):
        _fail()
    try:
        raw = base64.b64decode(payload.encode("ascii") + b"=", altchars=b"-_", validate=True)
    except (UnicodeEncodeError, ValueError, TypeError):
        _fail()
    if len(raw) != AUTH_EVIDENCE_PUBLIC_KEY_BYTES:
        _fail()
    if encode_marketplace_auth_verification_public_key(raw) != value:
        _fail()
    return raw


@dataclass(frozen=True, slots=True)
class AuthenticationVerificationMethodEvidenceClaim:
    verification_method: str
    controller_principal: str
    public_key: bytes
    valid_from: int | None = None
    valid_until: int | None = None

    def __post_init__(self) -> None:
        _absolute_uri(self.verification_method)
        _absolute_uri(self.controller_principal)
        if type(self.public_key) is not bytes or len(self.public_key) != AUTH_EVIDENCE_PUBLIC_KEY_BYTES:
            _fail()
        start = _optional_time(self.valid_from)
        end = _optional_time(self.valid_until)
        if start is not None and end is not None and start >= end:
            _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationVerificationMethodEvidenceClaims:
    authority: str
    issued_at: int
    expires_at: int
    entries: tuple[AuthenticationVerificationMethodEvidenceClaim, ...]

    def __post_init__(self) -> None:
        _absolute_uri(self.authority)
        issued = _time(self.issued_at)
        expires = _time(self.expires_at)
        if issued >= expires or expires - issued > AUTH_EVIDENCE_MAX_LEASE_SECONDS:
            _fail()
        if type(self.entries) is not tuple or not (1 <= len(self.entries) <= AUTH_EVIDENCE_MAX_ENTRIES):
            _fail()
        seen: set[str] = set()
        for entry in self.entries:
            if type(entry) is not AuthenticationVerificationMethodEvidenceClaim:
                _fail()
            if entry.verification_method in seen:
                _fail()
            seen.add(entry.verification_method)


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
    claims_json: bytes
    attestation: bytes

    def __post_init__(self) -> None:
        if type(self.claims_json) is not bytes or not self.claims_json:
            _fail()
        if len(self.claims_json) > AUTH_EVIDENCE_CLAIMS_MAX_BYTES:
            _fail()
        if type(self.attestation) is not bytes or not self.attestation:
            _fail()
        if len(self.attestation) > AUTH_EVIDENCE_ATTESTATION_MAX_BYTES:
            _fail()


@dataclass(frozen=True, slots=True)
class VerifiedAuthenticationVerificationMethodEvidence:
    claims_sha256: bytes
    authority: str
    accepted: bool

    def __post_init__(self) -> None:
        if type(self.claims_sha256) is not bytes or len(self.claims_sha256) != 32:
            _fail()
        _absolute_uri(self.authority)
        if type(self.accepted) is not bool:
            _fail()


class AuthenticationVerificationMethodEvidenceTrustVerifier(Protocol):
    def verify_authentication_verification_method_evidence(
        self,
        envelope: MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    ) -> VerifiedAuthenticationVerificationMethodEvidence: ...


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail()


def _claim_document(claims: MarketplaceAuthenticationVerificationMethodEvidenceClaims) -> dict[str, object]:
    return {
        "authority": claims.authority,
        "entries": [
            {
                "controllerPrincipal": entry.controller_principal,
                "publicKey": encode_marketplace_auth_verification_public_key(entry.public_key),
                "validFrom": entry.valid_from,
                "validUntil": entry.valid_until,
                "verificationMethod": entry.verification_method,
            }
            for entry in claims.entries
        ],
        "expiresAt": claims.expires_at,
        "issuedAt": claims.issued_at,
        "type": AUTH_EVIDENCE_BUNDLE_TYPE,
        "version": AUTH_EVIDENCE_BUNDLE_VERSION,
    }


def encode_marketplace_authentication_verification_method_evidence_claims(
    claims: MarketplaceAuthenticationVerificationMethodEvidenceClaims,
) -> bytes:
    if type(claims) is not MarketplaceAuthenticationVerificationMethodEvidenceClaims:
        _fail()
    raw = json.dumps(
        _claim_document(claims),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", "strict")
    if len(raw) > AUTH_EVIDENCE_CLAIMS_MAX_BYTES:
        _fail()
    return raw


def decode_marketplace_authentication_verification_method_evidence_claims(
    raw: object,
) -> MarketplaceAuthenticationVerificationMethodEvidenceClaims:
    if type(raw) is not bytes or not raw or len(raw) > AUTH_EVIDENCE_CLAIMS_MAX_BYTES:
        _fail()
    if raw.startswith(b"\\xef\\xbb\\xbf"):
        _fail()
    try:
        text = raw.decode("utf-8", "strict")
        document = json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        _fail()
    if type(document) is not dict or frozenset(document) != _TOP_LEVEL_KEYS:
        _fail()
    if document["type"] != AUTH_EVIDENCE_BUNDLE_TYPE:
        _fail()
    if type(document["version"]) is not int or document["version"] != AUTH_EVIDENCE_BUNDLE_VERSION:
        _fail()
    entries_document = document["entries"]
    if type(entries_document) is not list or not (1 <= len(entries_document) <= AUTH_EVIDENCE_MAX_ENTRIES):
        _fail()
    entries: list[AuthenticationVerificationMethodEvidenceClaim] = []
    for item in entries_document:
        if type(item) is not dict or frozenset(item) != _ENTRY_KEYS:
            _fail()
        entries.append(
            AuthenticationVerificationMethodEvidenceClaim(
                verification_method=item["verificationMethod"],
                controller_principal=item["controllerPrincipal"],
                public_key=parse_marketplace_auth_verification_public_key(item["publicKey"]),
                valid_from=_optional_time(item["validFrom"]),
                valid_until=_optional_time(item["validUntil"]),
            )
        )
    claims = MarketplaceAuthenticationVerificationMethodEvidenceClaims(
        authority=document["authority"],
        issued_at=_time(document["issuedAt"]),
        expires_at=_time(document["expiresAt"]),
        entries=tuple(entries),
    )
    if encode_marketplace_authentication_verification_method_evidence_claims(claims) != raw:
        _fail()
    return claims


def materialize_marketplace_authentication_verification_method_snapshot(
    *,
    envelope: MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    trust_verifier: AuthenticationVerificationMethodEvidenceTrustVerifier,
    at_time: int,
) -> MarketplaceAuthenticationVerificationMethodSnapshot:
    if type(envelope) is not MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
        _fail()
    reviewed_time = _time(at_time)
    claims = decode_marketplace_authentication_verification_method_evidence_claims(envelope.claims_json)
    verifier = getattr(trust_verifier, "verify_authentication_verification_method_evidence", None)
    if not callable(verifier):
        _fail()
    try:
        verified = verifier(envelope)
    except Exception:
        _fail()
    if type(verified) is not VerifiedAuthenticationVerificationMethodEvidence:
        _fail()
    if verified.accepted is not True:
        _fail()
    if verified.claims_sha256 != hashlib.sha256(envelope.claims_json).digest():
        _fail()
    if verified.authority != claims.authority:
        _fail()
    if reviewed_time < claims.issued_at or reviewed_time >= claims.expires_at:
        _fail()

    projected: list[AuthenticationVerificationMethodEvidence] = []
    try:
        for entry in claims.entries:
            effective_start = max(claims.issued_at, entry.valid_from if entry.valid_from is not None else claims.issued_at)
            effective_end = min(claims.expires_at, entry.valid_until if entry.valid_until is not None else claims.expires_at)
            if effective_start >= effective_end:
                _fail()
            projected.append(
                AuthenticationVerificationMethodEvidence(
                    verification_method=entry.verification_method,
                    controller_principal=entry.controller_principal,
                    public_key=entry.public_key,
                    valid_from=effective_start,
                    valid_until=effective_end,
                )
            )
        return MarketplaceAuthenticationVerificationMethodSnapshot(projected)
    except AuthenticationVerificationMethodSnapshotError:
        _fail()


__all__ = [
    "AUTH_EVIDENCE_ATTESTATION_MAX_BYTES",
    "AUTH_EVIDENCE_BUNDLE_TYPE",
    "AUTH_EVIDENCE_BUNDLE_VERSION",
    "AUTH_EVIDENCE_CLAIMS_MAX_BYTES",
    "AUTH_EVIDENCE_MAX_ENTRIES",
    "AUTH_EVIDENCE_MAX_LEASE_SECONDS",
    "AUTH_EVIDENCE_PUBLIC_KEY_BYTES",
    "AUTH_EVIDENCE_PUBLIC_KEY_PAYLOAD_CHARS",
    "AUTH_EVIDENCE_PUBLIC_KEY_PREFIX",
    "AUTH_EVIDENCE_URI_MAX_BYTES",
    "AuthenticationVerificationMethodEvidenceClaim",
    "AuthenticationVerificationMethodEvidenceError",
    "AuthenticationVerificationMethodEvidenceTrustVerifier",
    "MarketplaceAuthenticationVerificationMethodEvidenceClaims",
    "MarketplaceAuthenticationVerificationMethodEvidenceEnvelope",
    "PROFILE_NAME",
    "VerifiedAuthenticationVerificationMethodEvidence",
    "decode_marketplace_authentication_verification_method_evidence_claims",
    "encode_marketplace_auth_verification_public_key",
    "encode_marketplace_authentication_verification_method_evidence_claims",
    "materialize_marketplace_authentication_verification_method_snapshot",
    "parse_marketplace_auth_verification_public_key",
]
