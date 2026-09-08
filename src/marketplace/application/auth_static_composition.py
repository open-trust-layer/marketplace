"""M17.5O static in-memory Marketplace authentication composition.

This module wires only already-reviewed caller-supplied authentication evidence
into one coherent process-local composition. It performs no provisioning,
credential generation, external I/O, persistence, or runtime selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth import MarketplaceApplicationAuthService
from .auth_evidence_trust_ed25519 import (
    MarketplaceAuthenticationEvidenceTrustAnchorSnapshot,
    MarketplaceEd25519AuthenticationEvidenceTrustVerifier,
)
from .auth_trust_anchor_manifest import (
    materialize_marketplace_authentication_evidence_trust_anchor_snapshot,
)
from .auth_verification_method_evidence import (
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    materialize_marketplace_authentication_verification_method_snapshot,
)
from .auth_verification_method_snapshot import (
    MarketplaceAuthenticationVerificationMethodSnapshot,
)
from .auth_verifier_ed25519 import MarketplaceEd25519AuthenticationProofVerifier


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_STATIC_COMPOSITION_V1"


class MarketplaceStaticAuthenticationCompositionError(ValueError):
    """Stable fail-closed composition error without authentication-data reflection."""

    def __init__(self) -> None:
        super().__init__("static Marketplace authentication composition failed")


def _fail() -> None:
    raise MarketplaceStaticAuthenticationCompositionError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceStaticAuthenticationComposition:
    """One immutable reference to a coherent in-memory authentication graph."""

    trust_anchor_snapshot: MarketplaceAuthenticationEvidenceTrustAnchorSnapshot
    verification_method_snapshot: MarketplaceAuthenticationVerificationMethodSnapshot
    proof_verifier: MarketplaceEd25519AuthenticationProofVerifier
    auth_service: MarketplaceApplicationAuthService

    def __post_init__(self) -> None:
        if (
            type(self.trust_anchor_snapshot)
            is not MarketplaceAuthenticationEvidenceTrustAnchorSnapshot
        ):
            _fail()
        if (
            type(self.verification_method_snapshot)
            is not MarketplaceAuthenticationVerificationMethodSnapshot
        ):
            _fail()
        if (
            type(self.proof_verifier)
            is not MarketplaceEd25519AuthenticationProofVerifier
        ):
            _fail()
        if type(self.auth_service) is not MarketplaceApplicationAuthService:
            _fail()


def compose_marketplace_static_authentication(
    *,
    trust_anchor_manifest: bytes,
    verification_method_evidence:
        MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    at_time: int,
) -> MarketplaceStaticAuthenticationComposition:
    """Compose exact N -> M -> L -> one K snapshot -> J + auth service wiring."""

    if type(trust_anchor_manifest) is not bytes:
        _fail()
    if (
        type(verification_method_evidence)
        is not MarketplaceAuthenticationVerificationMethodEvidenceEnvelope
    ):
        _fail()
    if type(at_time) is not int or at_time < 0:
        _fail()

    try:
        trust_anchor_snapshot = (
            materialize_marketplace_authentication_evidence_trust_anchor_snapshot(
                trust_anchor_manifest
            )
        )
        evidence_trust_verifier = MarketplaceEd25519AuthenticationEvidenceTrustVerifier(
            trust_anchors=trust_anchor_snapshot
        )
        verification_method_snapshot = (
            materialize_marketplace_authentication_verification_method_snapshot(
                envelope=verification_method_evidence,
                trust_verifier=evidence_trust_verifier,
                at_time=at_time,
            )
        )
        proof_verifier = MarketplaceEd25519AuthenticationProofVerifier(
            key_source=verification_method_snapshot
        )
        auth_service = MarketplaceApplicationAuthService(
            principal_binding_verifier=verification_method_snapshot
        )
        return MarketplaceStaticAuthenticationComposition(
            trust_anchor_snapshot=trust_anchor_snapshot,
            verification_method_snapshot=verification_method_snapshot,
            proof_verifier=proof_verifier,
            auth_service=auth_service,
        )
    except Exception:
        _fail()


__all__ = [
    "MarketplaceStaticAuthenticationComposition",
    "MarketplaceStaticAuthenticationCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_static_authentication",
]
