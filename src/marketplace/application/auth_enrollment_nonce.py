"""M17.6H in-memory atomic authentication enrollment nonce authority.

This module issues short-lived enrollment nonce material from one injected source,
retains only SHA-256 digests plus non-secret binding state, and implements the
M17.6G purpose-specific atomic replay-consumption contract. It selects no HTTP,
ASGI, persistence, network provider, database, signer, policy, or runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from threading import Lock
from typing import Final, Protocol

from .auth_enrollment_coordination import AUTH_ENROLLMENT_NONCE_BYTES
from .auth_verification_method_evidence import (
    AUTH_EVIDENCE_MAX_LEASE_SECONDS,
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    parse_marketplace_auth_verification_public_key,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_NONCE_V1"
AUTH_ENROLLMENT_NONCE_MAX_AGE_SECONDS: Final = 2 * 60
AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES: Final = 128
AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES_PER_BINDING: Final = 4


class AuthenticationEnrollmentNonceError(ValueError):
    """Stable fail-closed nonce-authority error without sensitive reflection."""

    def __init__(self) -> None:
        super().__init__("authentication enrollment nonce operation failed")


def _fail() -> None:
    raise AuthenticationEnrollmentNonceError() from None


class AuthenticationEnrollmentNonceMaterialSource(Protocol):
    """Purpose-specific source for exact raw enrollment nonce material."""

    def enrollment_nonce_bytes(self) -> bytes: ...


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEnrollmentNonceView:
    """Ephemeral issuance result; raw nonce material is returned only to the caller."""

    nonce: bytes
    issued_at: int
    expires_at: int

    def __post_init__(self) -> None:
        if type(self.nonce) is not bytes or len(self.nonce) != AUTH_ENROLLMENT_NONCE_BYTES:
            _fail()
        if type(self.issued_at) is not int or self.issued_at < 0:
            _fail()
        if type(self.expires_at) is not int or self.expires_at <= self.issued_at:
            _fail()
        if self.expires_at - self.issued_at != AUTH_ENROLLMENT_NONCE_MAX_AGE_SECONDS:
            _fail()


@dataclass(frozen=True, slots=True)
class _NonceState:
    digest: bytes
    principal: str
    verification_method: str
    public_key: str
    authority: str
    evidence_lease_seconds: int
    issued_at: int
    expires_at: int

    def binding(self) -> tuple[str, str, str, str, int]:
        return (
            self.principal,
            self.verification_method,
            self.public_key,
            self.authority,
            self.evidence_lease_seconds,
        )


def _review_issue_binding(
    *,
    principal: str,
    verification_method: str,
    public_key: str,
    authority: str,
    evidence_lease_seconds: int,
    now: int,
) -> tuple[str, str, str, str, int]:
    if type(now) is not int or now < 0:
        _fail()
    if (
        type(evidence_lease_seconds) is not int
        or evidence_lease_seconds <= 0
        or evidence_lease_seconds > AUTH_EVIDENCE_MAX_LEASE_SECONDS
    ):
        _fail()
    try:
        public_key_bytes = parse_marketplace_auth_verification_public_key(public_key)
        claim = AuthenticationVerificationMethodEvidenceClaim(
            verification_method=verification_method,
            controller_principal=principal,
            public_key=public_key_bytes,
        )
        MarketplaceAuthenticationVerificationMethodEvidenceClaims(
            authority=authority,
            issued_at=now,
            expires_at=now + evidence_lease_seconds,
            entries=(claim,),
        )
    except AuthenticationVerificationMethodEvidenceError:
        _fail()
    return (
        principal,
        verification_method,
        public_key,
        authority,
        evidence_lease_seconds,
    )


def _review_consumption(
    *,
    nonce: object,
    principal: object,
    verification_method: object,
    public_key: object,
    authority: object,
    issued_at: object,
    expires_at: object,
) -> tuple[bytes, tuple[str, str, str, str, int], int] | None:
    if type(nonce) is not bytes or len(nonce) != AUTH_ENROLLMENT_NONCE_BYTES:
        return None
    if type(issued_at) is not int or issued_at < 0:
        return None
    if type(expires_at) is not int or expires_at <= issued_at:
        return None
    lease_seconds = expires_at - issued_at
    if lease_seconds > AUTH_EVIDENCE_MAX_LEASE_SECONDS:
        return None
    if (
        type(principal) is not str
        or type(verification_method) is not str
        or type(public_key) is not str
        or type(authority) is not str
    ):
        return None
    try:
        public_key_bytes = parse_marketplace_auth_verification_public_key(public_key)
        claim = AuthenticationVerificationMethodEvidenceClaim(
            verification_method=verification_method,
            controller_principal=principal,
            public_key=public_key_bytes,
        )
        MarketplaceAuthenticationVerificationMethodEvidenceClaims(
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
            entries=(claim,),
        )
    except AuthenticationVerificationMethodEvidenceError:
        return None
    return (
        nonce,
        (
            principal,
            verification_method,
            public_key,
            authority,
            lease_seconds,
        ),
        issued_at,
    )


class MarketplaceAuthenticationEnrollmentNonceAuthority:
    """Bounded process-memory nonce authority with atomic one-use consumption."""

    __slots__ = ("_nonce_bytes", "_lock", "_outstanding", "_spent")

    def __init__(self, *, material_source: AuthenticationEnrollmentNonceMaterialSource) -> None:
        try:
            nonce_bytes = getattr(material_source, "enrollment_nonce_bytes", None)
        except Exception:
            _fail()
        if not callable(nonce_bytes):
            _fail()
        self._nonce_bytes = nonce_bytes
        self._lock = Lock()
        self._outstanding: dict[bytes, _NonceState] = {}
        self._spent: dict[bytes, _NonceState] = {}

    def _purge_locked(self, now: int) -> None:
        stale_outstanding = [
            digest
            for digest, state in self._outstanding.items()
            if now >= state.expires_at
        ]
        for digest in stale_outstanding:
            del self._outstanding[digest]
        stale_spent = [
            digest
            for digest, state in self._spent.items()
            if now >= state.expires_at
        ]
        for digest in stale_spent:
            del self._spent[digest]

    def _binding_count_locked(self, binding: tuple[str, str, str, str, int]) -> int:
        return sum(
            1
            for state in (*self._outstanding.values(), *self._spent.values())
            if state.binding() == binding
        )

    def issue_authentication_enrollment_nonce(
        self,
        *,
        principal: str,
        verification_method: str,
        public_key: str,
        authority: str,
        evidence_lease_seconds: int,
        now: int,
    ) -> MarketplaceAuthenticationEnrollmentNonceView:
        binding = _review_issue_binding(
            principal=principal,
            verification_method=verification_method,
            public_key=public_key,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            now=now,
        )
        try:
            nonce = self._nonce_bytes()
        except Exception:
            _fail()
        if type(nonce) is not bytes or len(nonce) != AUTH_ENROLLMENT_NONCE_BYTES:
            _fail()

        digest = hashlib.sha256(nonce).digest()
        state = _NonceState(
            digest=digest,
            principal=principal,
            verification_method=verification_method,
            public_key=public_key,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            issued_at=now,
            expires_at=now + AUTH_ENROLLMENT_NONCE_MAX_AGE_SECONDS,
        )

        with self._lock:
            self._purge_locked(now)
            if digest in self._outstanding or digest in self._spent:
                _fail()
            if (
                len(self._outstanding) + len(self._spent)
                >= AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES
            ):
                _fail()
            if (
                self._binding_count_locked(binding)
                >= AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES_PER_BINDING
            ):
                _fail()
            self._outstanding[digest] = state

        return MarketplaceAuthenticationEnrollmentNonceView(
            nonce=nonce,
            issued_at=state.issued_at,
            expires_at=state.expires_at,
        )

    def consume_authentication_enrollment_nonce(
        self,
        *,
        nonce: bytes,
        principal: str,
        verification_method: str,
        public_key: str,
        authority: str,
        issued_at: int,
        expires_at: int,
    ) -> bool:
        reviewed = _review_consumption(
            nonce=nonce,
            principal=principal,
            verification_method=verification_method,
            public_key=public_key,
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        if reviewed is None:
            return False
        reviewed_nonce, binding, reviewed_issued_at = reviewed
        digest = hashlib.sha256(reviewed_nonce).digest()

        with self._lock:
            self._purge_locked(reviewed_issued_at)
            state = self._outstanding.pop(digest, None)
            if state is None:
                return False
            self._spent[digest] = state

        if state.binding() != binding:
            return False
        if not state.issued_at <= reviewed_issued_at < state.expires_at:
            return False
        return True


__all__ = [
    "AUTH_ENROLLMENT_NONCE_MAX_AGE_SECONDS",
    "AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES",
    "AUTH_MAX_OUTSTANDING_ENROLLMENT_NONCES_PER_BINDING",
    "AuthenticationEnrollmentNonceError",
    "AuthenticationEnrollmentNonceMaterialSource",
    "MarketplaceAuthenticationEnrollmentNonceAuthority",
    "MarketplaceAuthenticationEnrollmentNonceView",
    "PROFILE_NAME",
]
