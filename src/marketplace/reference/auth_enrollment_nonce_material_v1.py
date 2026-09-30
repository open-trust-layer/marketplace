"""M17.6P unselected reference enrollment nonce-material source."""
from __future__ import annotations

from secrets import token_bytes as _token_bytes
from typing import Final

from ..application.auth_enrollment_coordination import AUTH_ENROLLMENT_NONCE_BYTES


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_MATERIAL_V1"
)
_ERROR_MESSAGE: Final = "reference authentication enrollment nonce material failed"


class MarketplaceReferenceAuthenticationEnrollmentNonceMaterialError(RuntimeError):
    """Stable CSPRNG adapter failure without entropy-detail reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentNonceMaterialError() from None


class MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource:
    """Stateless standard-library OS-CSPRNG source for exact enrollment nonces."""

    __slots__ = ()

    def enrollment_nonce_bytes(self) -> bytes:
        try:
            material = _token_bytes(AUTH_ENROLLMENT_NONCE_BYTES)
        except Exception:
            _fail()
        if (
            type(material) is not bytes
            or len(material) != AUTH_ENROLLMENT_NONCE_BYTES
        ):
            _fail()
        return material


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentNonceMaterialError",
    "MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource",
    "PROFILE_NAME",
]
