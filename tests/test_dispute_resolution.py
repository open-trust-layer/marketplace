from __future__ import annotations

import unittest

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref, relationship_record

from marketplace_dispute_resolution_v1 import (
    METHOD_CORE,
    OBS_REJECT,
    OBS_UPHOLD,
    DisputeEvidence,
    MarketplaceDisputeResolutionError,
    ResolutionObservation,
    evaluate_dispute_resolution,
    evaluate_resolution_reuse,
    validate_dispute_resolution_result,
)

SOURCE = "https://source.example/a"
AUTHORITY = "https://authority.example/a"
PURPOSE = "https://example.test/purpose/review"
CRITICAL = "https://example.test/critical/procedure"


def record(kind: str, value: str) -> RecordV1:
    return RecordV1(
        envelope_version=1,
        type=f"https://example.test/record/{kind}",
        content={"https://example.test/value": value},
    )


class DisputeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.target = record("claim", "target")
        self.challenger = record("challenge", "challenger")
        self.dispute = relationship_record(
            "disputes",
            subject=record_ref(self.challenger),
            objects=[record_ref(self.target)],
        )
        self.target_id = record_identity_text(self.target)
        self.dispute_id = record_identity_text(self.dispute)
        self.request = {
            "version": 1,
            "method": METHOD_CORE,
            "purpose": PURPOSE,
            "challenged_record_ids": [self.target_id],
            "context": {},
            "accepted_sources": [SOURCE],
            "accepted_authorities": [AUTHORITY],
            "understood_critical": [],
            "max_disputes": 10,
            "max_resolutions": 10,
        }
        self.dispute_evidence = DisputeEvidence(
            self.dispute, SOURCE, AUTHORITY,
            "VERIFIED", "ACCEPTED", "ACCEPTED", "ACCEPTABLE",
        )

    def resolution(self, outcome: str, value: str = "r") -> ResolutionObservation:
        resolution_record = record("resolution", value)
        return ResolutionObservation(
            record_identity_text(resolution_record),
            (self.dispute_id,),
            (self.target_id,),
            outcome,
            SOURCE,
            AUTHORITY,
            "VERIFIED",
            "ACCEPTED",
            "ACCEPTED",
            "ACCEPTABLE",
        )

    def test_resolution_never_authorizes_protected_side_effect(self):
        result = evaluate_dispute_resolution(
            self.request,
            (self.dispute_evidence,),
            (self.resolution(OBS_UPHOLD),),
        )
        self.assertEqual(result["outcome"], "UPHOLD_CHALLENGE_UNDER_METHOD")
        self.assertFalse(result["protected_side_effect_authorized"])
        self.assertFalse(result["remedy_or_side_effect_implied"])

    def test_competing_uphold_and_reject_are_preserved_as_conflict(self):
        result = evaluate_dispute_resolution(
            self.request,
            (self.dispute_evidence,),
            (self.resolution(OBS_UPHOLD, "u"), self.resolution(OBS_REJECT, "r")),
        )
        self.assertEqual(result["outcome"], "CONFLICTING_RESOLUTION_EVIDENCE")
        self.assertEqual(set(result["admissible_outcomes"]), {"UPHOLD", "REJECT"})

    def test_admissible_dispute_without_resolution_requires_more_evidence(self):
        result = evaluate_dispute_resolution(self.request, (self.dispute_evidence,), ())
        self.assertEqual(result["outcome"], "REQUIRE_ADDITIONAL_EVIDENCE")

    def test_unknown_critical_dispute_is_indeterminate(self):
        critical_dispute = relationship_record(
            "disputes",
            subject=record_ref(self.challenger),
            objects=[record_ref(self.target)],
            qualifiers={CRITICAL: "required"},
            critical=[CRITICAL],
        )
        evidence = DisputeEvidence(
            critical_dispute, SOURCE, AUTHORITY,
            "VERIFIED", "ACCEPTED", "ACCEPTED", "ACCEPTABLE",
        )
        result = evaluate_dispute_resolution(self.request, (evidence,), ())
        self.assertEqual(result["outcome"], "INDETERMINATE")

    def test_resolution_target_must_match_referenced_dispute_targets(self):
        target_b = record("claim", "target-b")
        target_b_id = record_identity_text(target_b)
        request = dict(self.request)
        request["challenged_record_ids"] = sorted((self.target_id, target_b_id))
        resolution_record = record("resolution", "wrong-target-binding")
        resolution = ResolutionObservation(
            record_identity_text(resolution_record),
            (self.dispute_id,),
            (target_b_id,),
            OBS_UPHOLD,
            SOURCE,
            AUTHORITY,
            "VERIFIED",
            "ACCEPTED",
            "ACCEPTED",
            "ACCEPTABLE",
        )
        result = evaluate_dispute_resolution(request, (self.dispute_evidence,), (resolution,))
        self.assertEqual(result["outcome"], "INDETERMINATE")
        self.assertEqual(result["resolution_trace"][0]["state"], "UNRESOLVED")
        self.assertIn("DISPUTE_TARGET_BINDING_MISMATCH", result["resolution_trace"][0]["reasons"])

    def test_result_fingerprint_detects_tampering(self):
        result = evaluate_dispute_resolution(
            self.request,
            (self.dispute_evidence,),
            (self.resolution(OBS_UPHOLD),),
        )
        tampered = dict(result)
        tampered["outcome"] = "REJECT_CHALLENGE_UNDER_METHOD"
        with self.assertRaises(MarketplaceDisputeResolutionError) as caught:
            validate_dispute_resolution_result(tampered)
        self.assertEqual(caught.exception.code, "DISPUTE_RESULT_INTEGRITY_MISMATCH")

    def test_reuse_requires_exact_request_and_evidence_binding(self):
        resolution = self.resolution(OBS_UPHOLD)
        result = evaluate_dispute_resolution(
            self.request,
            (self.dispute_evidence,),
            (resolution,),
        )
        exact = evaluate_resolution_reuse(
            result, self.request, (self.dispute_evidence,), (resolution,)
        )
        self.assertEqual(exact["reuse_status"], "REUSABLE")
        changed_request = dict(self.request)
        changed_request["context"] = {"https://example.test/context/mode": "strict"}
        changed = evaluate_resolution_reuse(
            result, changed_request, (self.dispute_evidence,), (resolution,)
        )
        self.assertEqual(changed["reuse_status"], "NOT_REUSABLE")


if __name__ == "__main__":
    unittest.main()
