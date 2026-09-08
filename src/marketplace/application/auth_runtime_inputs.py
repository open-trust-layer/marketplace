"""M17.5Q reviewed authentication runtime inputs without activation.

This module selects only the existing OS-CSPRNG credential-material source and
one standard-library whole-Unix-seconds wall clock. Composition reads neither.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import time_ns as _time_ns
from typing import Final

from .auth_material import MarketplaceCredentialMaterialSource


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_RUNTIME_INPUTS_V1"
_ERROR_MESSAGE: Final = "authentication runtime input is invalid or unavailable"
_NANOSECONDS_PER_SECOND: Final = 1_000_000_000


class MarketplaceAuthenticationRuntimeInputError(RuntimeError):
    """Stable fail-closed runtime-input error without provider reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticationRuntimeInputError() from None


class MarketplaceAuthenticationUnixClock:
    """Stateless standard-library wall clock returning whole Unix seconds."""

    __slots__ = ()

    def now(self) -> int:
        """Read the reviewed local wall clock once and return whole seconds."""

        try:
            nanoseconds = _time_ns()
            if type(nanoseconds) is not int or nanoseconds < 0:
                _fail()
            seconds = nanoseconds // _NANOSECONDS_PER_SECOND
            if type(seconds) is not int or seconds < 0:
                _fail()
            return seconds
        except MarketplaceAuthenticationRuntimeInputError:
            raise
        except Exception:
            _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationRuntimeInputs:
    """Immutable references to the reviewed local authentication inputs."""

    material_source: MarketplaceCredentialMaterialSource
    clock: MarketplaceAuthenticationUnixClock

    def __post_init__(self) -> None:
        if type(self.material_source) is not MarketplaceCredentialMaterialSource:
            _fail()
        if type(self.clock) is not MarketplaceAuthenticationUnixClock:
            _fail()


def compose_marketplace_authentication_runtime_inputs(
) -> MarketplaceAuthenticationRuntimeInputs:
    """Compose reviewed local auth inputs without consuming either source."""

    try:
        material_source = MarketplaceCredentialMaterialSource()
        clock = MarketplaceAuthenticationUnixClock()
        return MarketplaceAuthenticationRuntimeInputs(
            material_source=material_source,
            clock=clock,
        )
    except MarketplaceAuthenticationRuntimeInputError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticationRuntimeInputError",
    "MarketplaceAuthenticationRuntimeInputs",
    "MarketplaceAuthenticationUnixClock",
    "PROFILE_NAME",
    "compose_marketplace_authentication_runtime_inputs",
]
