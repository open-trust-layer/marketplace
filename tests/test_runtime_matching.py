from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Callable

from olp import RecordV1, record_identity_text

from marketplace.runtime import (
    InMemoryEphemeralRecordRepository,
    InvalidLocalRecordIdentityError,
    InvalidMatchEvaluatorResult,
    LocalMatchService,
    LocalRecordNotFoundError,
)
from marketplace_matching_v1 import evaluate_match
from marketplace_record_v1 import CORE_PROFILE, TYPE_INTENT


class FakeExpiryHandle:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


@dataclass
class ScheduledExpiry:
    delay_seconds: float
    callback: Callable[[], None]
    handle: FakeExpiryHandle


class FakeExpiryScheduler:
    def __init__(self) -> None:
        self.events: list[ScheduledExpiry] = []

    def schedule(self, delay_seconds: float, callback: Callable[[], None]) -> FakeExpiryHandle:
        handle = FakeExpiryHandle()
        self.events.append(ScheduledExpiry(delay_seconds, callback, handle))
        return handle


class FakeExactSource:
    def __init__(self, records=None):
        self.records = dict(records or {})
        self.calls: list[str] = []

    def get(self, record_id: str):
        self.calls.append(record_id)
        return self.records.get(record_id)


def intent(
    *,
    principal: str,
    subject: str,
    action: str,
    constraint: dict | None = None,
    critical_uri: str | None = None,
) -> RecordV1:
    content = {
        "version": 1,
        "issuer": {"principal": principal},
        "subjects": [{"uri": subject}],
        "action": {"id": action},
        "terms": {},
    }
    if constraint is not None:
        content["constraints"] = [constraint]
    if critical_uri is not None:
        content["extensions"] = {critical_uri: True}
        content["critical"] = [critical_uri]
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": content,
            "profiles": [CORE_PROFILE],
        }
    )


class RuntimeMatchingTests(unittest.TestCase):
    def test_invalid_identity_input_is_rejected_before_source_or_evaluator(self):
        source = FakeExactSource()
        evaluator_calls = 0

        def evaluator(*args, **kwargs):
            nonlocal evaluator_calls
            evaluator_calls += 1
            return {}

        service = LocalMatchService(record_source=source, evaluate_match=evaluator)
        with self.assertRaises(InvalidLocalRecordIdentityError) as raised:
            service.evaluate(
                "",
                "r1_right",
                method="https://example.test/method/match",
                base_status="SATISFIED",
                observations=(),
                evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
            )
        self.assertEqual(raised.exception.code, "INVALID_LOCAL_RECORD_IDENTITY")
        self.assertEqual(source.calls, [])
        self.assertEqual(evaluator_calls, 0)

    def test_missing_left_is_explicit_local_not_found_without_evaluator(self):
        source = FakeExactSource({"r1_right": {"side": "right"}})
        evaluator_calls = 0

        def evaluator(*args, **kwargs):
            nonlocal evaluator_calls
            evaluator_calls += 1
            return {}

        service = LocalMatchService(record_source=source, evaluate_match=evaluator)
        with self.assertRaises(LocalRecordNotFoundError) as raised:
            service.evaluate(
                "r1_missing",
                "r1_right",
                method="https://example.test/method/match",
                base_status="SATISFIED",
                observations=(),
                evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
            )
        self.assertEqual(raised.exception.code, "LOCAL_RECORD_NOT_FOUND")
        self.assertEqual(raised.exception.side, "left")
        self.assertEqual(source.calls, ["r1_missing"])
        self.assertEqual(evaluator_calls, 0)

    def test_missing_right_is_explicit_local_not_found_without_fallback(self):
        source = FakeExactSource({"r1_left": {"side": "left"}})
        evaluator_calls = 0

        def evaluator(*args, **kwargs):
            nonlocal evaluator_calls
            evaluator_calls += 1
            return {}

        service = LocalMatchService(record_source=source, evaluate_match=evaluator)
        with self.assertRaises(LocalRecordNotFoundError) as raised:
            service.evaluate(
                "r1_left",
                "r1_missing",
                method="https://example.test/method/match",
                base_status="SATISFIED",
                observations=(),
                evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
            )
        self.assertEqual(raised.exception.side, "right")
        self.assertEqual(source.calls, ["r1_left", "r1_missing"])
        self.assertEqual(evaluator_calls, 0)

    def test_exact_repository_reads_refresh_only_referenced_records(self):
        scheduler = FakeExpiryScheduler()
        repository = InMemoryEphemeralRecordRepository(scheduler=scheduler, max_entries=3)
        repository.put("r1_left", {"side": "left"})
        repository.put("r1_right", {"side": "right"})
        repository.put("r1_other", {"side": "other"})

        service = LocalMatchService(
            record_source=repository,
            evaluate_match=lambda *args, **kwargs: {"conclusion": "TEST"},
        )
        result = service.evaluate(
            "r1_left",
            "r1_right",
            method="https://example.test/method/match",
            base_status="SATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        )

        self.assertEqual(result["conclusion"], "TEST")
        self.assertTrue(scheduler.events[0].handle.cancelled)
        self.assertTrue(scheduler.events[1].handle.cancelled)
        self.assertFalse(scheduler.events[2].handle.cancelled)
        self.assertEqual(len(scheduler.events), 5)

    def test_same_identity_is_read_once_and_reused_for_both_sides(self):
        source = FakeExactSource({"r1_same": {"record": "same"}})
        observed = {}

        def evaluator(left, right, **kwargs):
            observed["same_object"] = left is right
            return {"same": left is right}

        service = LocalMatchService(record_source=source, evaluate_match=evaluator)
        result = service.evaluate(
            "r1_same",
            "r1_same",
            method="https://example.test/method/match",
            base_status="SATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        )

        self.assertTrue(result["same"])
        self.assertTrue(observed["same_object"])
        self.assertEqual(source.calls, ["r1_same"])

    def test_actual_m5_compatible_result_never_creates_agreement_or_truth(self):
        left = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/buy",
        )
        right = intent(
            principal="did:example:bob",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        source = FakeExactSource(
            {record_identity_text(left): left, record_identity_text(right): right}
        )
        service = LocalMatchService(record_source=source, evaluate_match=evaluate_match)

        result = service.evaluate(
            record_identity_text(left),
            record_identity_text(right),
            method="https://example.test/method/exact-v1",
            base_status="SATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        )

        self.assertEqual(result["conclusion"], "COMPATIBLE_UNDER_METHOD")
        self.assertFalse(result["protocol_truth"])
        self.assertFalse(result["creates_agreement"])

    def test_actual_m5_incompatible_result_is_method_relative(self):
        left = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/buy",
        )
        right = intent(
            principal="did:example:bob",
            subject="urn:example:item:2",
            action="https://example.test/actions/sell",
        )
        source = FakeExactSource(
            {record_identity_text(left): left, record_identity_text(right): right}
        )
        service = LocalMatchService(record_source=source, evaluate_match=evaluate_match)

        result = service.evaluate(
            record_identity_text(left),
            record_identity_text(right),
            method="https://example.test/method/exact-v1",
            base_status="UNSATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        )

        self.assertEqual(result["conclusion"], "INCOMPATIBLE_UNDER_METHOD")
        self.assertFalse(result["protocol_truth"])
        self.assertFalse(result["creates_agreement"])

    def test_actual_m5_unknown_critical_semantics_remain_indeterminate(self):
        critical = "https://example.test/ext/match-context"
        left = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/buy",
            critical_uri=critical,
        )
        right = intent(
            principal="did:example:bob",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        source = FakeExactSource(
            {record_identity_text(left): left, record_identity_text(right): right}
        )
        service = LocalMatchService(record_source=source, evaluate_match=evaluate_match)

        result = service.evaluate(
            record_identity_text(left),
            record_identity_text(right),
            method="https://example.test/method/exact-v1",
            base_status="SATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
            understood_critical=(),
        )

        self.assertEqual(result["conclusion"], "INDETERMINATE")
        self.assertEqual(result["unsupported_critical_semantics"], [critical])
        self.assertFalse(result["creates_agreement"])

    def test_service_returns_evaluator_mapping_without_reinterpretation(self):
        source = FakeExactSource({"r1_left": {"left": 1}, "r1_right": {"right": 1}})
        expected = {
            "conclusion": "METHOD_SPECIFIC_RESULT",
            "protocol_truth": False,
            "creates_agreement": False,
            "extra": {"preserve": True},
        }
        observed = {}

        def evaluator(left, right, **kwargs):
            observed["left"] = left
            observed["right"] = right
            observed.update(kwargs)
            return expected

        service = LocalMatchService(record_source=source, evaluate_match=evaluator)
        result = service.evaluate(
            "r1_left",
            "r1_right",
            method="https://example.test/method/custom",
            base_status="UNKNOWN",
            observations=({"example": "opaque-to-runtime"},),
            evidence_completeness="UNKNOWN",
            understood_critical=("https://example.test/ext/known",),
        )

        self.assertIs(result, expected)
        self.assertEqual(observed["method"], "https://example.test/method/custom")
        self.assertEqual(observed["base_status"], "UNKNOWN")
        self.assertEqual(observed["evidence_completeness"], "UNKNOWN")

    def test_nonmapping_evaluator_result_is_rejected(self):
        source = FakeExactSource({"r1_left": {}, "r1_right": {}})
        service = LocalMatchService(
            record_source=source,
            evaluate_match=lambda *args, **kwargs: [],
        )

        with self.assertRaises(InvalidMatchEvaluatorResult) as raised:
            service.evaluate(
                "r1_left",
                "r1_right",
                method="https://example.test/method/custom",
                base_status="UNKNOWN",
                observations=(),
                evidence_completeness="UNKNOWN",
            )
        self.assertEqual(raised.exception.code, "INVALID_MATCH_EVALUATOR_RESULT")


if __name__ == "__main__":
    unittest.main()
