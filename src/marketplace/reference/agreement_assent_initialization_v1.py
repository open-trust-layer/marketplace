"""Explicit one-shot initialization seam for reference Agreement-assent coordination."""
from __future__ import annotations

from typing import Final

from ..application.agreement_assent_coordination import AgreementAssentExpiryResult
from .agreement_assent_postgres_v1 import (
    MarketplaceReferenceAgreementAssentPostgres,
)


PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_COORDINATION_INITIALIZATION_V1"
INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION: Final = (
    "INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION"
)


class MarketplaceReferenceAgreementAssentInitializationError(RuntimeError):
    """Stable non-reflective Agreement coordination initialization failure."""

    def __init__(self) -> None:
        super().__init__("reference Agreement assent coordination initialization failed")


def _fail() -> None:
    raise MarketplaceReferenceAgreementAssentInitializationError() from None


def _validate_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token != INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION
    ):
        _fail()


def _validate_graph(graph: MarketplaceReferenceAgreementAssentPostgres) -> None:
    if type(graph) is not MarketplaceReferenceAgreementAssentPostgres:
        _fail()
    try:
        coordination = graph.launch.services.coordination
        if coordination._store is not graph.store:
            _fail()
        if coordination._initialized is not False:
            _fail()
    except MarketplaceReferenceAgreementAssentInitializationError:
        raise
    except Exception:
        _fail()


def initialize_reference_agreement_assent_coordination(
    *,
    graph: MarketplaceReferenceAgreementAssentPostgres,
    execute_token: str,
) -> AgreementAssentExpiryResult:
    """Initialize exactly one reviewed coordination graph after explicit authority."""

    _validate_token(execute_token)
    _validate_graph(graph)

    try:
        result = graph.launch.services.coordination.initialize()
    except Exception:
        _fail()

    if type(result) is not AgreementAssentExpiryResult:
        _fail()
    if graph.launch.services.coordination._initialized is not True:
        _fail()
    return result


__all__ = [
    "INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION",
    "MarketplaceReferenceAgreementAssentInitializationError",
    "PROFILE_NAME",
    "initialize_reference_agreement_assent_coordination",
]
