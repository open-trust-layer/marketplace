from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import marketplace.runtime as runtime_api
from marketplace.reference import (
    TYPE_INTENT,
    evaluate_discovery,
    evaluate_match,
    federation_v1,
    record_identity_text,
    validate_market_record,
)
from marketplace.runtime import (
    BoundedFederationPageHydrator,
    FederationContinuationPlanner,
    FederationEndpointAuthorization,
    FederationOperationProfile,
    PageHydrationLimits,
    ValidatedFederationPage,
    compose_offline_federation_service,
    create_in_memory_runtime,
)
from marketplace.runtime.https_transport import HttpsFederationExchangeResult
from marketplace.runtime.synchronization import (
    SYNC_FINAL_PAGE_ACCEPTED,
    BoundedFederationSynchronizationOrchestrator,
    FederationControlTarget,
    FederationSynchronizationError,
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


def _final_page() -> tuple[object, ...]:
    return federation_v1.make_transport_envelope(
        federation_v1.MSG_SYNC_RESULT,
        {
            "version": 1,
            "source": SOURCE,
            "operation": federation_v1.OP_SYNC,
            "scope_fingerprint": federation_v1.scope_fingerprint(_scope()),
            "record_ids": [],
            "source_completeness": "COMPLETE_FOR_DECLARED_SOURCE",
            "page_truncated": False,
        },
    )


def _target() -> FederationControlTarget:
    endpoint = "https://peer.example/federation/1"
    authorization = FederationEndpointAuthorization(
        authorization_id="auth-1",
        policy_id="test-policy",
        policy_version=1,
        canonical_endpoint=endpoint,
        hostname="peer.example",
        port=443,
        path_mode="EXACT",
        path="/federation/1",
        allowed_operations=(federation_v1.OP_SYNC,),
        issued_at_epoch=1,
        expires_at_epoch=2,
    )
    return FederationControlTarget(endpoint=endpoint, authorization=authorization)


def _compose_service(runtime):
    return compose_offline_federation_service(
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


def _planner(service):
    return FederationContinuationPlanner(
        federation_service=service,
        validate_exchange_request=federation_v1.validate_exchange_request,
        bind_cursor=federation_v1.bind_cursor,
        validate_cursor_binding=federation_v1.validate_cursor_binding,
    )


def _hydrator(service):
    return BoundedFederationPageHydrator(
        federation_service=service,
        record_retriever=_NeverRecordRetriever(),
        verify_record_value=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("empty page must not verify a Record")
        ),
        limits=PageHydrationLimits(max_records=4, total_timeout_seconds=60.0),
        monotonic_clock=lambda: 0.0,
    )


class _NeverRecordRetriever:
    def preflight(self, **kwargs):
        raise AssertionError("empty page must not preflight a Record")

    def retrieve(self, **kwargs):
        raise AssertionError("empty page must not retrieve a Record")


class _AliasingControlTransport:
    def __init__(self, envelope):
        self.envelope = envelope
        self.calls = 0

    def exchange(self, prepared, *, endpoint, authorization):
        self.calls += 1
        return HttpsFederationExchangeResult(
            response_envelope=self.envelope,
            http_status=200,
            response_body_bytes=100,
            selected_address="203.0.113.10",
            tls_server_hostname="peer.example",
        )


class _UnsupportedPayload(dict):
    pass


class _ExplodingControlTargets:
    def __init__(self):
        self.iterated = False

    def __iter__(self):
        self.iterated = True
        raise AssertionError("non-tuple control targets must never be enumerated")


class FederationSynchronizationHardeningTests(unittest.TestCase):
    def _stack(self, transport, provider):
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=16,
        )
        service = _compose_service(runtime)
        planner = _planner(service)
        hydrator = _hydrator(service)
        orchestrator = BoundedFederationSynchronizationOrchestrator(
            federation_service=service,
            control_transport=transport,
            page_hydrator=hydrator,
            continuation_planner=planner,
            record_target_provider=provider,
            monotonic_clock=lambda: 0.0,
        )
        return runtime, service, planner, orchestrator

    def test_m31_required_repository_and_runtime_package_artifacts_are_present(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "src/marketplace/runtime/synchronization.py").is_file())
        self.assertTrue((root / "docs/bounded-multipage-federation-synchronization.md").is_file())
        self.assertIs(
            runtime_api.BoundedFederationSynchronizationOrchestrator,
            BoundedFederationSynchronizationOrchestrator,
        )

    def test_non_tuple_control_targets_fail_without_enumeration_or_transport(self):
        transport = _AliasingControlTransport(_final_page())
        runtime, service, planner, orchestrator = self._stack(
            transport,
            lambda record_ids, *, page_number: (),
        )
        exploding = _ExplodingControlTargets()
        try:
            initial = _request()
            prepared = service.prepare(initial)
            with self.assertRaises(FederationSynchronizationError) as caught:
                orchestrator.synchronize(initial, prepared, exploding)  # type: ignore[arg-type]
            self.assertEqual(caught.exception.code, "CONTROL_TARGET_LIMIT_EXCEEDED")
            self.assertFalse(exploding.iterated)
            self.assertEqual(transport.calls, 0)
        finally:
            runtime.close()

    def test_orchestrator_rejects_split_m24_service_graph(self):
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=16,
        )
        service = _compose_service(runtime)
        other_service = _compose_service(runtime)
        transport = _AliasingControlTransport(_final_page())
        try:
            with self.assertRaisesRegex(ValueError, "page_hydrator MUST share"):
                BoundedFederationSynchronizationOrchestrator(
                    federation_service=service,
                    control_transport=transport,
                    page_hydrator=_hydrator(other_service),
                    continuation_planner=_planner(service),
                    record_target_provider=lambda record_ids, *, page_number: (),
                    monotonic_clock=lambda: 0.0,
                )
            with self.assertRaisesRegex(ValueError, "continuation_planner MUST share"):
                BoundedFederationSynchronizationOrchestrator(
                    federation_service=service,
                    control_transport=transport,
                    page_hydrator=_hydrator(service),
                    continuation_planner=_planner(other_service),
                    record_target_provider=lambda record_ids, *, page_number: (),
                    monotonic_clock=lambda: 0.0,
                )
        finally:
            runtime.close()

    def test_hostile_validated_page_binding_drift_fails_before_target_provider(self):
        transport = _AliasingControlTransport(_final_page())
        provider_called = False

        def provider(record_ids, *, page_number):
            nonlocal provider_called
            provider_called = True
            return ()

        runtime, service, planner, orchestrator = self._stack(transport, provider)
        try:
            initial = _request()
            prepared = service.prepare(initial)
            hostile_page = ValidatedFederationPage(
                source="https://attacker.example/federation",
                operation=prepared.binding.operation,
                scope_fingerprint=prepared.binding.scope_fingerprint,
                page_size=prepared.binding.page_size,
                record_ids=(),
                source_completeness="COMPLETE_FOR_DECLARED_SOURCE",
                page_truncated=False,
                next_cursor=None,
            )
            with patch.object(service, "validate_page", return_value=hostile_page):
                with self.assertRaises(FederationSynchronizationError) as caught:
                    orchestrator.synchronize(initial, prepared, (_target(),))
            self.assertEqual(caught.exception.code, "VALIDATED_PAGE_BINDING_MISMATCH")
            self.assertFalse(provider_called)
            self.assertEqual(transport.calls, 1)
        finally:
            runtime.close()

    def test_provider_alias_mutation_cannot_change_detached_control_response(self):
        original = _final_page()
        transport = _AliasingControlTransport(original)

        def hostile_provider(record_ids, *, page_number):
            self.assertEqual(record_ids, ())
            self.assertEqual(page_number, 1)
            payload = transport.envelope[3]
            payload["source_completeness"] = "PARTIAL_SOURCE"
            payload["page_truncated"] = True
            payload["next_cursor"] = b"attacker-cursor"
            return ()

        runtime, service, planner, orchestrator = self._stack(transport, hostile_provider)
        try:
            initial = _request()
            prepared = service.prepare(initial)
            with patch.object(planner, "plan", side_effect=AssertionError("detached final page must stay final")):
                outcome = orchestrator.synchronize(initial, prepared, (_target(),))
            self.assertEqual(outcome.disposition, SYNC_FINAL_PAGE_ACCEPTED)
            self.assertTrue(outcome.final_page_observed)
            self.assertEqual(outcome.last_source_completeness, "COMPLETE_FOR_DECLARED_SOURCE")
            self.assertEqual(outcome.control_exchanges, 1)
            self.assertEqual(outcome.continuations_planned, 0)
            self.assertTrue(transport.envelope[3]["page_truncated"])
        finally:
            runtime.close()

    def test_unsupported_response_payload_subclass_fails_before_page_provider(self):
        normal = _final_page()
        hostile_payload = _UnsupportedPayload(normal[3])
        hostile_envelope = (normal[0], normal[1], normal[2], hostile_payload)
        transport = _AliasingControlTransport(hostile_envelope)
        provider_called = False

        def provider(record_ids, *, page_number):
            nonlocal provider_called
            provider_called = True
            return ()

        runtime, service, planner, orchestrator = self._stack(transport, provider)
        try:
            initial = _request()
            prepared = service.prepare(initial)
            with self.assertRaises(FederationSynchronizationError) as caught:
                orchestrator.synchronize(initial, prepared, (_target(),))
            self.assertEqual(caught.exception.code, "CONTROL_RESPONSE_DETACH_FAILED")
            self.assertFalse(provider_called)
            self.assertEqual(transport.calls, 1)
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
