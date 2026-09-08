"""M17.5K immutable authentication verification-method evidence snapshot.

The snapshot is constructor-injected, process-local, public-key-only evidence.
It performs no resolution, refresh, persistence, cryptography, or runtime selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Final, Mapping, Sequence


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_SNAPSHOT_V1"
AUTH_VERIFICATION_METHOD_MAX_ENTRIES: Final = 256
AUTH_VERIFICATION_METHOD_URI_MAX_BYTES: Final = 2048
AUTH_VERIFICATION_PUBLIC_KEY_BYTES: Final = 32
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


class AuthenticationVerificationMethodSnapshotError(ValueError):
    """Stable fail-closed snapshot error without identifier/key reflection."""

    def __init__(self) -> None:
        super().__init__("authentication verification-method evidence is unavailable")


def _fail() -> None:
    raise AuthenticationVerificationMethodSnapshotError() from None


def _absolute_uri(value: object) -> str:
    if type(value) is not str or not value:
        _fail()
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        _fail()
    if len(encoded) > AUTH_VERIFICATION_METHOD_URI_MAX_BYTES or _URI_RE.fullmatch(value) is None:
        _fail()
    return value


def _optional_time(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        _fail()
    return value


def _time(value: object) -> int:
    if type(value) is not int or value < 0:
        _fail()
    return value


@dataclass(frozen=True, slots=True)
class AuthenticationVerificationMethodEvidence:
    """One exact public verification-method/control statement for local policy."""

    verification_method: str
    controller_principal: str
    public_key: bytes
    valid_from: int | None = None
    valid_until: int | None = None

    def __post_init__(self) -> None:
        _absolute_uri(self.verification_method)
        _absolute_uri(self.controller_principal)
        if type(self.public_key) is not bytes or len(self.public_key) != AUTH_VERIFICATION_PUBLIC_KEY_BYTES:
            _fail()
        start = _optional_time(self.valid_from)
        end = _optional_time(self.valid_until)
        if start is not None and end is not None and start >= end:
            _fail()


@dataclass(frozen=True, slots=True, init=False)
class MarketplaceAuthenticationVerificationMethodSnapshot:
    """Immutable shared key-source and principal-binding evidence snapshot."""

    _entries: Mapping[str, AuthenticationVerificationMethodEvidence]

    def __init__(
        self,
        entries: Sequence[AuthenticationVerificationMethodEvidence],
    ) -> None:
        if type(entries) not in (list, tuple):
            _fail()
        if len(entries) > AUTH_VERIFICATION_METHOD_MAX_ENTRIES:
            _fail()

        copied: dict[str, AuthenticationVerificationMethodEvidence] = {}
        for entry in entries:
            if type(entry) is not AuthenticationVerificationMethodEvidence:
                _fail()
            method = entry.verification_method
            if method in copied:
                _fail()
            copied[method] = entry
        object.__setattr__(self, "_entries", MappingProxyType(copied))

    def verification_key_bytes(self, verification_method: str) -> bytes:
        """Return the exact frozen public key for one exact method identifier."""

        method = _absolute_uri(verification_method)
        entry = self._entries.get(method)
        if type(entry) is not AuthenticationVerificationMethodEvidence:
            _fail()
        if type(entry.public_key) is not bytes or len(entry.public_key) != AUTH_VERIFICATION_PUBLIC_KEY_BYTES:
            _fail()
        return entry.public_key

    def verify(
        self,
        *,
        principal: str,
        verification_method: str,
        at_time: int,
    ) -> bool:
        """Decide exact principal/method binding from this same frozen evidence set."""

        reviewed_principal = _absolute_uri(principal)
        method = _absolute_uri(verification_method)
        reviewed_time = _time(at_time)
        entry = self._entries.get(method)
        if type(entry) is not AuthenticationVerificationMethodEvidence:
            _fail()
        if entry.controller_principal != reviewed_principal:
            return False
        if entry.valid_from is not None and reviewed_time < entry.valid_from:
            return False
        if entry.valid_until is not None and reviewed_time >= entry.valid_until:
            return False
        return True


__all__ = [
    "AUTH_VERIFICATION_METHOD_MAX_ENTRIES",
    "AUTH_VERIFICATION_METHOD_URI_MAX_BYTES",
    "AUTH_VERIFICATION_PUBLIC_KEY_BYTES",
    "AuthenticationVerificationMethodEvidence",
    "AuthenticationVerificationMethodSnapshotError",
    "MarketplaceAuthenticationVerificationMethodSnapshot",
    "PROFILE_NAME",
]
