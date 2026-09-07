"""Transport-neutral M17.5B application authentication/session contracts.

This module owns no credential generator, cryptographic key material, HTTP carrier,
provider, resolver, database, filesystem, or runtime authority. Raw challenges and
session tokens are caller-supplied bounded values; only SHA-256 digests are retained.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Protocol

from .authoring import ProductListingAuthoringFields
from .proposal import BuyerRequestProposalDraft


AUTH_CHALLENGE_BYTES = 32
AUTH_SESSION_TOKEN_BYTES = 32
AUTH_CHALLENGE_MAX_AGE_SECONDS = 2 * 60
AUTH_SESSION_IDLE_SECONDS = 30 * 60
AUTH_SESSION_ABSOLUTE_SECONDS = 8 * 60 * 60
AUTH_MAX_OUTSTANDING_CHALLENGES = 128
AUTH_MAX_OUTSTANDING_CHALLENGES_PER_BINDING = 4
AUTH_MAX_ACTIVE_SESSIONS = 256
AUTH_MAX_ACTIVE_SESSIONS_PER_PRINCIPAL = 8
AUTH_PROOF_DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1"
AUTH_PROOF_PURPOSE = "assertion"
_AUTH_URI_MAX_BYTES = 2048
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


class ApplicationAuthError(RuntimeError):
    """Stable fail-closed application-auth failure without credential reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ApplicationAuthError(code, message) from None


def _exact_time(value: object, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} MUST be a non-negative exact integer")
    return value


def _absolute_uri(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} MUST be non-empty exact text")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} MUST be valid UTF-8 text") from exc
    if len(encoded) > _AUTH_URI_MAX_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError(f"{name} MUST be a bounded absolute URI")
    return value


def _fixed_bytes(value: object, *, name: str, size: int) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise ValueError(f"{name} MUST be exact {size}-byte material")
    return value


def _digest(value: bytes) -> bytes:
    return hashlib.sha256(value).digest()


class PrincipalBindingVerifier(Protocol):
    """Injected policy/evidence decision; there is deliberately no permissive default."""

    def verify(
        self,
        *,
        principal: str,
        verification_method: str,
        at_time: int,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class VerifiedAuthenticationProof:
    """Already-verified proof facts accepted from a separately reviewed verifier."""

    challenge_sha256: bytes
    domain: str
    proof_purpose: str
    verification_method: str
    cryptographically_valid: bool

    def __post_init__(self) -> None:
        _fixed_bytes(self.challenge_sha256, name="challenge_sha256", size=32)
        if type(self.domain) is not str or not self.domain:
            raise ValueError("domain MUST be non-empty exact text")
        if type(self.proof_purpose) is not str or not self.proof_purpose:
            raise ValueError("proof_purpose MUST be non-empty exact text")
        _absolute_uri(self.verification_method, name="verification_method")
        if type(self.cryptographically_valid) is not bool:
            raise TypeError("cryptographically_valid MUST be exact bool")


@dataclass(frozen=True, slots=True)
class ApplicationSessionView:
    """Non-secret session facts; raw token and token digest are intentionally absent."""

    principal: str
    verification_method: str
    issued_at: int
    last_used_at: int
    absolute_expires_at: int

    def __post_init__(self) -> None:
        _absolute_uri(self.principal, name="principal")
        _absolute_uri(self.verification_method, name="verification_method")
        issued = _exact_time(self.issued_at, name="issued_at")
        last_used = _exact_time(self.last_used_at, name="last_used_at")
        expires = _exact_time(self.absolute_expires_at, name="absolute_expires_at")
        if last_used < issued or expires <= issued:
            raise ValueError("session timestamps are not canonical")
        if expires - issued > AUTH_SESSION_ABSOLUTE_SECONDS:
            raise ValueError("session absolute lifetime exceeds the reviewed ceiling")


@dataclass(frozen=True, slots=True)
class ApplicationChallengeAttempt:
    """Non-secret one-use challenge facts after atomic consumption."""

    challenge_sha256: bytes
    principal: str
    verification_method: str
    issued_at: int
    expires_at: int

    def __post_init__(self) -> None:
        _fixed_bytes(self.challenge_sha256, name="challenge_sha256", size=32)
        _absolute_uri(self.principal, name="principal")
        _absolute_uri(self.verification_method, name="verification_method")
        issued = _exact_time(self.issued_at, name="issued_at")
        expires = _exact_time(self.expires_at, name="expires_at")
        if expires <= issued or expires - issued > AUTH_CHALLENGE_MAX_AGE_SECONDS:
            raise ValueError("challenge attempt timestamps are not canonical")


@dataclass(slots=True)
class _ChallengeState:
    digest: bytes
    principal: str
    verification_method: str
    issued_at: int
    expires_at: int
    consumed: bool = False


@dataclass(slots=True)
class _SessionState:
    token_digest: bytes
    principal: str
    verification_method: str
    issued_at: int
    last_used_at: int
    absolute_expires_at: int

    def view(self) -> ApplicationSessionView:
        return ApplicationSessionView(
            principal=self.principal,
            verification_method=self.verification_method,
            issued_at=self.issued_at,
            last_used_at=self.last_used_at,
            absolute_expires_at=self.absolute_expires_at,
        )


class MarketplaceApplicationAuthService:
    """Process-memory auth/session state with injected principal-binding policy."""

    def __init__(self, *, principal_binding_verifier: PrincipalBindingVerifier) -> None:
        verify = getattr(principal_binding_verifier, "verify", None)
        if not callable(verify):
            raise TypeError("principal_binding_verifier MUST provide callable verify")
        self._verify_principal_binding = verify
        self._challenges: dict[bytes, _ChallengeState] = {}
        self._sessions: dict[bytes, _SessionState] = {}

    def _purge_challenges(self, now: int) -> None:
        stale = [digest for digest, state in self._challenges.items() if now >= state.expires_at]
        for digest in stale:
            del self._challenges[digest]

    def _purge_sessions(self, now: int) -> None:
        stale = [
            digest
            for digest, state in self._sessions.items()
            if now >= state.absolute_expires_at
            or (now >= state.last_used_at and now - state.last_used_at >= AUTH_SESSION_IDLE_SECONDS)
        ]
        for digest in stale:
            del self._sessions[digest]

    def register_challenge(
        self,
        *,
        challenge: bytes,
        principal: str,
        verification_method: str,
        now: int,
    ) -> None:
        raw = _fixed_bytes(challenge, name="challenge", size=AUTH_CHALLENGE_BYTES)
        reviewed_principal = _absolute_uri(principal, name="principal")
        reviewed_method = _absolute_uri(verification_method, name="verification_method")
        reviewed_now = _exact_time(now, name="now")
        self._purge_challenges(reviewed_now)
        self._purge_sessions(reviewed_now)
        digest = _digest(raw)
        if digest in self._challenges:
            _fail("AUTH_CHALLENGE_REUSED", "authentication challenge was already registered")
        pair_count = sum(
            1
            for state in self._challenges.values()
            if state.principal == reviewed_principal and state.verification_method == reviewed_method
        )
        if (
            len(self._challenges) >= AUTH_MAX_OUTSTANDING_CHALLENGES
            or pair_count >= AUTH_MAX_OUTSTANDING_CHALLENGES_PER_BINDING
        ):
            _fail("AUTH_CAPACITY_EXCEEDED", "authentication challenge capacity is exhausted")
        self._challenges[digest] = _ChallengeState(
            digest=digest,
            principal=reviewed_principal,
            verification_method=reviewed_method,
            issued_at=reviewed_now,
            expires_at=reviewed_now + AUTH_CHALLENGE_MAX_AGE_SECONDS,
        )

    def begin_challenge_attempt(
        self,
        *,
        challenge: bytes,
        now: int,
    ) -> ApplicationChallengeAttempt:
        raw = _fixed_bytes(challenge, name="challenge", size=AUTH_CHALLENGE_BYTES)
        reviewed_now = _exact_time(now, name="now")
        digest = _digest(raw)
        state = self._challenges.get(digest)
        if state is None:
            _fail("AUTH_CHALLENGE_INVALID", "authentication challenge is unavailable")
        if reviewed_now < state.issued_at:
            del self._challenges[digest]
            _fail("AUTH_TIME_INVALID", "authentication clock moved before challenge issuance")
        if reviewed_now >= state.expires_at:
            del self._challenges[digest]
            _fail("AUTH_CHALLENGE_EXPIRED", "authentication challenge expired")
        del self._challenges[digest]
        return ApplicationChallengeAttempt(
            challenge_sha256=digest,
            principal=state.principal,
            verification_method=state.verification_method,
            issued_at=state.issued_at,
            expires_at=state.expires_at,
        )

    def authenticate_challenge_attempt(
        self,
        *,
        attempt: ApplicationChallengeAttempt,
        proof: VerifiedAuthenticationProof,
        session_token: bytes,
        now: int,
    ) -> ApplicationSessionView:
        if type(attempt) is not ApplicationChallengeAttempt:
            raise TypeError("attempt MUST be exact ApplicationChallengeAttempt")
        if type(proof) is not VerifiedAuthenticationProof:
            raise TypeError("proof MUST be exact VerifiedAuthenticationProof")
        raw_token = _fixed_bytes(session_token, name="session_token", size=AUTH_SESSION_TOKEN_BYTES)
        reviewed_now = _exact_time(now, name="now")
        if reviewed_now < attempt.issued_at or reviewed_now >= attempt.expires_at:
            _fail("AUTH_CHALLENGE_INVALID", "authentication challenge is unavailable")
        if (
            not proof.cryptographically_valid
            or proof.challenge_sha256 != attempt.challenge_sha256
            or proof.domain != AUTH_PROOF_DOMAIN
            or proof.proof_purpose != AUTH_PROOF_PURPOSE
            or proof.verification_method != attempt.verification_method
        ):
            _fail("AUTH_PROOF_INVALID", "authentication proof facts do not match the challenge")
        try:
            binding = self._verify_principal_binding(
                principal=attempt.principal,
                verification_method=attempt.verification_method,
                at_time=reviewed_now,
            )
        except Exception:
            _fail("AUTH_PRINCIPAL_BINDING_UNAVAILABLE", "principal-binding verification did not complete")
        if type(binding) is not bool:
            _fail("AUTH_PRINCIPAL_BINDING_UNAVAILABLE", "principal-binding verification did not return a decision")
        if not binding:
            _fail("AUTH_PRINCIPAL_BINDING_REJECTED", "principal-binding evidence was not sufficient under application policy")
        self._purge_sessions(reviewed_now)
        token_digest = _digest(raw_token)
        if token_digest in self._sessions:
            _fail("AUTH_SESSION_TOKEN_REUSED", "session token was already registered")
        principal_count = sum(1 for state in self._sessions.values() if state.principal == attempt.principal)
        if (
            len(self._sessions) >= AUTH_MAX_ACTIVE_SESSIONS
            or principal_count >= AUTH_MAX_ACTIVE_SESSIONS_PER_PRINCIPAL
        ):
            _fail("AUTH_CAPACITY_EXCEEDED", "application session capacity is exhausted")
        session = _SessionState(
            token_digest=token_digest,
            principal=attempt.principal,
            verification_method=attempt.verification_method,
            issued_at=reviewed_now,
            last_used_at=reviewed_now,
            absolute_expires_at=reviewed_now + AUTH_SESSION_ABSOLUTE_SECONDS,
        )
        self._sessions[token_digest] = session
        return session.view()

    def authenticate_challenge(
        self,
        *,
        challenge: bytes,
        proof: VerifiedAuthenticationProof,
        session_token: bytes,
        now: int,
    ) -> ApplicationSessionView:
        attempt = self.begin_challenge_attempt(challenge=challenge, now=now)
        return self.authenticate_challenge_attempt(
            attempt=attempt,
            proof=proof,
            session_token=session_token,
            now=now,
        )

    def _review_session(
        self,
        *,
        session_token: bytes,
        now: int,
        touch: bool,
    ) -> _SessionState:
        raw_token = _fixed_bytes(
            session_token,
            name="session_token",
            size=AUTH_SESSION_TOKEN_BYTES,
        )
        reviewed_now = _exact_time(now, name="now")
        token_digest = _digest(raw_token)
        state = self._sessions.get(token_digest)
        if state is None:
            _fail("AUTH_SESSION_INVALID", "application session is unavailable")
        if reviewed_now < state.issued_at or reviewed_now < state.last_used_at:
            _fail("AUTH_TIME_INVALID", "application session clock moved backwards")
        if (
            reviewed_now >= state.absolute_expires_at
            or reviewed_now - state.last_used_at >= AUTH_SESSION_IDLE_SECONDS
        ):
            del self._sessions[token_digest]
            _fail("AUTH_SESSION_EXPIRED", "application session expired")
        if touch:
            state.last_used_at = reviewed_now
        return state

    def authenticate_session(
        self,
        *,
        session_token: bytes,
        now: int,
    ) -> ApplicationSessionView:
        return self._review_session(
            session_token=session_token,
            now=now,
            touch=True,
        ).view()

    def validate_session(
        self,
        *,
        session_token: bytes,
        now: int,
    ) -> ApplicationSessionView:
        """Validate one active session without extending its idle lifetime."""
        return self._review_session(
            session_token=session_token,
            now=now,
            touch=False,
        ).view()

    def authorize_principal(
        self,
        *,
        session_token: bytes,
        claimed_principal: str,
        now: int,
    ) -> ApplicationSessionView:
        reviewed_principal = _absolute_uri(claimed_principal, name="claimed_principal")
        state = self._review_session(
            session_token=session_token,
            now=now,
            touch=False,
        )
        if reviewed_principal != state.principal:
            _fail(
                "AUTH_PRINCIPAL_MISMATCH",
                "authenticated session principal does not match the write issuer",
            )
        state.last_used_at = _exact_time(now, name="now")
        return state.view()

    def revoke_session(self, *, session_token: bytes, now: int) -> None:
        state = self._review_session(
            session_token=session_token,
            now=now,
            touch=False,
        )
        del self._sessions[state.token_digest]


class AuthenticatedProductListingAuthoringService:
    """Source-only guard: session principal must equal seller before downstream write."""

    def __init__(self, *, auth: MarketplaceApplicationAuthService, authoring: object) -> None:
        if type(auth) is not MarketplaceApplicationAuthService:
            raise TypeError("auth MUST be exact MarketplaceApplicationAuthService")
        create = getattr(authoring, "create_product_listing", None)
        if not callable(create):
            raise TypeError("authoring MUST provide callable create_product_listing")
        self._auth = auth
        self._create_product_listing = create

    def create_product_listing(
        self,
        *,
        session_token: bytes,
        fields: ProductListingAuthoringFields,
        now: int,
    ) -> Any:
        if type(fields) is not ProductListingAuthoringFields:
            raise TypeError("fields MUST be exact ProductListingAuthoringFields")
        self._auth.authorize_principal(
            session_token=session_token,
            claimed_principal=fields.seller_principal,
            now=now,
        )
        return self._create_product_listing(fields)


class AuthenticatedProposalAuthoringService:
    """Source-only guard: session principal must equal buyer before downstream write."""

    def __init__(self, *, auth: MarketplaceApplicationAuthService, authoring: object) -> None:
        if type(auth) is not MarketplaceApplicationAuthService:
            raise TypeError("auth MUST be exact MarketplaceApplicationAuthService")
        create = getattr(authoring, "create_buyer_request_proposal", None)
        if not callable(create):
            raise TypeError("authoring MUST provide callable create_buyer_request_proposal")
        self._auth = auth
        self._create_buyer_request_proposal = create

    def create_buyer_request_proposal(
        self,
        *,
        session_token: bytes,
        draft: BuyerRequestProposalDraft,
        now: int,
    ) -> Any:
        if type(draft) is not BuyerRequestProposalDraft:
            raise TypeError("draft MUST be exact BuyerRequestProposalDraft")
        self._auth.authorize_principal(
            session_token=session_token,
            claimed_principal=draft.buyer_principal,
            now=now,
        )
        return self._create_buyer_request_proposal(draft)


__all__ = [
    "AUTH_CHALLENGE_BYTES",
    "AUTH_CHALLENGE_MAX_AGE_SECONDS",
    "AUTH_MAX_ACTIVE_SESSIONS",
    "AUTH_MAX_ACTIVE_SESSIONS_PER_PRINCIPAL",
    "AUTH_MAX_OUTSTANDING_CHALLENGES",
    "AUTH_MAX_OUTSTANDING_CHALLENGES_PER_BINDING",
    "AUTH_PROOF_DOMAIN",
    "AUTH_PROOF_PURPOSE",
    "AUTH_SESSION_ABSOLUTE_SECONDS",
    "AUTH_SESSION_IDLE_SECONDS",
    "AUTH_SESSION_TOKEN_BYTES",
    "ApplicationAuthError",
    "ApplicationChallengeAttempt",
    "ApplicationSessionView",
    "AuthenticatedProductListingAuthoringService",
    "AuthenticatedProposalAuthoringService",
    "MarketplaceApplicationAuthService",
    "PrincipalBindingVerifier",
    "VerifiedAuthenticationProof",
]
