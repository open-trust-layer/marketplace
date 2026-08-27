from __future__ import annotations

import dataclasses
import unittest
from unittest.mock import patch

from marketplace.reference import (
    TYPE_INTENT,
    evaluate_discovery,
    evaluate_match,
    federation_v1,
    record_identity_text,
    validate_market_record,
)
from marketplace.runtime import (
    FederationContinuationError,
    FederationContinuationPlanner,
    FederationOperationProfile,
    compose_offline_federation_service,
    create_in_memory_runtime,
)

SOURCE = "https://peer.example/federation"


def _scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def _request() -> dict[str, object]:
    return {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SYNC,
        "scope": _scope(),
        "required_capabilities": [federation_v1.CAP_SYNC],
        "page_size": 4,
    }


class FederationContinuationHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=8,
        )
        self.service = compose_offline_federation_service(
            self.runtime,
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            validate_exchange_request=federation_v1.validate_exchange_request,
            make_transport_envelope=federation_v1.make_transport_envelope,
            validate_transport_envelope=federation_v1.validate_transport_envelope,
            validate_exchange_result=federation_v1.validate_exchange_result,
            operation_profiles=(
                FederationOperationProfile(
                    federation_v1.OP_SYNC,
                    federation_v1.MSG_SYNC_REQUEST,
                    federation_v1.MSG_SYNC_RESULT,
                ),
            ),
        )
        self.prior_request = _request()
        self.prior_prepared = self.service.prepare(self.prior_request)
        payload = {
            "version": 1,
            "source": SOURCE,
            "operation": federation_v1.OP_SYNC,
            "scope_fingerprint": federation_v1.scope_fingerprint(_scope()),
            "record_ids": [],
            "source_completeness": "PARTIAL_SOURCE",
            "page_truncated": True,
            "next_cursor": b"page-2",
        }
        envelope = federation_v1.make_transport_envelope(federation_v1.MSG_SYNC_RESULT, payload)
        self.page = self.service.validate_page(self.prior_prepared, envelope)

    def tearDown(self) -> None:
        self.runtime.close()

    def planner(self, *, request_validator=None, binder=None, cursor_validator=None):
        return FederationContinuationPlanner(
            federation_service=self.service,
            validate_exchange_request=request_validator or federation_v1.validate_exchange_request,
            bind_cursor=binder or federation_v1.bind_cursor,
            validate_cursor_binding=cursor_validator or federation_v1.validate_cursor_binding,
        )

    def test_request_validator_cannot_mutate_detached_prior_request(self):
        caller_snapshot = dataclasses.asdict(dataclasses.make_dataclass("Box", [("value", dict)])(dict(self.prior_request)))["value"]
        caller_scope_before = dict(self.prior_request["scope"])

        def mutating_validator(value):
            normalized = federation_v1.validate_exchange_request(value)
            value["page_size"] = 3
            return normalized

        with self.assertRaises(FederationContinuationError) as caught:
            self.planner(request_validator=mutating_validator).plan(
                self.prior_request,
                self.prior_prepared,
                self.page,
            )
        self.assertEqual(caught.exception.code, "REQUEST_VALIDATOR_MUTATED_INPUT")
        self.assertEqual(self.prior_request["page_size"], caller_snapshot["page_size"])
        self.assertEqual(self.prior_request["scope"], caller_scope_before)

    def test_cursor_binder_cannot_mutate_detached_scope(self):
        def mutating_binder(source, operation, scope_value, cursor):
            binding = federation_v1.bind_cursor(source, operation, scope_value, cursor)
            scope_value["record_types"] = ()
            return binding

        with self.assertRaises(FederationContinuationError) as caught:
            self.planner(binder=mutating_binder).plan(
                self.prior_request,
                self.prior_prepared,
                self.page,
            )
        self.assertEqual(caught.exception.code, "CURSOR_HELPER_MUTATED_SCOPE")

    def test_cursor_validator_cannot_mutate_detached_scope(self):
        def mutating_validator(binding, source, operation, scope_value):
            result = federation_v1.validate_cursor_binding(binding, source, operation, scope_value)
            scope_value["record_types"] = ()
            return result

        with self.assertRaises(FederationContinuationError) as caught:
            self.planner(cursor_validator=mutating_validator).plan(
                self.prior_request,
                self.prior_prepared,
                self.page,
            )
        self.assertEqual(caught.exception.code, "CURSOR_HELPER_MUTATED_SCOPE")

    def test_cursor_validator_cannot_promote_source_completeness(self):
        def hostile_validator(binding, source, operation, scope_value):
            result = federation_v1.validate_cursor_binding(binding, source, operation, scope_value)
            result["source_completeness_proof"] = True
            return result

        with self.assertRaises(FederationContinuationError) as caught:
            self.planner(cursor_validator=hostile_validator).plan(
                self.prior_request,
                self.prior_prepared,
                self.page,
            )
        self.assertEqual(caught.exception.code, "CURSOR_AUTHORITY_ESCALATION")

    def test_fabricated_validated_page_cannot_authorize_side_effects(self):
        hostile_page = dataclasses.replace(self.page, authorizes_side_effects=True)
        with self.assertRaises(FederationContinuationError) as caught:
            self.planner().plan(self.prior_request, self.prior_prepared, hostile_page)
        self.assertEqual(caught.exception.code, "VALIDATED_PAGE_AUTHORITY_ESCALATION")

    def test_fabricated_prior_prepared_exchange_cannot_be_pretransmitted(self):
        hostile_prepared = dataclasses.replace(self.prior_prepared, transmitted=True)
        with self.assertRaises(FederationContinuationError) as caught:
            self.planner().plan(self.prior_request, hostile_prepared, self.page)
        self.assertEqual(caught.exception.code, "INVALID_PRIOR_PREPARED_EXCHANGE")

    def test_hostile_request_validator_result_must_match_exact_shape(self):
        def hostile_validator(value):
            result = dict(federation_v1.validate_exchange_request(value))
            result["unexpected"] = "field"
            return result

        with self.assertRaises(FederationContinuationError) as caught:
            self.planner(request_validator=hostile_validator).plan(
                self.prior_request,
                self.prior_prepared,
                self.page,
            )
        self.assertEqual(caught.exception.code, "INVALID_REQUEST_VALIDATOR_RESULT")

    def test_continuation_prepare_cannot_mutate_next_request(self):
        actual_prepare = self.service.prepare

        def mutating_prepare(value):
            prepared = actual_prepare(value)
            value["page_size"] = 3
            return prepared

        with patch.object(self.service, "prepare", side_effect=mutating_prepare):
            with self.assertRaises(FederationContinuationError) as caught:
                self.planner().plan(self.prior_request, self.prior_prepared, self.page)
        self.assertEqual(caught.exception.code, "CONTINUATION_PREPARE_MUTATED_REQUEST")

    def test_continuation_prepare_cannot_drift_binding(self):
        actual_prepare = self.service.prepare

        def drifting_prepare(value):
            prepared = actual_prepare(value)
            return dataclasses.replace(
                prepared,
                binding=dataclasses.replace(prepared.binding, page_size=3),
            )

        with patch.object(self.service, "prepare", side_effect=drifting_prepare):
            with self.assertRaises(FederationContinuationError) as caught:
                self.planner().plan(self.prior_request, self.prior_prepared, self.page)
        self.assertEqual(caught.exception.code, "CONTINUATION_BINDING_DRIFT")


if __name__ == "__main__":
    unittest.main()
