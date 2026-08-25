from __future__ import annotations

import unittest
from copy import deepcopy

from marketplace_remedy_workflow_v1 import (
    PROFILE_REMEDY_WORKFLOW,
    MarketplaceRemedyWorkflowError,
    evaluate_remedy_workflow,
    evaluate_remedy_workflow_reuse,
    validate_remedy_workflow_profile,
    validate_remedy_workflow_result,
)

BASE = "https://example.test/remedy"
METHOD = f"{BASE}/method/software-remedy-v1"
DOMAIN = f"{BASE}/domain/software"
PURPOSE = f"{BASE}/purpose/post-dispute-coordination"
CRITICAL = f"{BASE}/critical/human-approval-v1"
RID = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"
SOURCE_FP = "a" * 43


def step(name, *, protected=False, depends_on=(), conflict_group=None, critical=()):
    return {
        "id": f"{BASE}/step/{name}", "action": f"{BASE}/action/{name}",
        "depends_on": sorted(depends_on), "protected": protected,
        "conflict_group": conflict_group, "critical": sorted(critical),
    }


def rule(name, *, required=False, steps=None, critical=()):
    return {
        "id": f"{BASE}/rule/{name}", "trigger": f"{BASE}/trigger/{name}",
        "required": required, "steps": steps or [step(name)], "critical": sorted(critical),
    }


def profile(*, rules=None, critical=()):
    return {
        "version": 1, "profile": PROFILE_REMEDY_WORKFLOW, "method": METHOD,
        "domain": DOMAIN, "purposes": [PURPOSE],
        "rules": rules or [rule("refund", required=True, steps=[step("refund", protected=True)])],
        "critical": sorted(critical),
    }


def request(*, understood=(), context=None):
    return {
        "version": 1, "method": METHOD, "domain": DOMAIN, "purpose": PURPOSE,
        "target_record_ids": [RID], "context": {} if context is None else context,
        "understood_critical": sorted(understood),
    }


def observation(name="refund", state="PRESENT", *, critical=(), fingerprint=SOURCE_FP):
    return {
        "trigger": f"{BASE}/trigger/{name}", "state": state,
        "target_record_id": RID, "source_result_fingerprint": fingerprint,
        "critical": sorted(critical),
    }


class RemedyWorkflowTests(unittest.TestCase):
    def test_protected_refund_is_proposal_not_authorization_or_execution(self):
        result = evaluate_remedy_workflow(profile(), request(), [observation()])
        self.assertEqual(result["workflow_status"], "PROPOSED")
        proposed = result["proposed_steps"][0]
        self.assertTrue(proposed["protected"])
        self.assertTrue(proposed["requires_fresh_authorization"])
        self.assertFalse(proposed["authorized"])
        self.assertFalse(proposed["executed"])
        self.assertFalse(result["protected_side_effect_authorized"])
        self.assertFalse(result["protected_side_effect_executed"])
        self.assertFalse(result["settlement_evidence_created"])
        self.assertFalse(result["legal_remedy_established"])

    def test_missing_required_trigger_fails_closed(self):
        result = evaluate_remedy_workflow(profile(), request(), [])
        self.assertEqual(result["workflow_status"], "REQUIRE_ADDITIONAL_EVIDENCE")
        self.assertEqual(result["unresolved_required_rules"], (f"{BASE}/rule/refund",))

    def test_missing_optional_trigger_is_not_adverse(self):
        result = evaluate_remedy_workflow(profile(rules=[rule("notify")]), request(), [])
        self.assertEqual(result["workflow_status"], "PARTIAL")
        self.assertEqual(result["rule_trace"][0]["decision"], "IGNORED_OPTIONAL_MISSING")

    def test_unknown_profile_critical_fails_closed(self):
        result = evaluate_remedy_workflow(profile(critical=[CRITICAL]), request(), [observation()])
        self.assertEqual(result["workflow_status"], "INDETERMINATE")
        self.assertIn(CRITICAL, result["unknown_critical_uris"])
        understood = evaluate_remedy_workflow(profile(critical=[CRITICAL]), request(understood=[CRITICAL]), [observation()])
        self.assertEqual(understood["workflow_status"], "PROPOSED")

    def test_unknown_rule_step_and_observation_critical_fail_closed(self):
        cases = [
            (profile(rules=[rule("refund", required=True, critical=[CRITICAL])]), observation()),
            (profile(rules=[rule("refund", required=True, steps=[step("refund", critical=[CRITICAL])])]), observation()),
            (profile(), observation(critical=[CRITICAL])),
        ]
        for method, observed in cases:
            with self.subTest(profile=method):
                self.assertEqual(evaluate_remedy_workflow(method, request(), [observed])["workflow_status"], "INDETERMINATE")

    def test_conflicting_actions_remain_visible_and_require_review(self):
        group = f"{BASE}/conflict/remedy-choice"
        rules = [rule("refund", steps=[step("refund", protected=True, conflict_group=group)]),
                 rule("replace", steps=[step("replace", protected=True, conflict_group=group)])]
        result = evaluate_remedy_workflow(profile(rules=rules), request(), [observation("refund"), observation("replace")])
        self.assertEqual(result["workflow_status"], "REQUIRE_HUMAN_REVIEW")
        self.assertEqual(len(result["conflicts"][0]["steps"]), 2)

    def test_dependencies_are_topologically_ordered(self):
        notify = step("notify")
        refund = step("refund", protected=True, depends_on=[notify["id"]])
        result = evaluate_remedy_workflow(profile(rules=[rule("refund", required=True, steps=[notify, refund])]), request(), [observation()])
        self.assertEqual(tuple(item["id"] for item in result["proposed_steps"]), (notify["id"], refund["id"]))

    def test_dependency_cycle_is_rejected(self):
        a = step("a", depends_on=[f"{BASE}/step/b"])
        b = step("b", depends_on=[f"{BASE}/step/a"])
        with self.assertRaises(MarketplaceRemedyWorkflowError) as caught:
            validate_remedy_workflow_profile(profile(rules=[rule("refund", steps=[a, b])]))
        self.assertEqual(caught.exception.code, "WORKFLOW_DEPENDENCY_CYCLE")

    def test_dangling_dependency_is_rejected(self):
        with self.assertRaises(MarketplaceRemedyWorkflowError) as caught:
            validate_remedy_workflow_profile(profile(rules=[rule("refund", steps=[step("refund", depends_on=[f"{BASE}/step/missing"])])]))
        self.assertEqual(caught.exception.code, "WORKFLOW_DANGLING_DEPENDENCY")

    def test_duplicate_delivery_is_semantically_replay_neutral(self):
        observed = observation()
        first = evaluate_remedy_workflow(profile(), request(), [observed])
        replay = evaluate_remedy_workflow(profile(), request(), [observed, deepcopy(observed)])
        self.assertEqual(first["input_fingerprint"], replay["input_fingerprint"])
        self.assertEqual(first["result_fingerprint"], replay["result_fingerprint"])
        self.assertEqual(replay["duplicate_observations"], 1)
        self.assertEqual(evaluate_remedy_workflow_reuse(first, profile(), request(), [observed, deepcopy(observed)])["reuse_status"], "REUSABLE")

    def test_changed_profile_invalidates_exact_reuse(self):
        first = evaluate_remedy_workflow(profile(), request(), [observation()])
        changed = profile(rules=[rule("refund", required=True, steps=[step("refund")])])
        reuse = evaluate_remedy_workflow_reuse(first, changed, request(), [observation()])
        self.assertEqual(reuse["reuse_status"], "NOT_REUSABLE")
        self.assertIn("WORKFLOW_METHOD_PROFILE_CHANGED", reuse["reasons"])

    def test_changed_source_fingerprint_invalidates_reuse(self):
        first = evaluate_remedy_workflow(profile(), request(), [observation()])
        reuse = evaluate_remedy_workflow_reuse(first, profile(), request(), [observation(fingerprint="b" * 43)])
        self.assertEqual(reuse["reuse_status"], "NOT_REUSABLE")
        self.assertIn("WORKFLOW_INPUT_CHANGED", reuse["reasons"])

    def test_conflicting_trigger_observations_are_rejected(self):
        with self.assertRaises(MarketplaceRemedyWorkflowError) as caught:
            evaluate_remedy_workflow(profile(), request(), [observation(), observation(state="ABSENT")])
        self.assertEqual(caught.exception.code, "WORKFLOW_OBSERVATION_CONFLICT")

    def test_tampered_result_is_rejected(self):
        tampered = evaluate_remedy_workflow(profile(), request(), [observation()])
        tampered["workflow_status"] = "PARTIAL"
        with self.assertRaises(MarketplaceRemedyWorkflowError) as caught:
            validate_remedy_workflow_result(tampered)
        self.assertEqual(caught.exception.code, "WORKFLOW_RESULT_INTEGRITY_MISMATCH")

    def test_unhashable_observation_state_fails_explicitly(self):
        bad = observation()
        bad["state"] = []
        with self.assertRaises(MarketplaceRemedyWorkflowError) as caught:
            evaluate_remedy_workflow(profile(), request(), [bad])
        self.assertEqual(caught.exception.code, "INVALID_WORKFLOW_OBSERVATION_STATE")


if __name__ == "__main__":
    unittest.main()
