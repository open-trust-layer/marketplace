"""M17.5N canonical static authentication trust-anchor manifest intake.

This module accepts only caller-supplied canonical bytes and materializes them
into the existing immutable M17.5M trust-anchor snapshot. It performs no
acquisition, refresh, persistence, replacement, or runtime selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Final

from .auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
    AuthenticationEvidenceTrustError,
    MarketplaceAuthenticationEvidenceTrustAnchorSnapshot,
)
from .auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceError,
    encode_marketplace_auth_verification_public_key,
    parse_marketplace_auth_verification_public_key,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_TRUST_ANCHOR_MANIFEST_V1"
AUTH_TRUST_ANCHOR_MANIFEST_TYPE: Final = (
    "MarketplaceAuthenticationEvidenceTrustAnchorManifest"
)
AUTH_TRUST_ANCHOR_MANIFEST_VERSION: Final = 1
AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES: Final = 256 * 1024
AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS: Final = 64
_TOP_LEVEL_KEYS = frozenset({"anchors", "type", "version"})
_ANCHOR_KEYS = frozenset({"authority", "publicKey"})


class AuthenticationTrustAnchorManifestError(ValueError):
    """Stable fail-closed manifest error without input reflection."""

    def __init__(self) -> None:
        super().__init__(
            "authentication trust-anchor manifest is invalid or unavailable"
        )


def _fail() -> None:
    raise AuthenticationTrustAnchorManifestError() from None


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEvidenceTrustAnchorManifest:
    """Canonical public trust-anchor manifest value."""

    anchors: tuple[AuthenticationEvidenceTrustAnchor, ...]

    def __post_init__(self) -> None:
        if type(self.anchors) is not tuple:
            _fail()
        if not (1 <= len(self.anchors) <= AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS):
            _fail()
        seen: set[str] = set()
        for anchor in self.anchors:
            if type(anchor) is not AuthenticationEvidenceTrustAnchor:
                _fail()
            if anchor.authority in seen:
                _fail()
            seen.add(anchor.authority)


def _manifest_document(
    manifest: MarketplaceAuthenticationEvidenceTrustAnchorManifest,
) -> dict[str, object]:
    return {
        "anchors": [
            {
                "authority": anchor.authority,
                "publicKey": encode_marketplace_auth_verification_public_key(
                    anchor.public_key
                ),
            }
            for anchor in manifest.anchors
        ],
        "type": AUTH_TRUST_ANCHOR_MANIFEST_TYPE,
        "version": AUTH_TRUST_ANCHOR_MANIFEST_VERSION,
    }


def encode_marketplace_authentication_trust_anchor_manifest(
    manifest: MarketplaceAuthenticationEvidenceTrustAnchorManifest,
) -> bytes:
    """Encode one manifest to the exact canonical UTF-8 JSON form."""

    if type(manifest) is not MarketplaceAuthenticationEvidenceTrustAnchorManifest:
        _fail()
    try:
        raw = json.dumps(
            _manifest_document(manifest),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (AuthenticationVerificationMethodEvidenceError, TypeError, ValueError):
        _fail()
    if len(raw) > AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES:
        _fail()
    return raw


def decode_marketplace_authentication_trust_anchor_manifest(
    raw: object,
) -> MarketplaceAuthenticationEvidenceTrustAnchorManifest:
    """Decode exact canonical caller-supplied manifest bytes."""

    if type(raw) is not bytes or not raw:
        _fail()
    if len(raw) > AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES:
        _fail()
    if raw.startswith(b"\xef\xbb\xbf"):
        _fail()
    try:
        text = raw.decode("utf-8", "strict")
        document = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (
        AuthenticationTrustAnchorManifestError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        _fail()
    if type(document) is not dict or frozenset(document) != _TOP_LEVEL_KEYS:
        _fail()
    if document["type"] != AUTH_TRUST_ANCHOR_MANIFEST_TYPE:
        _fail()
    if (
        type(document["version"]) is not int
        or document["version"] != AUTH_TRUST_ANCHOR_MANIFEST_VERSION
    ):
        _fail()

    anchor_documents = document["anchors"]
    if type(anchor_documents) is not list:
        _fail()
    if not (1 <= len(anchor_documents) <= AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS):
        _fail()

    anchors: list[AuthenticationEvidenceTrustAnchor] = []
    try:
        for item in anchor_documents:
            if type(item) is not dict or frozenset(item) != _ANCHOR_KEYS:
                _fail()
            anchors.append(
                AuthenticationEvidenceTrustAnchor(
                    authority=item["authority"],
                    public_key=parse_marketplace_auth_verification_public_key(
                        item["publicKey"]
                    ),
                )
            )
        manifest = MarketplaceAuthenticationEvidenceTrustAnchorManifest(
            anchors=tuple(anchors)
        )
    except (
        AuthenticationEvidenceTrustError,
        AuthenticationVerificationMethodEvidenceError,
        AuthenticationTrustAnchorManifestError,
        TypeError,
        ValueError,
    ):
        _fail()

    if encode_marketplace_authentication_trust_anchor_manifest(manifest) != raw:
        _fail()
    return manifest


def materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
    raw: object,
) -> MarketplaceAuthenticationEvidenceTrustAnchorSnapshot:
    """Materialize one immutable M17.5M snapshot from canonical manifest bytes."""

    manifest = decode_marketplace_authentication_trust_anchor_manifest(raw)
    try:
        return MarketplaceAuthenticationEvidenceTrustAnchorSnapshot(
            list(manifest.anchors)
        )
    except AuthenticationEvidenceTrustError:
        _fail()


__all__ = [
    "AUTH_TRUST_ANCHOR_MANIFEST_MAX_ANCHORS",
    "AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES",
    "AUTH_TRUST_ANCHOR_MANIFEST_TYPE",
    "AUTH_TRUST_ANCHOR_MANIFEST_VERSION",
    "AuthenticationTrustAnchorManifestError",
    "MarketplaceAuthenticationEvidenceTrustAnchorManifest",
    "PROFILE_NAME",
    "decode_marketplace_authentication_trust_anchor_manifest",
    "encode_marketplace_authentication_trust_anchor_manifest",
    "materialize_marketplace_authentication_evidence_trust_anchor_snapshot",
]
