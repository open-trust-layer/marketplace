"""M17.6Q unselected reference enrollment nonce-authority composition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from .auth_enrollment_nonce_material_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_AUTHORITY_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment nonce authority composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError(RuntimeError):
    """Stable fail-closed reference nonce-authority composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError() from None


def _bound_owner(value: object) -> object | None:
    try:
        if not callable(value):
            return None
        return getattr(value, "__self__", None)
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentNonceAuthority:
    """Exact inert P-to-H graph with no nonce material consumed at construction."""

    material_source: MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource
    nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority

    def __post_init__(self) -> None:
        if (
            type(self.material_source)
            is not MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource
        ):
            _fail()
        if (
            type(self.nonce_authority)
            is not MarketplaceAuthenticationEnrollmentNonceAuthority
        ):
            _fail()

        try:
            if _bound_owner(self.nonce_authority._nonce_bytes) is not self.material_source:
                _fail()
            if type(self.nonce_authority._outstanding) is not dict:
                _fail()
            if type(self.nonce_authority._spent) is not dict:
                _fail()
            if self.nonce_authority._outstanding != {}:
                _fail()
            if self.nonce_authority._spent != {}:
                _fail()
        except MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError:
            raise
        except Exception:
            _fail()


def build_reference_authentication_enrollment_nonce_authority(
) -> MarketplaceReferenceAuthenticationEnrollmentNonceAuthority:
    """Construct exactly one unselected P source and one H nonce authority."""

    try:
        material_source = (
            MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource()
        )
        nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=material_source,
        )
        return MarketplaceReferenceAuthenticationEnrollmentNonceAuthority(
            material_source=material_source,
            nonce_authority=nonce_authority,
        )
    except MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentNonceAuthority",
    "MarketplaceReferenceAuthenticationEnrollmentNonceAuthorityError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_nonce_authority",
]
