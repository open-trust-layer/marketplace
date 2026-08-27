from __future__ import annotations

import ast
import unittest
from pathlib import Path
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
    BoundedFederationPageHydrator,
    FederationContinuationPlanner,
    FederationEndpointAuthorization,
    FederationOperationProfile,
    PageHydrationLimits,
    compose_offline_federation_service,
    create_in_memory_runtime,
)
from marketplace.runtime.continuation import ContinuationPlanOutcome, NO_CONTINUATION
from marketplace.runtime.https_transport import HttpsFederationExchangeResult
from marketplace.runtime.synchronization import (
    MAX_SYNCHRONIZATION_PAGES,
    MAX_SYNCHRONIZATION_RECORDS,
    MAX_SYNCHRONIZATION_TIMEOUT_SECONDS,
    SYNC_FINAL_PAGE_ACCEPTED,
    SYNC_STOPPED_CONTROL_TARGET_LIMIT,
    SYNC_STOPPED_PAGE_LIMIT,
    SYNC_STOPPED_TIME_LIMIT,
    BoundedFederationSynchronizationOrchestrator,
    FederationControlTarget,
    FederationSynchronizationError,
    FederationSynchronizationLimits,
)


SOURCE = "https://peer.example/federation"
VALID_RECORD_ID_1 = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"
VALID_RECORD_ID_2 = "r1_krAuHnpOl5qW631XJC4ecOQISaB93rVNQ0bFvU0ed1w"


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


def page_envelope(
    *,
    next_cursor: bytes | None,
    record_ids: tuple[str, ...] = (),
    completeness: str | None = None,
) -> tuple[object, ...]:
    payload: dict[str, object] = {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SYNC,
        "scope_fingerprint": federation_v1.scope_fingerprint(scope()),
        "record_ids": list(record_ids),
        "source_completeness": completeness
        or ("PARTIAL_SOURCE" if next_cursor is not None else "COMPLETE_FOR_DECLARED_SOURCE"),
        "page_truncated": next_cursor is not None,
    }
    if next_cursor is not None:
        payload["next_cursor"] = next_cursor
    return federation_v1.make_transport_envelope(federation_v1.MSG_SYNC_RESULT, payload)


def authorization(index: int) -> FederationEndpointAuthorization:
    path = f"/federation/{index}"
    endpoint = f"https://peer.example{path}"
    return FederationEndpointAuthorization(
        authorization_id=f"auth-{index}",
        policy_id="test-policy",
        policy_version=1,
        canonical_endpoint=endpoint,
        hostname="peer.example",
        port=443,
        path_mode="EXACT",
        path=path,
        allowed_operations=(federation_v1.OP_SYNC,),
        issued_at_epoch=1,
        expires_at_epoch=2,
    )


def control_target(index: int) -> FederationControlTarget:
    auth = authorization(index)
    return FederationControlTarget(endpoint=auth.canonical_endpoint, authorization=auth)


class NeverRecordRetriever:
    def preflight(self, **kwargs):
        raise AssertionError("empty page must not preflight a Record")

    def retrieve(self, **kwargs):
        raise AssertionError("empty page must not retrieve a Record")


class SequencedControlTransport:
    def __init__(self, envelopes: tuple[tuple[object, ...], ...]):
        self.envelopes = envelopes
        self.calls: list[tuple[object, str, FederationEndpointAuthorization]] = []

    def exchange(self, prepared, *, endpoint, authorization):
        index = len(self.calls)
        if index >= len(self.envelopes):
            raise AssertionError("unexpected extra control exchange")
        self.calls.append((prepared, endpoint, authorization))
        return HttpsFederationExchangeResult(
            response_envelope=self.envelopes[index],
            http_status=200,
            response_body_bytes=100,
            selected_address="203.0.113.10",
            tls_server_hostname="peer.example",
        )


class SequenceClock:
    def __init__(self, values: list[float]):
        self._values = iter(values)
        self._last = values[-1]

    def __call__(self) -> float:
        try:
            self._last = next(self._values)
        except StopIteration:
            pass
        return self._last


class FederationSynchronizationTests(unittest.TestCase):
    def stack(self, transport, *, target_provider=None, limits=None, clock=None):
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=16,
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
        hydrator = BoundedFederationPageHydrator(
            federation_service=service,
            record_retriever=NeverRecordRetriever(),
            verify_record_value=lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("empty page must not verify a Record")
            ),
            limits=PageHydrationLimits(max_records=4, total_timeout_seconds=60.0),
            monotonic_clock=lambda: 0.0,
        )
        provider = target_provider or (lambda record_ids, *, page_number: ())
        orchestrator = BoundedFederationSynchronizationOrchestrator(
            federation_service=service,
            control_transport=transport,
            page_hydrator=hydrator,
            continuation_planner=planner,
            record_target_provider=provider,
            limits=limits,
            monotonic_clock=clock or (lambda: 0.0),
        )
        return runtime, service, planner, hydrator, orchestrator

    def test_three_pages_use_three_explicit_control_slots_and_two_continuations(self):
        transport = SequencedControlTransport(
            (
                page_envelope(next_cursor=b"page-2"),
                page_envelope(next_cursor=b"page-3"),
                page_envelope(next_cursor=None),
            )
        )
        provider_calls: list[tuple[int, tuple[str, ...]]] = []

        def provider(record_ids, *, page_number):
            provider_calls.append((page_number, record_ids))
            return ()

        runtime, service, planner, hydrator, orchestrator = self.stack(
            transport,
            target_provider=provider,
        )
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            outcome = orchestrator.synchronize(
                initial_request,
                prepared,
                (control_target(1), control_target(2), control_target(3)),
            )
            self.assertEqual(outcome.disposition, SYNC_FINAL_PAGE_ACCEPTED)
            self.assertEqual(outcome.pages_accepted, 3)
            self.assertEqual(outcome.control_exchanges, 3)
            self.assertEqual(outcome.continuations_planned, 2)
            self.assertEqual(outcome.continuations_transmitted, 2)
            self.assertEqual(outcome.hydrated_record_count, 0)
            self.assertEqual(outcome.record_retrieval_attempts, 0)
            self.assertTrue(outcome.final_page_observed)
            self.assertTrue(outcome.control_transport_was_invoked)
            self.assertFalse(outcome.record_transport_was_invoked)
            self.assertEqual(outcome.global_completeness, "UNKNOWN")
            self.assertFalse(outcome.absence_is_deletion_evidence)
            self.assertFalse(outcome.retries_performed)
            self.assertFalse(outcome.parallel_execution)
            self.assertFalse(outcome.background_execution)
            self.assertFalse(outcome.proofs_verified)
            self.assertFalse(outcome.establishes_truth)
            self.assertFalse(outcome.establishes_peer_trust)
            self.assertFalse(outcome.establishes_authorization)
            self.assertFalse(outcome.creates_agreement)
            self.assertFalse(outcome.authorizes_side_effects)
            self.assertEqual(provider_calls, [(1, ()), (2, ()), (3, ())])
            self.assertEqual([call[1] for call in transport.calls], [
                control_target(1).endpoint,
                control_target(2).endpoint,
                control_target(3).endpoint,
            ])
            self.assertNotIn("cursor", transport.calls[0][0].envelope[3])
            self.assertEqual(transport.calls[1][0].envelope[3]["cursor"], b"page-2")
            self.assertEqual(transport.calls[2][0].envelope[3]["cursor"], b"page-3")
        finally:
            runtime.close()

    def test_final_page_never_invokes_continuation_planner(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=None),))
        runtime, service, planner, hydrator, orchestrator = self.stack(transport)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with patch.object(planner, "plan", side_effect=AssertionError("planner must not run")):
                outcome = orchestrator.synchronize(initial_request, prepared, (control_target(1),))
            self.assertEqual(outcome.disposition, SYNC_FINAL_PAGE_ACCEPTED)
            self.assertEqual(outcome.continuations_planned, 0)
        finally:
            runtime.close()

    def test_truncated_page_stops_at_page_limit_without_planning_or_second_send(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=b"page-2"),))
        limits = FederationSynchronizationLimits(max_pages=1, max_total_records=4, total_timeout_seconds=30)
        runtime, service, planner, hydrator, orchestrator = self.stack(transport, limits=limits)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with patch.object(planner, "plan", side_effect=AssertionError("planner must not run")):
                outcome = orchestrator.synchronize(initial_request, prepared, (control_target(1),))
            self.assertEqual(outcome.disposition, SYNC_STOPPED_PAGE_LIMIT)
            self.assertEqual(outcome.pages_accepted, 1)
            self.assertEqual(outcome.control_exchanges, 1)
            self.assertEqual(outcome.continuations_planned, 0)
            self.assertFalse(outcome.final_page_observed)
        finally:
            runtime.close()

    def test_truncated_page_stops_when_no_next_explicit_control_target_exists(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=b"page-2"),))
        runtime, service, planner, hydrator, orchestrator = self.stack(transport)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with patch.object(planner, "plan", side_effect=AssertionError("planner must not run")):
                outcome = orchestrator.synchronize(initial_request, prepared, (control_target(1),))
            self.assertEqual(outcome.disposition, SYNC_STOPPED_CONTROL_TARGET_LIMIT)
            self.assertEqual(outcome.control_exchanges, 1)
            self.assertEqual(outcome.continuations_planned, 0)
        finally:
            runtime.close()

    def test_time_budget_stops_after_accepted_truncated_page_before_planning(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=b"page-2"),))
        clock = SequenceClock([0.0, 0.0, 0.0, 0.0, 0.0, 121.0])
        runtime, service, planner, hydrator, orchestrator = self.stack(transport, clock=clock)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with patch.object(planner, "plan", side_effect=AssertionError("planner must not run")):
                outcome = orchestrator.synchronize(
                    initial_request,
                    prepared,
                    (control_target(1), control_target(2)),
                )
            self.assertEqual(outcome.disposition, SYNC_STOPPED_TIME_LIMIT)
            self.assertEqual(outcome.pages_accepted, 1)
            self.assertEqual(outcome.control_exchanges, 1)
        finally:
            runtime.close()

    def test_repeated_opaque_cursor_is_rejected_before_planning_or_second_send(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=b"page-2"),))
        runtime, service, planner, hydrator, orchestrator = self.stack(transport)
        try:
            initial_request = request(cursor=b"page-2")
            prepared = service.prepare(initial_request)
            with patch.object(planner, "plan", side_effect=AssertionError("planner must not run")):
                with self.assertRaises(FederationSynchronizationError) as caught:
                    orchestrator.synchronize(
                        initial_request,
                        prepared,
                        (control_target(1), control_target(2)),
                    )
            self.assertEqual(caught.exception.code, "CURSOR_REPLAY_DETECTED")
            self.assertEqual(len(transport.calls), 1)
        finally:
            runtime.close()

    def test_mutated_initial_request_is_rejected_before_control_transport(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=None),))
        runtime, service, planner, hydrator, orchestrator = self.stack(transport)
        try:
            original = request()
            prepared = service.prepare(original)
            original["page_size"] = 3
            with self.assertRaises(FederationSynchronizationError) as caught:
                orchestrator.synchronize(original, prepared, (control_target(1),))
            self.assertEqual(caught.exception.code, "INITIAL_REQUEST_PREPARED_MISMATCH")
            self.assertEqual(transport.calls, [])
        finally:
            runtime.close()

    def test_hostile_control_result_cannot_promote_authorization(self):
        class HostileTransport(SequencedControlTransport):
            def exchange(self, prepared, *, endpoint, authorization):
                result = super().exchange(prepared, endpoint=endpoint, authorization=authorization)
                return HttpsFederationExchangeResult(
                    response_envelope=result.response_envelope,
                    http_status=200,
                    response_body_bytes=100,
                    selected_address="203.0.113.10",
                    tls_server_hostname="peer.example",
                    establishes_authorization=True,
                )

        transport = HostileTransport((page_envelope(next_cursor=None),))
        provider_called = False

        def provider(record_ids, *, page_number):
            nonlocal provider_called
            provider_called = True
            return ()

        runtime, service, planner, hydrator, orchestrator = self.stack(
            transport,
            target_provider=provider,
        )
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with self.assertRaises(FederationSynchronizationError) as caught:
                orchestrator.synchronize(initial_request, prepared, (control_target(1),))
            self.assertEqual(caught.exception.code, "CONTROL_AUTHORITY_INVARIANT")
            self.assertFalse(provider_called)
        finally:
            runtime.close()

    def test_record_budget_overflow_fails_before_target_provider_or_hydrator(self):
        transport = SequencedControlTransport((
            page_envelope(
                next_cursor=None,
                record_ids=(VALID_RECORD_ID_1, VALID_RECORD_ID_2),
            ),
        ))
        provider_called = False
        limits = FederationSynchronizationLimits(max_pages=2, max_total_records=1, total_timeout_seconds=30)

        def provider(record_ids, *, page_number):
            nonlocal provider_called
            provider_called = True
            return ()

        runtime, service, planner, hydrator, orchestrator = self.stack(
            transport,
            target_provider=provider,
            limits=limits,
        )
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with patch.object(hydrator, "hydrate_and_accept", side_effect=AssertionError("hydrator must not run")):
                with self.assertRaises(FederationSynchronizationError) as caught:
                    orchestrator.synchronize(initial_request, prepared, (control_target(1),))
            self.assertEqual(caught.exception.code, "TOTAL_RECORD_LIMIT_EXCEEDED")
            self.assertFalse(provider_called)
        finally:
            runtime.close()

    def test_hydration_failure_never_plans_or_sends_continuation(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=b"page-2"),))
        runtime, service, planner, hydrator, orchestrator = self.stack(transport)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            with patch.object(hydrator, "hydrate_and_accept", side_effect=RuntimeError("boom")):
                with patch.object(planner, "plan", side_effect=AssertionError("planner must not run")):
                    with self.assertRaises(FederationSynchronizationError) as caught:
                        orchestrator.synchronize(
                            initial_request,
                            prepared,
                            (control_target(1), control_target(2)),
                        )
            self.assertEqual(caught.exception.code, "PAGE_HYDRATION_FAILED")
            self.assertEqual(len(transport.calls), 1)
        finally:
            runtime.close()

    def test_truncated_page_rejects_hostile_no_continuation_planner_result(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=b"page-2"),))
        runtime, service, planner, hydrator, orchestrator = self.stack(transport)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)
            hostile = ContinuationPlanOutcome(
                disposition=NO_CONTINUATION,
                prepared_exchange=None,
                prior_page_truncated=False,
            )
            with patch.object(planner, "plan", return_value=hostile):
                with self.assertRaises(FederationSynchronizationError) as caught:
                    orchestrator.synchronize(
                        initial_request,
                        prepared,
                        (control_target(1), control_target(2)),
                    )
            self.assertEqual(caught.exception.code, "CONTINUATION_INCONSISTENCY")
            self.assertEqual(len(transport.calls), 1)
        finally:
            runtime.close()

    def test_limit_types_and_hard_maxima_fail_closed(self):
        for kwargs in (
            {"max_pages": 0},
            {"max_pages": True},
            {"max_pages": MAX_SYNCHRONIZATION_PAGES + 1},
            {"max_total_records": 0},
            {"max_total_records": True},
            {"max_total_records": MAX_SYNCHRONIZATION_RECORDS + 1},
            {"total_timeout_seconds": 0},
            {"total_timeout_seconds": True},
            {"total_timeout_seconds": float("inf")},
            {"total_timeout_seconds": MAX_SYNCHRONIZATION_TIMEOUT_SECONDS + 1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    FederationSynchronizationLimits(**kwargs)

    def test_control_target_iterable_is_bounded_before_any_exchange(self):
        transport = SequencedControlTransport((page_envelope(next_cursor=None),))
        limits = FederationSynchronizationLimits(max_pages=2, max_total_records=4, total_timeout_seconds=30)
        runtime, service, planner, hydrator, orchestrator = self.stack(transport, limits=limits)
        try:
            initial_request = request()
            prepared = service.prepare(initial_request)

            def too_many_targets():
                for index in range(1, 1000):
                    yield control_target(index)

            with self.assertRaises(FederationSynchronizationError) as caught:
                orchestrator.synchronize(initial_request, prepared, too_many_targets())
            self.assertEqual(caught.exception.code, "CONTROL_TARGET_LIMIT_EXCEEDED")
            self.assertEqual(transport.calls, [])
        finally:
            runtime.close()

    def test_m31_source_contains_no_second_network_or_background_stack(self):
        path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "runtime" / "synchronization.py"
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
