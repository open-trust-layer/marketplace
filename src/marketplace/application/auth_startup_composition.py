"""M17.5T one-shot authenticated startup composition without launch selection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_asgi_composition import (
    MarketplaceAuthenticatedAsgiComposition,
    compose_marketplace_authenticated_asgi,
)
from .auth_http import RecordJsonDecoder, RecordPrincipalExtractor
from .auth_http_composition import (
    MarketplaceAuthenticatedHttpComposition,
    compose_marketplace_authenticated_http,
)
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_startup_provisioning import MarketplaceAuthenticationStartupProvisioning
from .auth_static_composition import (
    MarketplaceStaticAuthenticationComposition,
    compose_marketplace_static_authentication,
)
from .composition import MarketplaceApplicationComposition


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_STARTUP_COMPOSITION_V1"
_ERROR_MESSAGE: Final = "authenticated Marketplace startup composition failed"


class MarketplaceAuthenticatedStartupCompositionError(ValueError):
    """Stable fail-closed startup-composition error without data reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticatedStartupCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticatedStartupComposition:
    """Immutable coherent references to the reviewed O -> P -> R graph."""

    authentication: MarketplaceStaticAuthenticationComposition
    http: MarketplaceAuthenticatedHttpComposition
    asgi: MarketplaceAuthenticatedAsgiComposition

    def __post_init__(self) -> None:
        if type(self.authentication) is not MarketplaceStaticAuthenticationComposition:
            _fail()
        if type(self.http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if type(self.asgi) is not MarketplaceAuthenticatedAsgiComposition:
            _fail()
        if self.http.authentication is not self.authentication:
            _fail()
        if self.asgi.http is not self.http:
            _fail()


def compose_marketplace_authenticated_startup(
    *,
    application: MarketplaceApplicationComposition,
    provisioning: MarketplaceAuthenticationStartupProvisioning,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
    decode_record_json: RecordJsonDecoder,
    record_principal: RecordPrincipalExtractor,
) -> MarketplaceAuthenticatedStartupComposition:
    """Consume one reviewed clock sample and compose exact O -> P -> R once."""

    if type(application) is not MarketplaceApplicationComposition:
        _fail()
    if type(provisioning) is not MarketplaceAuthenticationStartupProvisioning:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()
    if not callable(decode_record_json) or not callable(record_principal):
        _fail()

    try:
        at_time = runtime_inputs.clock.now()
        if type(at_time) is not int or at_time < 0:
            _fail()
        authentication = compose_marketplace_static_authentication(
            trust_anchor_manifest=provisioning.trust_anchor_manifest,
            verification_method_evidence=provisioning.verification_method_evidence,
            at_time=at_time,
        )
        http = compose_marketplace_authenticated_http(
            application=application,
            authentication=authentication,
            material_source=runtime_inputs.material_source,
            decode_record_json=decode_record_json,
            record_principal=record_principal,
        )
        asgi = compose_marketplace_authenticated_asgi(
            http=http,
            runtime_inputs=runtime_inputs,
        )
        return MarketplaceAuthenticatedStartupComposition(
            authentication=authentication,
            http=http,
            asgi=asgi,
        )
    except MarketplaceAuthenticatedStartupCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticatedStartupComposition",
    "MarketplaceAuthenticatedStartupCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_authenticated_startup",
]