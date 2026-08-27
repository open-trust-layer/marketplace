from __future__ import annotations

import ast
import unittest
from pathlib import Path

from olp import RecordV1, record_identity_text

from marketplace.reference import (
    CORE_PROFILE,
    TYPE_INTENT,
    evaluate_discovery,
    evaluate_match,
    federation_v1,
    validate_market_record,
)
from marketplace.reference.record_retrieval_v1 import verified_retrieved_market_record_value
from marketplace.runtime import (
    FederationOperationProfile,
    compose_offline_federation_service,
    create_in_memory_runtime,
)
from marketplace.runtime.network_policy import (
    FederationEgressPolicy,
    authorize_federation_endpoint,
)
from marketplace.runtime.page_hydration import (
    DEFAULT_MAX_HYDRATED_RECORDS,
    DEFAULT_PAGE_HYDRATION_TIMEOUT_SECONDS,
    MAX_HYDRATED_RECORDS,
    MAX_PAGE_HYDRATION_TIMEOUT_SECONDS,
    BoundedFederationPageHydrator,
    FederationPageHydrationError,
    PageHydrationLimits,
    RecordHydrationTarget,
)
from marketplace.runtime.record_retrieval import (
    RECORD_RETRIEVAL_OPERATION,
    RetrievedRecordTransportResult,
)

SOURCE = "urn:example:source:m28"
HOST = "records.example.com"
ACTION = "https://example.test/actions/request"


def record_mapping(index: int) -> dict[str, object]:
    return {
        "envelope_version": 1,
        "type": TYPE_INTENT,
        "content": {
            "version": 1,
            "issuer": {"principal": f"did:example:m28:{index}"},
            "subjects": [{"uri": f"urn:example:m28:{index}"}],
            "action": {"id": ACTION},
            "terms": {},
        },
        "profiles": [CORE_PROFILE],
    }


def record(index: int) -> RecordV1:
    return RecordV1.from_mapping(record_mapping(index))


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def request(page_size: int = 32) -> dict[str, object]:
    return {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SNAPSHOT,
        "scope": scope(),
        "required_capabilities": [federation_v1.CAP_SNAPSHOT],
        "page_size": page_size,
    }


def result_payload(records: list[RecordV1], *, next_cursor: bytes | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SNAPSHOT,
        "scope_fingerprint": federation_v1.scope_fingerprint(scope()),
        "record_ids": sorted(record_identity_text(item) for item in records),
        "source_completeness": "PARTIAL_SOURCE",
        "page_truncated": next_cursor is not None,
    }
    if next_cursor is not None:
        payload["next_cursor"] = next_cursor
    return payload


def envelope(records: list[RecordV1], *, next_cursor: bytes | None = None):
    return federation_v1.make_transport_envelope(
        federation_v1.MSG_SNAPSHOT_RESULT,
        result_payload(records, next_cursor=next_cursor),
    )


class FakeRetriever:
    def __init__(self, mappings: dict[str, dict[str, object]]) -> None:
        self.mappings = mappings
        self.events: list[tuple[str, str]] = []
        self.fail_preflight_for: str | None = None
        self.fail_retrieve_for: str | None = None
        self.result_overrides: dict[str, dict[str, object]] = {}
        self.on_retrieve = None

    def preflight(self, *, endpoint, authorization, expected_record_identity):
        self.events.append(("preflight", expected_record_identity))
        if expected_record_identity == self.fail_preflight_for:
            raise RuntimeError("synthetic preflight failure")

    def retrieve(self, *, endpoint, authorization, expected_record_identity):
        self.events.append(("retrieve", expected_record_identity))
        if self.on_retrieve is not None:
            self.on_retrieve(expected_record_identity)
        if expected_record_identity == self.fail_retrieve_for:
            raise RuntimeError("synthetic retrieval failure")
        values = {
            "expected_record_identity": expected_record_identity,
            "response_envelope": (
                "OLP-TRANSPORT",
                1,
                "record",
                self.mappings[expected_record_identity],
            ),
            "http_status": 200,
            "response_body_bytes": 128,
            "selected_address": "1.1.1.1",
            "tls_server_hostname": HOST,
        }
        values.update(self.result_overrides.get(expected_record_identity, {}))
        return RetrievedRecordTransportResult(**values)


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class PageHydrationTests(unittest.TestCase):
    def runtime_service(self):
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=128,
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
                    federation_v1.OP_SNAPSHOT,
                    federation_v1.MSG_SNAPSHOT_REQUEST,
                    federation_v1.MSG_SNAPSHOT_RESULT,
                ),
            ),
        )
        return runtime, service

    def policy(self) -> FederationEgressPolicy:
        return FederationEgressPolicy(
            policy_id="https://open-trust-layer.github.io/marketplace/policy/m28-tests-v1",
            policy_version=1,
            allowed_hosts=(HOST,),
        )

    def target(self, item: RecordV1) -> RecordHydrationTarget:
        record_id = record_identity_text(item)
        endpoint = f"https://{HOST}/olp/v1/records/{record_id}"
        authorization = authorize_federation_endpoint(
            endpoint=endpoint,
            allowed_operations=(RECORD_RETRIEVAL_OPERATION,),
            authorization_id=f"m28-{record_id[-8:]}",
            issued_at_epoch=1_000,
            expires_at_epoch=1_120,
            policy=self.policy(),
        )
        return RecordHydrationTarget(record_id, endpoint, authorization)

    def hydrator(self, service, retriever, *, limits=None, clock=None, verifier=verified_retrieved_market_record_value):
        return BoundedFederationPageHydrator(
            federation_service=service,
            record_retriever=retriever,
            verify_record_value=verifier,
            limits=limits,
            monotonic_clock=clock or (lambda: 0.0),
        )

    def test_default_and_hard_limits_are_explicit(self):
        limits = PageHydrationLimits()
        self.assertEqual(limits.max_records, DEFAULT_MAX_HYDRATED_RECORDS)
        self.assertEqual(limits.max_records, 16)
        self.assertEqual(limits.total_timeout_seconds, DEFAULT_PAGE_HYDRATION_TIMEOUT_SECONDS)
        self.assertEqual(limits.total_timeout_seconds, 60.0)
        with self.assertRaises(ValueError):
            PageHydrationLimits(max_records=MAX_HYDRATED_RECORDS + 1)
        with self.assertRaises(ValueError):
            PageHydrationLimits(total_timeout_seconds=MAX_PAGE_HYDRATION_TIMEOUT_SECONDS + 0.001)
        with self.assertRaises(ValueError):
            PageHydrationLimits(max_records=0)
        with self.assertRaises(ValueError):
            PageHydrationLimits(total_timeout_seconds=0)

    def test_oversized_validated_page_fails_before_target_preflight_or_retrieval(self):
        runtime, service = self.runtime_service()
        try:
            records = [record(index) for index in range(3)]
            mappings = {record_identity_text(item): record_mapping(index) for index, item in enumerate(records)}
            retriever = FakeRetriever(mappings)
            hydrator = self.hydrator(service, retriever, limits=PageHydrationLimits(max_records=2))
            prepared = service.prepare(request(page_size=3))
            with self.assertRaises(FederationPageHydrationError) as caught:
                hydrator.hydrate_and_accept(prepared, envelope(records), [self.target(item) for item in records])
            self.assertEqual(caught.exception.code, "HYDRATION_PAGE_LIMIT_EXCEEDED")
            self.assertEqual(retriever.events, [])
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_target_set_mismatch_fails_before_any_preflight_or_retrieval(self):
        runtime, service = self.runtime_service()
        try:
            left, right = record(1), record(2)
            mappings = {
                record_identity_text(left): record_mapping(1),
                record_identity_text(right): record_mapping(2),
            }
            retriever = FakeRetriever(mappings)
            hydrator = self.hydrator(service, retriever)
            prepared = service.prepare(request())
            with self.assertRaises(FederationPageHydrationError) as caught:
                hydrator.hydrate_and_accept(prepared, envelope([left, right]), [self.target(left)])
            self.assertEqual(caught.exception.code, "HYDRATION_TARGET_SET_MISMATCH")
            self.assertEqual(retriever.events, [])
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_every_target_preflights_before_first_retrieval(self):
        runtime, service = self.runtime_service()
        try:
            records = [record(1), record(2)]
            mappings = {record_identity_text(item): record_mapping(index) for index, item in zip((1, 2), records)}
            retriever = FakeRetriever(mappings)
            canonical_ids = sorted(mappings)
            retriever.fail_preflight_for = canonical_ids[1]
            hydrator = self.hydrator(service, retriever)
            prepared = service.prepare(request())
            with self.assertRaises(FederationPageHydrationError) as caught:
                hydrator.hydrate_and_accept(prepared, envelope(records), [self.target(item) for item in reversed(records)])
            self.assertEqual(caught.exception.code, "HYDRATION_TARGET_PREFLIGHT_FAILED")
            self.assertEqual(
                retriever.events,
                [("preflight", canonical_ids[0]), ("preflight", canonical_ids[1])],
            )
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_success_is_sequential_canonical_and_stores_only_after_all_verify(self):
        runtime, service = self.runtime_service()
        try:
            records = [record(3), record(1), record(2)]
            mappings = {
                record_identity_text(item): record_mapping(index)
                for index, item in zip((3, 1, 2), records)
            }
            retriever = FakeRetriever(mappings)
            hydrator = self.hydrator(service, retriever)
            prepared = service.prepare(request())
            outcome = hydrator.hydrate_and_accept(
                prepared,
                envelope(records),
                [self.target(item) for item in records],
            )
            canonical_ids = tuple(sorted(mappings))
            self.assertEqual(
                retriever.events,
                [("preflight", item) for item in canonical_ids]
                + [("retrieve", item) for item in canonical_ids],
            )
            self.assertEqual(outcome.hydrated_record_ids, canonical_ids)
            self.assertEqual(outcome.page_outcome.record_ids, canonical_ids)
            self.assertEqual(outcome.page_outcome.stored_record_ids, canonical_ids)
            self.assertEqual(outcome.retrieval_attempts, 3)
            self.assertTrue(outcome.record_transport_was_invoked)
            self.assertEqual(outcome.retries_performed, 0)
            self.assertFalse(outcome.parallel_retrieval)
            self.assertFalse(outcome.cursor_automatically_followed)
            self.assertFalse(outcome.proofs_verified)
            self.assertFalse(outcome.establishes_truth)
            self.assertFalse(outcome.establishes_authorization)
            self.assertFalse(outcome.creates_agreement)
            self.assertFalse(outcome.page_outcome.transport_was_invoked)
            self.assertEqual(len(runtime.repository), 3)
        finally:
            runtime.close()

    def test_hostile_transport_result_fails_before_verifier_and_storage(self):
        runtime, service = self.runtime_service()
        try:
            item = record(1)
            record_id = record_identity_text(item)
            retriever = FakeRetriever({record_id: record_mapping(1)})
            retriever.result_overrides[record_id] = {"identity_verified": True}
            verifier_calls = 0

            def verifier(*args, **kwargs):
                nonlocal verifier_calls
                verifier_calls += 1
                return item

            hydrator = self.hydrator(service, retriever, verifier=verifier)
            prepared = service.prepare(request())
            with self.assertRaises(FederationPageHydrationError) as caught:
                hydrator.hydrate_and_accept(prepared, envelope([item]), [self.target(item)])
            self.assertEqual(caught.exception.code, "RETRIEVAL_AUTHORITY_INVARIANT")
            self.assertEqual(verifier_calls, 0)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_verification_failure_after_completed_gets_leaves_repository_empty(self):
        runtime, service = self.runtime_service()
        try:
            records = [record(1), record(2)]
            mappings = {record_identity_text(item): record_mapping(index) for index, item in zip((1, 2), records)}
            failing_id = sorted(mappings)[1]
            retriever = FakeRetriever(mappings)

            def verifier(envelope_value, *, expected_record_identity):
                if expected_record_identity == failing_id:
                    raise ValueError("synthetic verifier rejection")
                return verified_retrieved_market_record_value(
                    envelope_value,
                    expected_record_identity=expected_record_identity,
                )

            hydrator = self.hydrator(service, retriever, verifier=verifier)
            prepared = service.prepare(request())
            with self.assertRaises(FederationPageHydrationError) as caught:
                hydrator.hydrate_and_accept(prepared, envelope(records), [self.target(item) for item in records])
            self.assertEqual(caught.exception.code, "HYDRATION_RECORD_VERIFICATION_FAILED")
            self.assertEqual(
                [event for event in retriever.events if event[0] == "retrieve"],
                [("retrieve", item) for item in sorted(mappings)],
            )
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_page_budget_stops_new_gets_and_never_partially_stores(self):
        runtime, service = self.runtime_service()
        try:
            records = [record(1), record(2), record(3)]
            mappings = {
                record_identity_text(item): record_mapping(index)
                for index, item in zip((1, 2, 3), records)
            }
            clock = ManualClock()
            retriever = FakeRetriever(mappings)
            retriever.on_retrieve = lambda record_id: setattr(clock, "value", clock.value + 35.0)
            hydrator = self.hydrator(
                service,
                retriever,
                limits=PageHydrationLimits(total_timeout_seconds=60.0),
                clock=clock,
            )
            prepared = service.prepare(request())
            with self.assertRaises(FederationPageHydrationError) as caught:
                hydrator.hydrate_and_accept(prepared, envelope(records), [self.target(item) for item in records])
            self.assertEqual(caught.exception.code, "PAGE_HYDRATION_TIMEOUT")
            retrieves = [event for event in retriever.events if event[0] == "retrieve"]
            self.assertEqual(len(retrieves), 2)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_empty_valid_page_performs_no_record_transport(self):
        runtime, service = self.runtime_service()
        try:
            retriever = FakeRetriever({})
            hydrator = self.hydrator(service, retriever)
            prepared = service.prepare(request())
            outcome = hydrator.hydrate_and_accept(prepared, envelope([]), [])
            self.assertEqual(retriever.events, [])
            self.assertEqual(outcome.hydrated_record_ids, ())
            self.assertEqual(outcome.retrieval_attempts, 0)
            self.assertFalse(outcome.record_transport_was_invoked)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_m28_runtime_has_no_parallel_or_concrete_network_client_surface(self):
        path = Path(__file__).resolve().parents[1] / "src/marketplace/runtime/page_hydration.py"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        imported: set[str] = set()
        direct_calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                direct_calls.add(node.func.id)
        for forbidden in (
            "socket",
            "ssl",
            "urllib.request",
            "http.client",
            "requests",
            "httpx",
            "aiohttp",
            "threading",
            "asyncio",
            "concurrent.futures",
            "subprocess",
            "os",
        ):
            self.assertNotIn(forbidden, imported)
        for forbidden_call in ("eval", "exec", "compile", "open", "__import__"):
            self.assertNotIn(forbidden_call, direct_calls)


if __name__ == "__main__":
    unittest.main()
