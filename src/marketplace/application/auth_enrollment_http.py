"""M17.6I authenticated enrollment HTTP carrier without runtime selection.

This module exposes two framework-neutral authenticated enrollment routes over the
already-reviewed M17.6D/G/H boundaries. It does not select ASGI, startup/runtime
composition, a nonce material source, persistence, policy implementation, attestor
provider, browser activation, or deployment.
"""
from __future__ import annotations

import base64
import re
from typing import Final

from .auth import (
    AUTH_SESSION_TOKEN_BYTES,
    ApplicationAuthError,
    MarketplaceApplicationAuthService,
)
from .auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityAttestor,
    AuthenticationEnrollmentAuthorityError,
    MarketplaceAuthenticationEnrollmentProposal,
)
from .auth_enrollment_coordination import (
    AUTH_ENROLLMENT_NONCE_BYTES,
    AuthenticationEnrollmentCoordinationError,
    coordinate_marketplace_authentication_enrollment,
)
from .auth_enrollment_nonce import (
    AuthenticationEnrollmentNonceError,
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from .auth_enrollment_policy import AuthenticationEnrollmentApprovalPolicy
from .auth_verification_method_evidence import (
    AUTH_EVIDENCE_ATTESTATION_MAX_BYTES,
    AUTH_EVIDENCE_CLAIMS_MAX_BYTES,
    AUTH_EVIDENCE_MAX_LEASE_SECONDS,
    AUTH_EVIDENCE_URI_MAX_BYTES,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
)
from .http import (
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    _decode_json_object_bytes,
    _error_response,
    _json_response,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1"
WEB_PROPOSAL_PROFILE: Final = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1"
WEB_PROPOSAL_TYPE: Final = "MarketplaceAuthenticationEnrollmentProposal"
NONCE_RESPONSE_TYPE: Final = "MarketplaceAuthenticationEnrollmentNonce"
EVIDENCE_RESPONSE_TYPE: Final = "MarketplaceAuthenticationVerificationMethodEvidenceEnvelope"

AUTH_ENROLLMENT_NONCE_ROUTE: Final = "/api/authentication-enrollment/nonces"
AUTH_ENROLLMENT_EVIDENCE_ROUTE: Final = "/api/authentication-enrollment/evidence"
AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES: Final = 16 * 1024

AUTH_ENROLLMENT_NONCE_PREFIX: Final = "mken1_"
AUTH_ENROLLMENT_NONCE_PAYLOAD_CHARS: Final = 43
AUTH_ENROLLMENT_CLAIMS_PREFIX: Final = "mkec1_"
AUTH_ENROLLMENT_ATTESTATION_PREFIX: Final = "mkea1_"

_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_BASE64URL = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
_PROPOSAL_KEYS = frozenset(
    {"profile", "type", "principal", "verificationMethod", "publicKey"}
)
_NONCE_REQUEST_KEYS = frozenset({"profile", "proposal"})
_EVIDENCE_REQUEST_KEYS = frozenset({"profile", "proposal", "nonce"})


class AuthenticationEnrollmentHttpError(ValueError):
    """Stable source/composition error without enrollment-data reflection."""

    def __init__(self) -> None:
        super().__init__("authentication enrollment HTTP operation failed")


def _fail() -> None:
    raise AuthenticationEnrollmentHttpError() from None


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


def _encode_prefixed_base64url(
    value: object,
    *,
    prefix: str,
    max_bytes: int,
) -> str:
    if (
        type(value) is not bytes
        or not value
        or len(value) > max_bytes
        or type(prefix) is not str
        or not prefix
    ):
        _fail()
    payload = base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
    if not payload or any(char not in _BASE64URL for char in payload):
        _fail()
    return prefix + payload


def _encode_nonce(nonce: object) -> str:
    if type(nonce) is not bytes or len(nonce) != AUTH_ENROLLMENT_NONCE_BYTES:
        _fail()
    carrier = _encode_prefixed_base64url(
        nonce,
        prefix=AUTH_ENROLLMENT_NONCE_PREFIX,
        max_bytes=AUTH_ENROLLMENT_NONCE_BYTES,
    )
    payload = carrier[len(AUTH_ENROLLMENT_NONCE_PREFIX):]
    if len(payload) != AUTH_ENROLLMENT_NONCE_PAYLOAD_CHARS:
        _fail()
    return carrier


def _parse_nonce(value: object) -> bytes:
    if (
        type(value) is not str
        or not value.startswith(AUTH_ENROLLMENT_NONCE_PREFIX)
    ):
        raise ValueError("invalid enrollment nonce")
    payload = value[len(AUTH_ENROLLMENT_NONCE_PREFIX):]
    if (
        len(payload) != AUTH_ENROLLMENT_NONCE_PAYLOAD_CHARS
        or any(char not in _BASE64URL for char in payload)
    ):
        raise ValueError("invalid enrollment nonce")
    try:
        raw = base64.b64decode(
            payload.encode("ascii") + b"=",
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, ValueError, TypeError):
        raise ValueError("invalid enrollment nonce") from None
    if len(raw) != AUTH_ENROLLMENT_NONCE_BYTES:
        raise ValueError("invalid enrollment nonce")
    if _encode_nonce(raw) != value:
        raise ValueError("invalid enrollment nonce")
    return raw


def _proposal_from_document(value: object) -> MarketplaceAuthenticationEnrollmentProposal:
    if (
        type(value) is not dict
        or frozenset(value) != _PROPOSAL_KEYS
        or len(value) != len(_PROPOSAL_KEYS)
        or value.get("profile") != WEB_PROPOSAL_PROFILE
        or value.get("type") != WEB_PROPOSAL_TYPE
    ):
        raise ValueError("invalid enrollment proposal")
    if (
        type(value.get("principal")) is not str
        or type(value.get("verificationMethod")) is not str
        or type(value.get("publicKey")) is not str
    ):
        raise ValueError("invalid enrollment proposal")
    try:
        return MarketplaceAuthenticationEnrollmentProposal(
            principal=value["principal"],
            verification_method=value["verificationMethod"],
            public_key=value["publicKey"],
        )
    except AuthenticationEnrollmentAuthorityError:
        raise ValueError("invalid enrollment proposal") from None


def _request_document(
    request: ApplicationHttpRequest,
    *,
    expected_keys: frozenset[str],
) -> dict[str, object]:
    if request.query:
        raise ValueError("query forbidden")
    if request.content_type != "application/json":
        raise TypeError("application/json required")
    if not request.body or len(request.body) > AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES:
        raise ValueError("invalid enrollment request body")
    document = _decode_json_object_bytes(request.body)
    if (
        frozenset(document) != expected_keys
        or len(document) != len(expected_keys)
        or document.get("profile") != PROFILE_NAME
    ):
        raise ValueError("invalid enrollment request shape")
    return document


def _auth_required() -> ApplicationHttpResponse:
    return _error_response(
        401,
        "Unauthorized",
        "AUTH_REQUIRED",
        "application authentication is required",
    )


def _auth_invalid() -> ApplicationHttpResponse:
    return _error_response(
        401,
        "Unauthorized",
        "AUTH_SESSION_INVALID",
        "application session is invalid",
    )


def _principal_mismatch() -> ApplicationHttpResponse:
    return _error_response(
        403,
        "Forbidden",
        "AUTH_PRINCIPAL_MISMATCH",
        "authenticated session principal does not match the enrollment principal",
    )


def _request_invalid() -> ApplicationHttpResponse:
    return _error_response(
        400,
        "Bad Request",
        "AUTH_ENROLLMENT_REQUEST_INVALID",
        "authentication enrollment request is invalid",
    )


def _nonce_unavailable() -> ApplicationHttpResponse:
    return _error_response(
        503,
        "Service Unavailable",
        "AUTH_ENROLLMENT_NONCE_UNAVAILABLE",
        "authentication enrollment nonce is unavailable",
    )


def _enrollment_unavailable() -> ApplicationHttpResponse:
    return _error_response(
        409,
        "Conflict",
        "AUTH_ENROLLMENT_UNAVAILABLE",
        "authentication enrollment could not be completed",
    )


def _auth_error(exc: ApplicationAuthError) -> ApplicationHttpResponse:
    if exc.code == "AUTH_PRINCIPAL_MISMATCH":
        return _principal_mismatch()
    return _auth_invalid()


class MarketplaceAuthenticationEnrollmentHttpAdapter:
    """Two authenticated enrollment routes with trusted fixed authority/lease."""

    __slots__ = (
        "_auth",
        "_nonce_authority",
        "_policy",
        "_attestor",
        "_authority",
        "_lease_seconds",
    )

    def __init__(
        self,
        *,
        auth: MarketplaceApplicationAuthService,
        nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority,
        policy: AuthenticationEnrollmentApprovalPolicy,
        attestor: AuthenticationEnrollmentAuthorityAttestor,
        authority: str,
        evidence_lease_seconds: int,
    ) -> None:
        if type(auth) is not MarketplaceApplicationAuthService:
            _fail()
        if type(nonce_authority) is not MarketplaceAuthenticationEnrollmentNonceAuthority:
            _fail()
        try:
            approve = getattr(policy, "approve_authentication_enrollment", None)
            attest = getattr(attestor, "attest_authentication_enrollment", None)
        except Exception:
            _fail()
        if not callable(approve) or not callable(attest):
            _fail()
        _absolute_uri(authority)
        if (
            type(evidence_lease_seconds) is not int
            or evidence_lease_seconds <= 0
            or evidence_lease_seconds > AUTH_EVIDENCE_MAX_LEASE_SECONDS
        ):
            _fail()
        self._auth = auth
        self._nonce_authority = nonce_authority
        self._policy = policy
        self._attestor = attestor
        self._authority = authority
        self._lease_seconds = evidence_lease_seconds

    def handle(
        self,
        request: ApplicationHttpRequest,
        *,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if type(request) is not ApplicationHttpRequest:
            raise TypeError("request MUST be exact ApplicationHttpRequest")
        if request.path not in {
            AUTH_ENROLLMENT_NONCE_ROUTE,
            AUTH_ENROLLMENT_EVIDENCE_ROUTE,
        }:
            return _error_response(
                404,
                "Not Found",
                "NOT_FOUND",
                "resource not found",
            )
        if request.method != "POST":
            return _error_response(
                405,
                "Method Not Allowed",
                "METHOD_NOT_ALLOWED",
                "POST is required",
                allow="POST",
            )
        if type(session_invalid) is not bool:
            raise TypeError("session_invalid MUST be exact bool")
        if type(now) is not int or now < 0:
            raise ValueError("now MUST be a non-negative exact integer")
        if session_invalid:
            return _auth_invalid()
        if session_token is None:
            return _auth_required()
        if type(session_token) is not bytes or len(session_token) != AUTH_SESSION_TOKEN_BYTES:
            return _auth_invalid()

        try:
            session = self._auth.validate_session(
                session_token=session_token,
                now=now,
            )
        except ApplicationAuthError:
            return _auth_invalid()

        expected_keys = (
            _NONCE_REQUEST_KEYS
            if request.path == AUTH_ENROLLMENT_NONCE_ROUTE
            else _EVIDENCE_REQUEST_KEYS
        )
        try:
            document = _request_document(request, expected_keys=expected_keys)
            proposal = _proposal_from_document(document["proposal"])
            nonce = (
                None
                if request.path == AUTH_ENROLLMENT_NONCE_ROUTE
                else _parse_nonce(document["nonce"])
            )
        except TypeError:
            return _error_response(
                415,
                "Unsupported Media Type",
                "UNSUPPORTED_MEDIA_TYPE",
                "application/json is required",
            )
        except (ValueError, UnicodeError):
            return _request_invalid()

        if session.principal != proposal.principal:
            return _principal_mismatch()

        if request.path == AUTH_ENROLLMENT_NONCE_ROUTE:
            try:
                self._auth.authorize_principal(
                    session_token=session_token,
                    claimed_principal=proposal.principal,
                    now=now,
                )
            except ApplicationAuthError as exc:
                return _auth_error(exc)
            try:
                view = self._nonce_authority.issue_authentication_enrollment_nonce(
                    principal=proposal.principal,
                    verification_method=proposal.verification_method,
                    public_key=proposal.public_key,
                    authority=self._authority,
                    evidence_lease_seconds=self._lease_seconds,
                    now=now,
                )
                nonce_text = _encode_nonce(view.nonce)
            except (AuthenticationEnrollmentNonceError, AuthenticationEnrollmentHttpError):
                return _nonce_unavailable()
            return _json_response(
                201,
                "Created",
                {
                    "expiresAt": view.expires_at,
                    "issuedAt": view.issued_at,
                    "nonce": nonce_text,
                    "profile": PROFILE_NAME,
                    "type": NONCE_RESPONSE_TYPE,
                },
            )

        if nonce is None:
            return _request_invalid()
        try:
            envelope = coordinate_marketplace_authentication_enrollment(
                auth=self._auth,
                session_token=session_token,
                proposal=proposal,
                nonce=nonce,
                now=now,
                authority=self._authority,
                lease_seconds=self._lease_seconds,
                replay_guard=self._nonce_authority,
                policy=self._policy,
                attestor=self._attestor,
            )
        except AuthenticationEnrollmentCoordinationError:
            return _enrollment_unavailable()
        if type(envelope) is not MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
            return _enrollment_unavailable()
        try:
            claims = _encode_prefixed_base64url(
                envelope.claims_json,
                prefix=AUTH_ENROLLMENT_CLAIMS_PREFIX,
                max_bytes=AUTH_EVIDENCE_CLAIMS_MAX_BYTES,
            )
            attestation = _encode_prefixed_base64url(
                envelope.attestation,
                prefix=AUTH_ENROLLMENT_ATTESTATION_PREFIX,
                max_bytes=AUTH_EVIDENCE_ATTESTATION_MAX_BYTES,
            )
        except AuthenticationEnrollmentHttpError:
            return _enrollment_unavailable()
        return _json_response(
            201,
            "Created",
            {
                "attestation": attestation,
                "claims": claims,
                "profile": PROFILE_NAME,
                "type": EVIDENCE_RESPONSE_TYPE,
            },
        )


__all__ = [
    "AUTH_ENROLLMENT_ATTESTATION_PREFIX",
    "AUTH_ENROLLMENT_CLAIMS_PREFIX",
    "AUTH_ENROLLMENT_EVIDENCE_ROUTE",
    "AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES",
    "AUTH_ENROLLMENT_NONCE_PREFIX",
    "AUTH_ENROLLMENT_NONCE_ROUTE",
    "AuthenticationEnrollmentHttpError",
    "EVIDENCE_RESPONSE_TYPE",
    "MarketplaceAuthenticationEnrollmentHttpAdapter",
    "NONCE_RESPONSE_TYPE",
    "PROFILE_NAME",
    "WEB_PROPOSAL_PROFILE",
    "WEB_PROPOSAL_TYPE",
]
