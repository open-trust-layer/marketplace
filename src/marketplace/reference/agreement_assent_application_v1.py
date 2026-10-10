"""Inert reference Agreement-assent service graph over reviewed Marketplace state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.agreement_assent import MarketplaceAgreementAssentProofService
from ..application.agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from ..application.agreement_assent_coordination import (
    AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS,
    MAX_AGREEMENT_ASSENT_RETENTION_SECONDS,
    AgreementAssentCoordinationStore,
    MarketplaceAgreementAssentCoordinationService,
)
from ..application.agreement_assent_formation import (
    MarketplaceAgreementAssentFormationService,
)
from ..application.agreement_assent_workflow import (
    MarketplaceAgreementAssentWorkflowService,
)
from ..application.agreement_candidate import (
    MarketplaceAgreementCandidateAuthoringService,
)
from ..application.agreement_formation import (
    MarketplaceAgreementFormationEvaluationService,
)
from ..application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
)
from ..application.composition import MarketplaceApplicationComposition
from .agreement_assent_coordination_v1 import (
    build_prepared_product_agreement_assent,
)
from .agreement_assent_formation_v1 import (
    build_product_agreement_formation_evidence_from_verified_assent,
    reverify_prepared_product_agreement_assent,
)
from .agreement_assent_v1 import (
    build_product_agreement_assent_signing_input,
    build_verified_product_agreement_assent_proof,
)
from .agreement_candidate_v1 import (
    agreement_candidate_record_id,
    build_product_agreement_candidate,
)
from .agreement_formation_v1 import evaluate_product_agreement_formation
from .application_record_v1 import marketplace_response_parent_ids
from .proposal_acceptance_v1 import is_marketplace_proposal_record


PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_SERVICES_V1"


class MarketplaceReferenceAgreementAssentServicesError(ValueError):
    """Stable fail-closed reference Agreement-service composition error."""

    def __init__(self) -> None:
        super().__init__("reference Agreement assent service composition failed")


def _fail() -> None:
    raise MarketplaceReferenceAgreementAssentServicesError() from None


def _review_store(store: AgreementAssentCoordinationStore) -> None:
    try:
        retention_class = store.retention_class
        retention_seconds = store.retention_seconds
        initialize = store.initialize
        put = store.put
        peek = store.peek
        list_for_agreement = store.list_for_agreement
        expire_due = store.expire_due
    except Exception:
        _fail()
    if retention_class != AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS:
        _fail()
    if (
        type(retention_seconds) is not int
        or isinstance(retention_seconds, bool)
        or not 1 <= retention_seconds <= MAX_AGREEMENT_ASSENT_RETENTION_SECONDS
    ):
        _fail()
    if not all(
        callable(value)
        for value in (initialize, put, peek, list_for_agreement, expire_due)
    ):
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAgreementAssentServices:
    """One coherent inert Agreement service graph; coordination remains uninitialized."""

    application: MarketplaceApplicationComposition
    authenticated_startup: MarketplaceAuthenticatedStartupComposition
    candidate_authoring: MarketplaceAgreementCandidateAuthoringService
    candidate_resolution: MarketplaceAgreementAssentCandidateResolutionService
    proof: MarketplaceAgreementAssentProofService
    coordination: MarketplaceAgreementAssentCoordinationService
    formation_evaluation: MarketplaceAgreementFormationEvaluationService
    formation: MarketplaceAgreementAssentFormationService
    workflow: MarketplaceAgreementAssentWorkflowService

    def __post_init__(self) -> None:
        if type(self.application) is not MarketplaceApplicationComposition:
            _fail()
        if type(self.authenticated_startup) is not MarketplaceAuthenticatedStartupComposition:
            _fail()
        if (
            type(self.candidate_authoring)
            is not MarketplaceAgreementCandidateAuthoringService
        ):
            _fail()
        if (
            type(self.candidate_resolution)
            is not MarketplaceAgreementAssentCandidateResolutionService
        ):
            _fail()
        if type(self.proof) is not MarketplaceAgreementAssentProofService:
            _fail()
        if type(self.coordination) is not MarketplaceAgreementAssentCoordinationService:
            _fail()
        if (
            type(self.formation_evaluation)
            is not MarketplaceAgreementFormationEvaluationService
        ):
            _fail()
        if type(self.formation) is not MarketplaceAgreementAssentFormationService:
            _fail()
        if type(self.workflow) is not MarketplaceAgreementAssentWorkflowService:
            _fail()
        if self.authenticated_startup.http.application is not self.application:
            _fail()
        if self.candidate_authoring._state is not self.application.state:
            _fail()
        if self.candidate_resolution._read_proposal.__self__ is not self.application.state:
            _fail()
        if self.candidate_resolution._build_candidate.__self__ is not self.candidate_authoring:
            _fail()
        verification_methods = (
            self.authenticated_startup.authentication.verification_method_snapshot
        )
        if self.proof._verification_methods is not verification_methods:
            _fail()
        if self.formation._verification_methods is not verification_methods:
            _fail()
        if self.formation._coordination is not self.coordination:
            _fail()
        if self.formation._formation is not self.formation_evaluation:
            _fail()
        if self.workflow._proof is not self.proof:
            _fail()
        if self.workflow._coordination is not self.coordination:
            _fail()
        if self.workflow._formation is not self.formation:
            _fail()
        if self.coordination._initialized is not False:
            _fail()


def build_reference_agreement_assent_services(
    *,
    application: MarketplaceApplicationComposition,
    authenticated_startup: MarketplaceAuthenticatedStartupComposition,
    coordination_store: AgreementAssentCoordinationStore,
) -> MarketplaceReferenceAgreementAssentServices:
    """Compose reviewed Agreement services without initialization or external I/O."""

    if type(application) is not MarketplaceApplicationComposition:
        _fail()
    if type(authenticated_startup) is not MarketplaceAuthenticatedStartupComposition:
        _fail()
    if authenticated_startup.http.application is not application:
        _fail()
    _review_store(coordination_store)

    try:
        candidate_authoring = MarketplaceAgreementCandidateAuthoringService(
            state=application.state,
            build_record=build_product_agreement_candidate,
            record_identity=agreement_candidate_record_id,
        )
        candidate_resolution = MarketplaceAgreementAssentCandidateResolutionService(
            read_proposal=application.state.peek,
            is_proposal_record=is_marketplace_proposal_record,
            proposal_parent_ids=marketplace_response_parent_ids,
            build_candidate=candidate_authoring.build_candidate,
        )
        verification_methods = (
            authenticated_startup.authentication.verification_method_snapshot
        )
        proof = MarketplaceAgreementAssentProofService(
            verification_methods=verification_methods,
            record_identity=agreement_candidate_record_id,
            build_signing_input=build_product_agreement_assent_signing_input,
            build_verified_proof=build_verified_product_agreement_assent_proof,
        )
        coordination = MarketplaceAgreementAssentCoordinationService(
            store=coordination_store,
            prepare_verified_assent=build_prepared_product_agreement_assent,
        )
        formation_evaluation = MarketplaceAgreementFormationEvaluationService(
            evaluate=evaluate_product_agreement_formation,
        )
        formation = MarketplaceAgreementAssentFormationService(
            coordination=coordination,
            verification_methods=verification_methods,
            formation=formation_evaluation,
            record_identity=agreement_candidate_record_id,
            reverify_prepared_proof=reverify_prepared_product_agreement_assent,
            build_formation_evidence=(
                build_product_agreement_formation_evidence_from_verified_assent
            ),
        )
        workflow = MarketplaceAgreementAssentWorkflowService(
            proof=proof,
            coordination=coordination,
            formation=formation,
        )
        return MarketplaceReferenceAgreementAssentServices(
            application=application,
            authenticated_startup=authenticated_startup,
            candidate_authoring=candidate_authoring,
            candidate_resolution=candidate_resolution,
            proof=proof,
            coordination=coordination,
            formation_evaluation=formation_evaluation,
            formation=formation,
            workflow=workflow,
        )
    except MarketplaceReferenceAgreementAssentServicesError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAgreementAssentServices",
    "MarketplaceReferenceAgreementAssentServicesError",
    "PROFILE_NAME",
    "build_reference_agreement_assent_services",
]
