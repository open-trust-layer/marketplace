from __future__ import annotations

import ast
import dataclasses
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from marketplace.reference import (
    CORE_PROFILE,
    TYPE_INTENT,
    evaluate_discovery,
    evaluate_match,
    federation_v1,
    record_identity_text,
    validate_market_record,
)
from marketplace.runtime import (
    CONTINUATION_PREPARED,
    NO_CONTINUATION,
    FederationContinuationError,
    FederationContinuationPlanner,
    FederationOperationProfile,
    PreparedFederationExchange,
    ValidatedFederationPage,
    compose_offline_federation_service,
    create_in_memory_runtime,
)


SOURCE = "https://peer.example/federation"


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def request(*, cursor: bytes | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SYNC,
        "scope": scope(),
        "required_capabilities": [federation_v1.CAP_SYNC],
        "page_size": 4,
    }
    if cursor is not None:
        value["cursor"] = cursor
    return value


class FederationContinuationTests(unittest.TestCase):
    def runtime_service_planner(self):
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=8,
        )
        service = compose_offline_federation_service(
            runtime,
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
        planner = FederationContinuationPlanner(
            federation_service=service,
            validate_exchange_request=federation_v1.validate_exchange_request,
            bind_cursor=federation_v1.bind_cursor,
            validate_cursor_binding=federation_v1.validate_cursor_binding,
        )
        return runtime, service, planner

    def validated_page(self, service, prepared, *, next_cursor: bytes | None):
        payload: dict[str, object] = {
            "version": 1,
            "source": SOURCE,
            "operation": federation_v1.OP_SYNC,
            "scope_fingerprint": federation_v1.scope_fingerprint(scope()),
            "record_ids": [],
            "source_completeness": "PARTIAL_SOURCE",
            "page_truncated": next_cursor is not None,
        }
        if next_cursor is not None:
            payload["next_cursor"] = next_cursor
        envelope = federation_v1.make_transport_envelope(federation_v1.MSG_SYNC_RESULT, payload)
        return service.validate_page(prepared, envelope)

    def test_truncated_page_prepares_exactly_one_unsent_continuation(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"page-2")
            outcome = planner.plan(prior_request, prior_prepared, page)
            self.assertEqual(outcome.disposition, CONTINUATION_PREPARED)
            self.assertTrue(outcome.prior_page_truncated)
            self.assertIsInstance(outcome.prepared_exchange, PreparedFederationExchange)
            self.assertFalse(outcome.prepared_exchange.transmitted)
            self.assertEqual(outcome.prepared_exchange.binding, prior_prepared.binding)
            self.assertEqual(outcome.prepared_exchange.envelope[:3], prior_prepared.envelope[:3])
            self.assertEqual(outcome.prepared_exchange.envelope[3]["cursor"], b"page-2")
            self.assertFalse(outcome.network_was_invoked)
            self.assertFalse(outcome.cursor_automatically_followed)
            self.assertFalse(outcome.authorization_established)
            self.assertFalse(outcome.source_completeness_established)
            self.assertEqual(outcome.global_completeness, "UNKNOWN")
            self.assertFalse(outcome.absence_is_deletion_evidence)
            self.assertFalse(outcome.creates_agreement)
            self.assertFalse(outcome.authorizes_side_effects)
            self.assertNotIn("cursor", prior_request)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_already_cursored_request_replaces_only_cursor(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request(cursor=b"page-2")
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"page-3")
            outcome = planner.plan(prior_request, prior_prepared, page)
            next_request = outcome.prepared_exchange.envelope[3]
            self.assertEqual(next_request["cursor"], b"page-3")
            prior_without = dict(prior_request)
            next_without = dict(next_request)
            prior_without.pop("cursor")
            next_without.pop("cursor")
            self.assertEqual(next_without, prior_without)
            self.assertEqual(prior_request["cursor"], b"page-2")
        finally:
            runtime.close()

    def test_final_page_returns_no_continuation_after_context_validation(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=None)
            outcome = planner.plan(prior_request, prior_prepared, page)
            self.assertEqual(outcome.disposition, NO_CONTINUATION)
            self.assertIsNone(outcome.prepared_exchange)
            self.assertFalse(outcome.prior_page_truncated)
        finally:
            runtime.close()

    def test_final_page_does_not_invoke_cursor_helpers_or_prepare_again(self):
        runtime, service, _ = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=None)
            binder = Mock(side_effect=AssertionError("cursor binder must not run"))
            validator = Mock(side_effect=AssertionError("cursor validator must not run"))
            planner = FederationContinuationPlanner(
                federation_service=service,
                validate_exchange_request=federation_v1.validate_exchange_request,
                bind_cursor=binder,
                validate_cursor_binding=validator,
            )
            with patch.object(service, "prepare", side_effect=AssertionError("next prepare must not run")):
                outcome = planner.plan(prior_request, prior_prepared, page)
            self.assertEqual(outcome.disposition, NO_CONTINUATION)
            binder.assert_not_called()
            validator.assert_not_called()
        finally:
            runtime.close()

    def test_mismatched_validated_page_fails_even_when_final(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=None)
            hostile = dataclasses.replace(page, source="https://other.example/federation")
            with self.assertRaises(FederationContinuationError) as caught:
                planner.plan(prior_request, prior_prepared, hostile)
            self.assertEqual(caught.exception.code, "VALIDATED_PAGE_BINDING_MISMATCH")
        finally:
            runtime.close()

    def test_prior_request_payload_must_match_prior_prepared_envelope(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            original = request()
            prior_prepared = service.prepare(original)
            page = self.validated_page(service, prior_prepared, next_cursor=b"page-2")
            changed = request()
            changed["page_size"] = 3
            with self.assertRaises(FederationContinuationError) as caught:
                planner.plan(changed, prior_prepared, page)
            self.assertEqual(caught.exception.code, "INVALID_PRIOR_PREPARED_EXCHANGE")
        finally:
            runtime.close()

    def test_truncated_page_requires_bounded_nonempty_cursor(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"ok")
            hostile = dataclasses.replace(page, next_cursor=b"")
            with self.assertRaises(FederationContinuationError) as caught:
                planner.plan(prior_request, prior_prepared, hostile)
            self.assertEqual(caught.exception.code, "INVALID_VALIDATED_PAGE")
        finally:
            runtime.close()

    def test_hostile_cursor_validator_cannot_promote_authorization(self):
        runtime, service, _ = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"page-2")

            def hostile_validator(binding, source, operation, scope_value):
                result = federation_v1.validate_cursor_binding(binding, source, operation, scope_value)
                result["authorization_proof"] = True
                return result

            planner = FederationContinuationPlanner(
                federation_service=service,
                validate_exchange_request=federation_v1.validate_exchange_request,
                bind_cursor=federation_v1.bind_cursor,
                validate_cursor_binding=hostile_validator,
            )
            with self.assertRaises(FederationContinuationError) as caught:
                planner.plan(prior_request, prior_prepared, page)
            self.assertEqual(caught.exception.code, "CURSOR_AUTHORITY_ESCALATION")
        finally:
            runtime.close()

    def test_boolean_cursor_byte_count_cannot_impersonate_integer(self):
        runtime, service, _ = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"x")

            def hostile_validator(binding, source, operation, scope_value):
                result = federation_v1.validate_cursor_binding(binding, source, operation, scope_value)
                result["cursor_bytes"] = True
                return result

            planner = FederationContinuationPlanner(
                federation_service=service,
                validate_exchange_request=federation_v1.validate_exchange_request,
                bind_cursor=federation_v1.bind_cursor,
                validate_cursor_binding=hostile_validator,
            )
            with self.assertRaises(FederationContinuationError) as caught:
                planner.plan(prior_request, prior_prepared, page)
            self.assertEqual(caught.exception.code, "INVALID_CURSOR_VALIDATOR_RESULT")
        finally:
            runtime.close()

    def test_hostile_next_prepare_cannot_report_transmitted(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"page-2")
            actual_prepare = service.prepare

            def hostile_prepare(next_request):
                return dataclasses.replace(actual_prepare(next_request), transmitted=True)

            with patch.object(service, "prepare", side_effect=hostile_prepare):
                with self.assertRaises(FederationContinuationError) as caught:
                    planner.plan(prior_request, prior_prepared, page)
            self.assertEqual(caught.exception.code, "INVALID_CONTINUATION_PREPARED_EXCHANGE")
        finally:
            runtime.close()

    def test_hostile_next_prepare_cannot_change_message_profile(self):
        runtime, service, planner = self.runtime_service_planner()
        try:
            prior_request = request()
            prior_prepared = service.prepare(prior_request)
            page = self.validated_page(service, prior_prepared, next_cursor=b"page-2")
            actual_prepare = service.prepare

            def hostile_prepare(next_request):
                prepared = actual_prepare(next_request)
                return dataclasses.replace(
                    prepared,
                    envelope=("OLP-TRANSPORT", 1, "https://example.test/other-message", next_request),
                )

            with patch.object(service, "prepare", side_effect=hostile_prepare):
                with self.assertRaises(FederationContinuationError) as caught:
                    planner.plan(prior_request, prior_prepared, page)
            # M30 rejects the stale integrity witness during forged exchange
            # construction, before M29 can inspect the returned message profile.
            self.assertEqual(caught.exception.code, "CONTINUATION_PREPARE_FAILED")
        finally:
            runtime.close()

    def test_m29_source_has_no_network_filesystem_process_concurrency_or_logging_surface(self):
        path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "runtime" / "continuation.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden_modules = {
            "socket",
            "ssl",
            "urllib",
            "http",
            "requests",
            "httpx",
            "subprocess",
            "asyncio",
            "threading",
            "concurrent",
            "multiprocessing",
            "logging",
            "pathlib",
            "os",
        }
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(forbidden_modules.isdisjoint(imported), imported & forbidden_modules)
        forbidden_calls = {"open", "exec", "eval", "compile", "__import__"}
        direct_calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(forbidden_calls.isdisjoint(direct_calls), direct_calls & forbidden_calls)


if __name__ == "__main__":
    unittest.main()
