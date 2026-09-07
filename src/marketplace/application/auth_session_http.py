"""M17.5D source-only challenge/session establishment HTTP contract."""
from __future__ import annotations

import base64
import json
import math
import re
from typing import Any, Protocol

from .auth import (
    AUTH_CHALLENGE_MAX_AGE_SECONDS,
    AUTH_MAX_ACTIVE_SESSIONS,
    AUTH_MAX_ACTIVE_SESSIONS_PER_PRINCIPAL,
    AUTH_MAX_OUTSTANDING_CHALLENGES,
    AUTH_MAX_OUTSTANDING_CHALLENGES_PER_BINDING,
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    AUTH_SESSION_ABSOLUTE_SECONDS,
    AUTH_SESSION_IDLE_SECONDS,
    ApplicationAuthError,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from .auth_challenge import (
    MarketplaceChallengeTransportError,
    encode_marketplace_auth_challenge,
    parse_marketplace_auth_challenge,
)
from .http import ApplicationHttpRequest, ApplicationHttpResponse, _error_response, _json_response

AUTH_REQUEST_MAX_BYTES = 64 * 1024
MAX_PROOF_JSON_BYTES = 48 * 1024
MAX_JSON_DEPTH = 8
MAX_JSON_OBJECT_KEYS = 64
MAX_JSON_ARRAY_ITEMS = 64
MAX_JSON_STRING_BYTES = 8192
MAX_OUTSTANDING_CHALLENGES = AUTH_MAX_OUTSTANDING_CHALLENGES
MAX_OUTSTANDING_CHALLENGES_PER_BINDING = AUTH_MAX_OUTSTANDING_CHALLENGES_PER_BINDING
MAX_ACTIVE_SESSIONS = AUTH_MAX_ACTIVE_SESSIONS
MAX_ACTIVE_SESSIONS_PER_PRINCIPAL = AUTH_MAX_ACTIVE_SESSIONS_PER_PRINCIPAL
_AUTH_URI_MAX_BYTES = 2048
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_SESSION_PREFIX = "mkt1_"


class CredentialMaterialSource(Protocol):
    def challenge_bytes(self) -> bytes: ...
    def session_token_bytes(self) -> bytes: ...


class AuthenticationProofVerifier(Protocol):
    def verify(self, proof_document: object) -> VerifiedAuthenticationProof: ...


def _error(status: int, reason: str, code: str, message: str) -> ApplicationHttpResponse:
    return _error_response(status, reason, code, message)


def _auth_request_invalid() -> ApplicationHttpResponse:
    return _error(400, "Bad Request", "AUTH_REQUEST_INVALID", "authentication request is invalid")


def _auth_required() -> ApplicationHttpResponse:
    return _error(401, "Unauthorized", "AUTH_REQUIRED", "application authentication is required")


def _auth_session_invalid() -> ApplicationHttpResponse:
    return _error(401, "Unauthorized", "AUTH_SESSION_INVALID", "application session is invalid")


def _absolute_uri(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("invalid URI")
    encoded = value.encode("utf-8", "strict")
    if len(encoded) > _AUTH_URI_MAX_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError("invalid URI")
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len(pairs) > MAX_JSON_OBJECT_KEYS:
        raise ValueError("too many object keys")
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON number")


def _review_json_value(value: object, *, depth: int = 1) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError("JSON depth exceeded")
    if isinstance(value, str):
        if len(value.encode("utf-8", "strict")) > MAX_JSON_STRING_BYTES:
            raise ValueError("JSON string exceeded")
        return
    if value is None or type(value) is bool or type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return
    if type(value) is list:
        if len(value) > MAX_JSON_ARRAY_ITEMS:
            raise ValueError("JSON array exceeded")
        for item in value:
            _review_json_value(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > MAX_JSON_OBJECT_KEYS:
            raise ValueError("JSON object exceeded")
        for key, item in value.items():
            _review_json_value(key, depth=depth + 1)
            _review_json_value(item, depth=depth + 1)
        return
    raise ValueError("unsupported JSON value")


def _decode_auth_object(body: bytes) -> dict[str, Any]:
    if type(body) is not bytes or not body or len(body) > AUTH_REQUEST_MAX_BYTES:
        raise ValueError("auth body outside bound")
    if body.startswith(b"\xef\xbb\xbf"):
        raise ValueError("BOM forbidden")
    text = body.decode("utf-8", "strict")
    document = json.loads(text, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    if type(document) is not dict:
        raise ValueError("auth body must be object")
    _review_json_value(document)
    return document


def _review_proof(document: object) -> dict[str, Any]:
    if type(document) is not dict:
        raise ValueError("proof must be object")
    _review_json_value(document)
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", "strict")
    if len(encoded) > MAX_PROOF_JSON_BYTES:
        raise ValueError("proof exceeds byte bound")
    return document


def _encode_session_token(token: bytes) -> str:
    if type(token) is not bytes or len(token) != 32:
        raise ValueError("session token must be exact 32 bytes")
    payload = base64.urlsafe_b64encode(token).rstrip(b"=").decode("ascii")
    if len(payload) != 43:
        raise ValueError("session token encoding failed")
    return _SESSION_PREFIX + payload


def _auth_failure(exc: ApplicationAuthError) -> ApplicationHttpResponse:
    if exc.code in {"AUTH_CHALLENGE_INVALID", "AUTH_CHALLENGE_EXPIRED", "AUTH_TIME_INVALID"}:
        return _error(401, "Unauthorized", "AUTH_CHALLENGE_INVALID", "authentication challenge is invalid")
    if exc.code == "AUTH_PROOF_INVALID":
        return _error(401, "Unauthorized", "AUTH_PROOF_INVALID", "authentication proof is invalid")
    if exc.code == "AUTH_PRINCIPAL_BINDING_REJECTED":
        return _error(403, "Forbidden", "AUTH_PRINCIPAL_BINDING_REJECTED", "principal binding was rejected")
    if exc.code == "AUTH_PRINCIPAL_BINDING_UNAVAILABLE":
        return _error(503, "Service Unavailable", "AUTH_PRINCIPAL_BINDING_UNAVAILABLE", "principal binding is unavailable")
    if exc.code == "AUTH_CAPACITY_EXCEEDED":
        return _error(503, "Service Unavailable", "AUTH_CAPACITY_EXCEEDED", "authentication capacity is exhausted")
    if exc.code in {"AUTH_CHALLENGE_REUSED", "AUTH_SESSION_TOKEN_REUSED"}:
        return _error(503, "Service Unavailable", "AUTH_MATERIAL_UNAVAILABLE", "credential material is unavailable")
    if exc.code in {"AUTH_SESSION_INVALID", "AUTH_SESSION_EXPIRED"}:
        return _auth_session_invalid()
    return _error(503, "Service Unavailable", "AUTH_PROOF_VERIFIER_UNAVAILABLE", "authentication verification is unavailable")


def _request_shape(request: ApplicationHttpRequest, *, body: bool) -> bool:
    if type(request) is not ApplicationHttpRequest or request.query:
        return False
    if body:
        return request.content_type == "application/json" and 0 < len(request.body) <= AUTH_REQUEST_MAX_BYTES
    return request.content_type is None and request.body == b""


class MarketplaceAuthenticationSessionHttpAdapter:
    """Four reviewed auth-establishment routes with injected-only authority."""

    __slots__ = (
        "_auth",
        "_challenge_bytes",
        "_session_token_bytes",
        "_verify_proof",
    )

    def __init__(
        self,
        *,
        auth: MarketplaceApplicationAuthService,
        material_source: CredentialMaterialSource,
        proof_verifier: AuthenticationProofVerifier,
    ) -> None:
        if type(auth) is not MarketplaceApplicationAuthService:
            raise TypeError("auth MUST be exact MarketplaceApplicationAuthService")
        challenge_bytes = getattr(material_source, "challenge_bytes", None)
        session_token_bytes = getattr(material_source, "session_token_bytes", None)
        verify = getattr(proof_verifier, "verify", None)
        if not callable(challenge_bytes) or not callable(session_token_bytes):
            raise TypeError("material_source MUST provide exact material callables")
        if not callable(verify):
            raise TypeError("proof_verifier MUST provide callable verify")
        self._auth = auth
        self._challenge_bytes = challenge_bytes
        self._session_token_bytes = session_token_bytes
        self._verify_proof = verify

    def handle(
        self,
        request: ApplicationHttpRequest,
        *,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if type(session_invalid) is not bool:
            raise TypeError("session_invalid MUST be exact bool")
        if type(now) is not int or now < 0:
            raise ValueError("now MUST be a non-negative exact integer")
        if request.path == "/api/auth/challenges" and request.method == "POST":
            return self._challenge(request, session_token, session_invalid, now)
        if request.path == "/api/auth/sessions" and request.method == "POST":
            return self._session(request, session_token, session_invalid, now)
        if request.path == "/api/auth/session" and request.method == "GET":
            return self._inspect(request, session_token, session_invalid, now)
        if request.path == "/api/auth/logout" and request.method == "POST":
            return self._logout(request, session_token, session_invalid, now)
        if session_invalid or session_token is not None:
            return _auth_session_invalid()
        return _error(404, "Not Found", "NOT_FOUND", "resource not found")

    def _challenge(
        self,
        request: ApplicationHttpRequest,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if session_invalid or session_token is not None:
            return _auth_session_invalid()
        if not _request_shape(request, body=True):
            return _auth_request_invalid()
        try:
            document = _decode_auth_object(request.body)
            if frozenset(document) != frozenset({"principal", "verification_method"}):
                raise ValueError("unexpected keys")
            principal = _absolute_uri(document["principal"])
            method = _absolute_uri(document["verification_method"])
        except (TypeError, ValueError, UnicodeError, json.JSONDecodeError):
            return _auth_request_invalid()
        try:
            challenge = self._challenge_bytes()
        except Exception:
            return _error(503, "Service Unavailable", "AUTH_MATERIAL_UNAVAILABLE", "credential material is unavailable")
        if type(challenge) is not bytes or len(challenge) != 32:
            return _error(503, "Service Unavailable", "AUTH_MATERIAL_UNAVAILABLE", "credential material is unavailable")
        try:
            self._auth.register_challenge(
                challenge=challenge,
                principal=principal,
                verification_method=method,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_failure(exc)
        return _json_response(
            201,
            "Created",
            {
                "challenge": encode_marketplace_auth_challenge(challenge),
                "domain": AUTH_PROOF_DOMAIN,
                "proof_purpose": AUTH_PROOF_PURPOSE,
                "expires_in_seconds": AUTH_CHALLENGE_MAX_AGE_SECONDS,
            },
        )

    def _session(
        self,
        request: ApplicationHttpRequest,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if session_invalid or session_token is not None:
            return _auth_session_invalid()
        if not _request_shape(request, body=True):
            return _auth_request_invalid()
        try:
            document = _decode_auth_object(request.body)
            if frozenset(document) != frozenset({"challenge", "proof"}):
                raise ValueError("unexpected keys")
            challenge = parse_marketplace_auth_challenge(document["challenge"])
            proof_document = _review_proof(document["proof"])
        except (TypeError, ValueError, UnicodeError, json.JSONDecodeError, MarketplaceChallengeTransportError):
            return _auth_request_invalid()
        try:
            attempt = self._auth.begin_challenge_attempt(challenge=challenge, now=now)
        except ApplicationAuthError as exc:
            return _auth_failure(exc)
        try:
            proof = self._verify_proof(proof_document)
        except Exception:
            return _error(
                503,
                "Service Unavailable",
                "AUTH_PROOF_VERIFIER_UNAVAILABLE",
                "authentication proof verifier is unavailable",
            )
        if type(proof) is not VerifiedAuthenticationProof:
            return _error(
                503,
                "Service Unavailable",
                "AUTH_PROOF_VERIFIER_UNAVAILABLE",
                "authentication proof verifier is unavailable",
            )
        try:
            raw_token = self._session_token_bytes()
        except Exception:
            return _error(503, "Service Unavailable", "AUTH_MATERIAL_UNAVAILABLE", "credential material is unavailable")
        if type(raw_token) is not bytes or len(raw_token) != 32:
            return _error(503, "Service Unavailable", "AUTH_MATERIAL_UNAVAILABLE", "credential material is unavailable")
        try:
            view = self._auth.authenticate_challenge_attempt(
                attempt=attempt,
                proof=proof,
                session_token=raw_token,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_failure(exc)
        try:
            token_text = _encode_session_token(raw_token)
        except ValueError:
            return _error(503, "Service Unavailable", "AUTH_MATERIAL_UNAVAILABLE", "credential material is unavailable")
        return _json_response(
            201,
            "Created",
            {
                "session_token": token_text,
                "principal": view.principal,
                "verification_method": view.verification_method,
                "idle_timeout_seconds": AUTH_SESSION_IDLE_SECONDS,
                "absolute_timeout_seconds": AUTH_SESSION_ABSOLUTE_SECONDS,
            },
        )

    def _inspect(
        self,
        request: ApplicationHttpRequest,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if session_invalid:
            return _auth_session_invalid()
        if session_token is None:
            return _auth_required()
        if type(session_token) is not bytes or len(session_token) != 32:
            return _auth_session_invalid()
        if not _request_shape(request, body=False):
            return _auth_request_invalid()
        try:
            view = self._auth.validate_session(session_token=session_token, now=now)
        except ApplicationAuthError:
            return _auth_session_invalid()
        return _json_response(
            200,
            "OK",
            {
                "principal": view.principal,
                "verification_method": view.verification_method,
                "issued_at": view.issued_at,
                "last_used_at": view.last_used_at,
                "absolute_expires_at": view.absolute_expires_at,
            },
        )

    def _logout(
        self,
        request: ApplicationHttpRequest,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if session_invalid:
            return _auth_session_invalid()
        if session_token is None:
            return _auth_required()
        if type(session_token) is not bytes or len(session_token) != 32:
            return _auth_session_invalid()
        if not _request_shape(request, body=False):
            return _auth_request_invalid()
        try:
            self._auth.revoke_session(session_token=session_token, now=now)
        except ApplicationAuthError:
            return _auth_session_invalid()
        return _json_response(200, "OK", {"status": "REVOKED"})


__all__ = [
    "AUTH_REQUEST_MAX_BYTES",
    "AuthenticationProofVerifier",
    "CredentialMaterialSource",
    "MAX_ACTIVE_SESSIONS",
    "MAX_ACTIVE_SESSIONS_PER_PRINCIPAL",
    "MAX_JSON_ARRAY_ITEMS",
    "MAX_JSON_DEPTH",
    "MAX_JSON_OBJECT_KEYS",
    "MAX_JSON_STRING_BYTES",
    "MAX_OUTSTANDING_CHALLENGES",
    "MAX_OUTSTANDING_CHALLENGES_PER_BINDING",
    "MAX_PROOF_JSON_BYTES",
    "MarketplaceAuthenticationSessionHttpAdapter",
]
