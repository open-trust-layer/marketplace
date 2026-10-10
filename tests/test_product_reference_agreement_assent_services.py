from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_coordination import (
    MemoryAgreementAssentCoordinationStore,
)
from marketplace.reference.agreement_assent_application_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAgreementAssentServices,
    MarketplaceReferenceAgreementAssentServicesError,
    build_reference_agreement_assent_services,
)
from marketplace.reference.agreement_assent_coordination_v1 import (
    build_prepared_product_agreement_assent,
)
from marketplace.reference.agreement_assent_formation_v1 import (
    build_product_agreement_formation_evidence_from_verified_assent,
    reverify_prepared_product_agreement_assent,
)
from marketplace.reference.agreement_assent_v1 import (
    build_product_agreement_assent_signing_input,
    build_verified_product_agreement_assent_proof,
)
from marketplace.reference.agreement_candidate_v1 import (
    agreement_candidate_record_id,
    build_product_agreement_candidate,
)
from marketplace.reference.agreement_formation_v1 import (
    evaluate_product_agreement_formation,
)
from tests.test_m17_5t_auth_startup_composition import _compose


def _store() -> MemoryAgreementAssentCoordinationStore:
    return MemoryAgreementAssentCoordinationStore(clock=lambda: 123)


class ProductReferenceAgreementAssentServicesTests(unittest.TestCase):
    def test_profile_exact_graph_and_shared_identity_bindings(self) -> None:
        authenticated, application, _provisioning, _runtime_inputs = _compose()
        store = _store()
        result = build_reference_agreement_assent_services(
            application=application,
            authenticated_startup=authenticated,
            coordination_store=store,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_SERVICES_V1",
        )
        self.assertIs(type(result), MarketplaceReferenceAgreementAssentServices)
        self.assertIs(result.application, application)
        self.assertIs(result.authenticated_startup, authenticated)
        self.assertIs(result.candidate_authoring._state, application.state)
        self.assertIs(
            result.candidate_resolution._read_proposal.__self__,
            application.state,
        )
        self.assertIs(
            result.candidate_resolution._build_candidate.__self__,
            result.candidate_authoring,
        )
        verification_methods = authenticated.authentication.verification_method_snapshot
        self.assertIs(result.proof._verification_methods, verification_methods)
        self.assertIs(result.formation._verification_methods, verification_methods)
        self.assertIs(result.coordination._store, store)
        self.assertIs(result.workflow._proof, result.proof)
        self.assertIs(result.workflow._coordination, result.coordination)
        self.assertIs(result.workflow._formation, result.formation)
        self.assertFalse(result.coordination._initialized)

    def test_exact_reviewed_reference_functions_are_selected(self) -> None:
        authenticated, application, _provisioning, _runtime_inputs = _compose()
        result = build_reference_agreement_assent_services(
            application=application,
            authenticated_startup=authenticated,
            coordination_store=_store(),
        )
        self.assertIs(result.candidate_authoring._build_record, build_product_agreement_candidate)
        self.assertIs(result.candidate_authoring._record_identity, agreement_candidate_record_id)
        self.assertIs(result.proof._record_identity, agreement_candidate_record_id)
        self.assertIs(
            result.proof._build_signing_input,
            build_product_agreement_assent_signing_input,
        )
        self.assertIs(
            result.proof._build_verified_proof,
            build_verified_product_agreement_assent_proof,
        )
        self.assertIs(
            result.coordination._prepare_verified_assent,
            build_prepared_product_agreement_assent,
        )
        self.assertIs(
            result.formation._reverify_prepared_proof,
            reverify_prepared_product_agreement_assent,
        )
        self.assertIs(
            result.formation._build_formation_evidence,
            build_product_agreement_formation_evidence_from_verified_assent,
        )
        self.assertIs(
            result.formation_evaluation._evaluate,
            evaluate_product_agreement_formation,
        )

    def test_composition_does_not_initialize_store_or_consume_clock(self) -> None:
        authenticated, application, _provisioning, _runtime_inputs = _compose()
        store = _store()
        with (
            patch.object(
                MemoryAgreementAssentCoordinationStore,
                "initialize",
                side_effect=AssertionError("store initialized"),
            ) as initialize,
            patch.object(
                MemoryAgreementAssentCoordinationStore,
                "_now",
                side_effect=AssertionError("store clock consumed"),
            ) as now,
        ):
            result = build_reference_agreement_assent_services(
                application=application,
                authenticated_startup=authenticated,
                coordination_store=store,
            )

        self.assertFalse(result.coordination._initialized)
        initialize.assert_not_called()
        now.assert_not_called()

    def test_mismatched_application_and_authenticated_graph_fail_closed(self) -> None:
        authenticated, _application, _provisioning, _runtime_inputs = _compose()
        _other_authenticated, other_application, _p2, _r2 = _compose()

        with self.assertRaises(MarketplaceReferenceAgreementAssentServicesError):
            build_reference_agreement_assent_services(
                application=other_application,
                authenticated_startup=authenticated,
                coordination_store=_store(),
            )

    def test_invalid_store_shape_fails_before_service_construction(self) -> None:
        authenticated, application, _provisioning, _runtime_inputs = _compose()
        with self.assertRaises(MarketplaceReferenceAgreementAssentServicesError):
            build_reference_agreement_assent_services(
                application=application,
                authenticated_startup=authenticated,
                coordination_store=object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
