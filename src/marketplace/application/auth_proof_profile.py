"""M17.5H source-only authentication proof transcript and custody contract."""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
from typing import Final, Protocol

from .auth import AUTH_PROOF_DOMAIN, AUTH_PROOF_PURPOSE
from .auth_challenge import (
    MarketplaceChallengeTransportError,
    encode_marketplace_auth_challenge,
    parse_marketplace_auth_challenge,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_PROOF_TRANSCRIPT_V1"
AUTH_PROOF_TYPE: Final = "MarketplaceAuthenticationProof"
AUTH_PROOF_VERSION: Final = 1
AUTH_PROOF_CRYPTOSUITE: Final = (
    "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1"
)
AUTH_SIGNATURE_PREFIX: Final = "mks1_"
AUTH_SIGNATURE_BYTES: Final = 64
AUTH_SIGNATURE_PAYLOAD_CHARS: Final = 86
AUTH_SIGNATURE_TEXT_CHARS: Final = 91
AUTH_PROOF_JSON_MAX_BYTES: Final = 48 * 1024
AUTH_TRANSCRIPT_DOMAIN_SEPARATOR: Final = b"MARKETPLACE-AUTH"
_AUTH_URI_MAX_BYTES: Final = 2048
_BASE64URL: Final = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_PROOF_KEYS: Final = frozenset(
    {
        "type",
        "version",
        "cryptosuite",
        "proofPurpose",
        "verificationMethod",
        "domain",
        "challenge",
        "proofValue",
    }
)


class MarketplaceAuthenticationProofProfileError(ValueError):
    """Stable fail-closed profile error without proof/signature reflection."""

    def __init__(self) -> None:
        super().__init__("application authentication proof is invalid")
        self.code = "AUTH_PROOF_INVALID"


def _fail() -> None:
    raise MarketplaceAuthenticationProofProfileError() from None


def _absolute_uri(value: object) -> str:
    if type(value) is not str or not value:
        _fail()
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        _fail()
    if len(encoded) > _AUTH_URI_MAX_BYTES or _URI_RE.fullmatch(value) is None:
        _fail()
    return value


def _fixed_bytes(value: object, *, size: int) -> bytes:
    if type(value) is not bytes or len(value) != size:
        _fail()
    return value


def _length_prefixed_utf8(value: str) -> bytes:
    encoded = value.encode("utf-8", "strict")
    if len(encoded) > 0xFFFF:
        _fail()
    return len(encoded).to_bytes(2, "big") + encoded


def encode_marketplace_auth_signature(signature: object) -> str:
    raw = _fixed_bytes(signature, size=AUTH_SIGNATURE_BYTES)
    payload = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if len(payload) != AUTH_SIGNATURE_PAYLOAD_CHARS:
        _fail()
    return AUTH_SIGNATURE_PREFIX + payload


def parse_marketplace_auth_signature(value: object) -> bytes:
    if type(value) is not str or len(value) != AUTH_SIGNATURE_TEXT_CHARS:
        _fail()
    if not value.startswith(AUTH_SIGNATURE_PREFIX):
        _fail()
    payload = value[len(AUTH_SIGNATURE_PREFIX):]
    if len(payload) != AUTH_SIGNATURE_PAYLOAD_CHARS or any(char not in _BASE64URL for char in payload):
        _fail()
    try:
        raw_payload = payload.encode("ascii", "strict")
        signature = base64.b64decode(raw_payload + b"==", altchars=b"-_", validate=True)
    except (UnicodeEncodeError, ValueError, TypeError):
        _fail()
    if len(signature) != AUTH_SIGNATURE_BYTES:
        _fail()
    if base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii") != payload:
        _fail()
    return signature


@dataclass(frozen=True, slots=True)
class AuthenticationProofSigningRequest:
    """Purpose-specific signing request; contains no arbitrary message or key material."""

    verification_method: str
    challenge: bytes

    def __post_init__(self) -> None:
        _absolute_uri(self.verification_method)
        _fixed_bytes(self.challenge, size=32)


class AuthenticationProofSigner(Protocol):
    """Injected custody seam for this exact profile; not a generic signing oracle."""

    def sign_authentication_proof(self, request: AuthenticationProofSigningRequest) -> bytes: ...


def build_marketplace_auth_transcript(request: AuthenticationProofSigningRequest) -> bytes:
    if type(request) is not AuthenticationProofSigningRequest:
        _fail()
    return b"".join(
        (
            AUTH_TRANSCRIPT_DOMAIN_SEPARATOR,
            b"\x00",
            bytes((AUTH_PROOF_VERSION,)),
            _length_prefixed_utf8(AUTH_PROOF_CRYPTOSUITE),
            _length_prefixed_utf8(AUTH_PROOF_PURPOSE),
            _length_prefixed_utf8(request.verification_method),
            _length_prefixed_utf8(AUTH_PROOF_DOMAIN),
            request.challenge,
        )
    )


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationProof:
    type: str
    version: int
    cryptosuite: str
    proof_purpose: str
    verification_method: str
    domain: str
    challenge: bytes
    proof_value: bytes

    def __post_init__(self) -> None:
        if self.type != AUTH_PROOF_TYPE:
            _fail()
        if type(self.version) is not int or self.version != AUTH_PROOF_VERSION:
            _fail()
        if self.cryptosuite != AUTH_PROOF_CRYPTOSUITE:
            _fail()
        if self.proof_purpose != AUTH_PROOF_PURPOSE:
            _fail()
        _absolute_uri(self.verification_method)
        if self.domain != AUTH_PROOF_DOMAIN:
            _fail()
        _fixed_bytes(self.challenge, size=32)
        _fixed_bytes(self.proof_value, size=AUTH_SIGNATURE_BYTES)

    def signing_request(self) -> AuthenticationProofSigningRequest:
        return AuthenticationProofSigningRequest(
            verification_method=self.verification_method,
            challenge=self.challenge,
        )

    def to_document(self) -> dict[str, object]:
        return {
            "type": self.type,
            "version": self.version,
            "cryptosuite": self.cryptosuite,
            "proofPurpose": self.proof_purpose,
            "verificationMethod": self.verification_method,
            "domain": self.domain,
            "challenge": encode_marketplace_auth_challenge(self.challenge),
            "proofValue": encode_marketplace_auth_signature(self.proof_value),
        }


def make_marketplace_authentication_proof(
    request: AuthenticationProofSigningRequest,
    signature: object,
) -> MarketplaceAuthenticationProof:
    if type(request) is not AuthenticationProofSigningRequest:
        _fail()
    return MarketplaceAuthenticationProof(
        type=AUTH_PROOF_TYPE,
        version=AUTH_PROOF_VERSION,
        cryptosuite=AUTH_PROOF_CRYPTOSUITE,
        proof_purpose=AUTH_PROOF_PURPOSE,
        verification_method=request.verification_method,
        domain=AUTH_PROOF_DOMAIN,
        challenge=request.challenge,
        proof_value=_fixed_bytes(signature, size=AUTH_SIGNATURE_BYTES),
    )


def parse_marketplace_authentication_proof_document(document: object) -> MarketplaceAuthenticationProof:
    if type(document) is not dict or frozenset(document) != _PROOF_KEYS:
        _fail()
    try:
        challenge = parse_marketplace_auth_challenge(document["challenge"])
    except MarketplaceChallengeTransportError:
        _fail()
    return MarketplaceAuthenticationProof(
        type=document["type"],
        version=document["version"],
        cryptosuite=document["cryptosuite"],
        proof_purpose=document["proofPurpose"],
        verification_method=document["verificationMethod"],
        domain=document["domain"],
        challenge=challenge,
        proof_value=parse_marketplace_auth_signature(document["proofValue"]),
    )


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail()


def decode_marketplace_authentication_proof_json(raw: object) -> MarketplaceAuthenticationProof:
    if type(raw) is not bytes or not raw or len(raw) > AUTH_PROOF_JSON_MAX_BYTES:
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
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        _fail()
    return parse_marketplace_authentication_proof_document(document)


def encode_marketplace_authentication_proof_json(proof: MarketplaceAuthenticationProof) -> bytes:
    if type(proof) is not MarketplaceAuthenticationProof:
        _fail()
    return json.dumps(
        proof.to_document(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", "strict")


__all__ = [
    "AUTH_PROOF_CRYPTOSUITE",
    "AUTH_PROOF_JSON_MAX_BYTES",
    "AUTH_PROOF_TYPE",
    "AUTH_PROOF_VERSION",
    "AUTH_SIGNATURE_BYTES",
    "AUTH_SIGNATURE_PAYLOAD_CHARS",
    "AUTH_SIGNATURE_PREFIX",
    "AUTH_SIGNATURE_TEXT_CHARS",
    "AUTH_TRANSCRIPT_DOMAIN_SEPARATOR",
    "AuthenticationProofSigner",
    "AuthenticationProofSigningRequest",
    "MarketplaceAuthenticationProof",
    "MarketplaceAuthenticationProofProfileError",
    "PROFILE_NAME",
    "build_marketplace_auth_transcript",
    "decode_marketplace_authentication_proof_json",
    "encode_marketplace_auth_signature",
    "encode_marketplace_authentication_proof_json",
    "make_marketplace_authentication_proof",
    "parse_marketplace_auth_signature",
    "parse_marketplace_authentication_proof_document",
]
