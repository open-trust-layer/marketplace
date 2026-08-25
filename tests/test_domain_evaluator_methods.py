from __future__ import annotations

import unittest
from copy import deepcopy

from marketplace_domain_evaluator_v1 import (
    PROFILE_CRITERION_THRESHOLD,
    MarketplaceDomainEvaluatorError,
    domain_method_profile_fingerprint,
    evaluate_domain_method,
    evaluate_domain_method_reuse,
    validate_domain_method_profile,
    validate_domain_result,
)
from marketplace_trust_evaluation_v1 import DOMAIN_STATUSES as M9_DOMAIN_STATUSES

BASE = "https://example.test/domain-method"
METHOD = f"{BASE}/method/software-release-readiness-v1"
DOMAIN = f"{BASE}/domain/software-change"
PURPOSE = f"{BASE}/purpose/release-readiness"
CRITICAL = f"{BASE}/critical/static-analysis-v1"
RID = "r1_SK_yrUOC25u_ZODjtpO757oZsM1NquB1W1VM5BZK8QI"


def criterion(name: str, *, required: bool, weight: int, critical=()) -> dict:
    return {
        "id": f"{BASE}/criterion/{name}",
        "required": required,
        "weight": weight,
        "critical": sorted(critical),
    }


def profile(*, critical=()) -> dict:
    criteria = [
        criterion("a", required=True, weight=3),
        criterion("b", required=True, weight=3),
        criterion("c", required=False, weight=1),
    ]
    return {
        "version": 1,
        "profile": PROFILE_CRITERION_THRESHOLD,
        "method": METHOD,
        "domain": DOMAIN,
        "purposes": [PURPOSE],
        "criteria": criteria,
        "support_threshold": 3,
        "oppose_threshold": 3,
        "critical": sorted(critical),
    }


def request(*, understood=()) -> dict:
    return {
        "version": 1,
        "method": METHOD,
        "domain": DOMAIN,
        "purpose": PURPOSE,
        "target_record_id": RID,
        "context": {},
        "understood_critical": sorted(understood),
    }


def observation(name: str, state: str, *, critical=(), reasons=()) -> dict:
    return {
        "criterion": f"{BASE}/criterion/{name}",
        "state": state,
        "critical": sorted(critical),
        "reason_uris": sorted(reasons),
    }


def complete(a: str = "SUPPORTS", b: str = "NEUTRAL", c: str = "NEUTRAL") -> list[dict]:
    return [observation("a", a), observation("b", b), observation("c", c)]


class DomainEvaluatorMethodTests(unittest.TestCase):
    def test_support_threshold_derives_m9_compatible_domain_status(self):
        result = evaluate_domain_method(profile(), request(), complete())
        self.assertEqual(result["domain_status"], "SUPPORTS")
        self.assertIn(result["domain_status"], M9_DOMAIN_STATUSES)
        self.assertEqual(result["support_points"], 3)

    def test_oppose_threshold_is_method_relative(self):
        result = evaluate_domain_method(profile(), request(), complete(a="OPPOSES"))
        self.assertEqual(result["domain_status"], "OPPOSES")
        self.assertEqual(result["oppose_points"], 3)
        self.assertFalse(result["universal_trust_score_established"])

    def test_below_threshold_is_neutral_not_negative(self):
        result = evaluate_domain_method(
            profile(), request(),
            [observation("a", "NEUTRAL"), observation("b", "NEUTRAL")],
        )
        self.assertEqual(result["domain_status"], "NEUTRAL")
        self.assertEqual(result["final_rule"], "NO_DIRECTIONAL_THRESHOLD_MET")

    def test_support_and_oppose_thresholds_preserve_conflict(self):
        result = evaluate_domain_method(
            profile(), request(),
            [observation("a", "SUPPORTS"), observation("b", "OPPOSES")],
        )
        self.assertEqual(result["domain_status"], "UNKNOWN")
        self.assertTrue(result["conflict_detected"])
        self.assertEqual(result["final_rule"], "CONFLICTING_CRITERIA")

    def test_missing_required_criterion_fails_closed(self):
        result = evaluate_domain_method(profile(), request(), [observation("a", "SUPPORTS")])
        self.assertEqual(result["domain_status"], "UNKNOWN")
        self.assertIn(f"{BASE}/criterion/b", result["unresolved_required_criteria"])

    def test_missing_optional_criterion_does_not_block(self):
        result = evaluate_domain_method(
            profile(), request(),
            [observation("a", "SUPPORTS"), observation("b", "NEUTRAL")],
        )
        self.assertEqual(result["domain_status"], "SUPPORTS")
        optional = next(item for item in result["criterion_trace"] if item["criterion"].endswith("/c"))
        self.assertEqual(optional["decision"], "IGNORED_OPTIONAL_MISSING")

    def test_unknown_method_critical_semantics_fail_closed_until_understood(self):
        value = profile(critical=(CRITICAL,))
        blocked = evaluate_domain_method(value, request(), complete())
        self.assertEqual(blocked["domain_status"], "UNKNOWN")
        self.assertIn(CRITICAL, blocked["unknown_critical_uris"])
        accepted = evaluate_domain_method(value, request(understood=(CRITICAL,)), complete())
        self.assertEqual(accepted["domain_status"], "SUPPORTS")

    def test_unknown_criterion_critical_semantics_fail_closed(self):
        value = profile()
        value["criteria"][0]["critical"] = [CRITICAL]
        result = evaluate_domain_method(value, request(), complete())
        self.assertEqual(result["domain_status"], "UNKNOWN")
        self.assertEqual(result["final_rule"], "UNKNOWN_CRITICAL_SEMANTICS")

    def test_positive_domain_result_does_not_authorize_or_establish_trust(self):
        result = evaluate_domain_method(profile(), request(), complete())
        self.assertFalse(result["protected_side_effect_authorized"])
        self.assertFalse(result["authorization_evaluated"])
        self.assertFalse(result["truth_established"])
        self.assertFalse(result["numeric_confidence_standardized"])
        self.assertFalse(result["cross_method_comparability_established"])

    def test_exact_reuse_is_reusable(self):
        p = profile()
        r = request()
        observed = complete()
        prior = evaluate_domain_method(p, r, observed)
        reuse = evaluate_domain_method_reuse(prior, p, r, observed)
        self.assertEqual(reuse["reuse_status"], "REUSABLE")
        self.assertEqual(reuse["reasons"], ())

    def test_changed_profile_is_not_reused_as_same_method(self):
        p = profile()
        prior = evaluate_domain_method(p, request(), complete())
        changed = deepcopy(p)
        changed["support_threshold"] = 4
        reuse = evaluate_domain_method_reuse(prior, changed, request(), complete())
        self.assertEqual(reuse["reuse_status"], "NOT_REUSABLE")
        self.assertIn("DOMAIN_METHOD_PROFILE_CHANGED", reuse["reasons"])
        self.assertNotEqual(
            domain_method_profile_fingerprint(p),
            domain_method_profile_fingerprint(changed),
        )

    def test_conflicting_observations_for_one_criterion_are_rejected(self):
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            evaluate_domain_method(
                profile(), request(),
                [observation("a", "SUPPORTS"), observation("a", "OPPOSES")],
            )
        self.assertEqual(caught.exception.code, "DOMAIN_OBSERVATION_CONFLICT")

    def test_exact_duplicate_observation_is_deduplicated(self):
        observed = complete()
        observed.append(deepcopy(observed[0]))
        result = evaluate_domain_method(profile(), request(), observed)
        self.assertEqual(result["duplicate_observations"], 1)
        self.assertEqual(result["domain_status"], "SUPPORTS")

    def test_duplicate_delivery_preserves_semantic_result_and_reuse(self):
        base_observations = complete()
        duplicate_observations = complete()
        duplicate_observations.append(deepcopy(duplicate_observations[0]))
        prior = evaluate_domain_method(profile(), request(), base_observations)
        replayed = evaluate_domain_method(profile(), request(), duplicate_observations)
        self.assertEqual(prior["input_fingerprint"], replayed["input_fingerprint"])
        self.assertEqual(prior["result_fingerprint"], replayed["result_fingerprint"])
        self.assertEqual(replayed["duplicate_observations"], 1)
        reuse = evaluate_domain_method_reuse(prior, profile(), request(), duplicate_observations)
        self.assertEqual(reuse["reuse_status"], "REUSABLE")
        self.assertEqual(reuse["reasons"], ())

    def test_invalid_method_binding_is_rejected(self):
        r = request()
        r["method"] = f"{BASE}/method/other"
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            evaluate_domain_method(profile(), r, complete())
        self.assertEqual(caught.exception.code, "DOMAIN_METHOD_BINDING_MISMATCH")

    def test_noncollection_observations_fail_explicitly(self):
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            evaluate_domain_method(profile(), request(), 7)
        self.assertEqual(caught.exception.code, "INVALID_DOMAIN_COLLECTION")

    def test_unhashable_observation_state_is_explicit_input_error(self):
        bad = observation("a", "SUPPORTS")
        bad["state"] = []
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            evaluate_domain_method(profile(), request(), [bad])
        self.assertEqual(caught.exception.code, "INVALID_DOMAIN_OBSERVATION_STATE")

    def test_threshold_above_total_weight_is_rejected(self):
        value = profile()
        value["support_threshold"] = 8
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            validate_domain_method_profile(value)
        self.assertEqual(caught.exception.code, "INVALID_DOMAIN_THRESHOLD")

    def test_result_fingerprint_detects_tampering(self):
        result = evaluate_domain_method(profile(), request(), complete())
        tampered = dict(result)
        tampered["domain_status"] = "NEUTRAL"
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            validate_domain_result(tampered)
        self.assertEqual(caught.exception.code, "DOMAIN_RESULT_INTEGRITY_MISMATCH")


    def test_unhashable_prior_domain_status_is_explicit_input_error(self):
        result = evaluate_domain_method(profile(), request(), complete())
        tampered = dict(result)
        tampered["domain_status"] = []
        with self.assertRaises(MarketplaceDomainEvaluatorError) as caught:
            validate_domain_result(tampered)
        self.assertEqual(caught.exception.code, "INVALID_PRIOR_DOMAIN_RESULT")


if __name__ == "__main__":
    unittest.main()
