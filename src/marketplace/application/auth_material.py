"""M17.5G unselected OS-CSPRNG credential-material source."""
from __future__ import annotations

from secrets import token_bytes as _token_bytes
from typing import Final

from .auth import AUTH_CHALLENGE_BYTES, AUTH_SESSION_TOKEN_BYTES


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_CREDENTIAL_MATERIAL_SOURCE_V1"


class MarketplaceCredentialMaterialSourceError(RuntimeError):
    """Stable local failure for malformed credential material without reflection."""


class MarketplaceCredentialMaterialSource:
    """Stateless standard-library OS-CSPRNG adapter for exact auth material."""

    __slots__ = ()

    @staticmethod
    def _fresh_material(size: int) -> bytes:
        material = _token_bytes(size)
        if type(material) is not bytes or len(material) != size:
            raise MarketplaceCredentialMaterialSourceError(
                "credential material source returned invalid material"
            )
        return material

    def challenge_bytes(self) -> bytes:
        return self._fresh_material(AUTH_CHALLENGE_BYTES)

    def session_token_bytes(self) -> bytes:
        return self._fresh_material(AUTH_SESSION_TOKEN_BYTES)


__all__ = [
    "MarketplaceCredentialMaterialSource",
    "MarketplaceCredentialMaterialSourceError",
    "PROFILE_NAME",
]
