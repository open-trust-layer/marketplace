from __future__ import annotations

import unittest

from marketplace_deployment_v1 import (
    MODE_READ_ONLY,
    MODE_SIDE_EFFECT,
    PROFILE_CORE,
    ROLE_EVIDENCE_STORE,
    ROLE_POLICY_AUTHORIZATION,
    ROLE_RESOLVER,
    ROLE_SIDE_EFFECT_EXECUTOR,
    ROLE_TRANSPORT_INGRESS,
    MarketplaceDeploymentError,
    evaluate_deployment_readiness,
    evaluate_deployment_reuse,
    validate_deployment_profile,
    validate_deployment_result,
)

BASE = "https://example.test/deployment"
CAP_READ = f"{BASE}/capability/read"
CAP_WRITE = f"{BASE}/capability/write"
CRITICAL = f"{BASE}/critical/runtime-v1"


def component(name: str, role: str, *, required: bool = True) -> dict:
    return {
        "id": f"{BASE}/component/{name}",
        "role": role,
        "adapter": f"{BASE}/adapter/{name}",
        "required": required,
        "critical": [],
    }


def service(name: str, capability: str, mode: str, roles: tuple[str, ...], *, required: bool = True) -> dict:
    return {
        "id": f"{BASE}/service/{name}",
        "capability": capability,
        "mode": mode,
        "required": required,
        "required_roles": sorted(roles),
        "endpoints": [f"https://node.example/{name}"],
        "critical": [],
    }


def profile(*, side_effect: bool = True, optional_resolver: bool = False, critical=()) -> dict:
    components = [
        component("ingress", ROLE_TRANSPORT_INGRESS),
        component("store", ROLE_EVIDENCE_STORE),
    ]
    services = [
        service("read", CAP_READ, MODE_READ_ONLY, (ROLE_EVIDENCE_STORE, ROLE_TRANSPORT_INGRESS)),
    ]
    if side_effect:
        components.extend([
            component("authorization", ROLE_POLICY_AUTHORIZATION),
            component("executor", ROLE_SIDE_EFFECT_EXECUTOR),
        ])
        services.append(service(
            "write", CAP_WRITE, MODE_SIDE_EFFECT,
            (ROLE_POLICY_AUTHORIZATION, ROLE_SIDE_EFFECT_EXECUTOR, ROLE_TRANSPORT_INGRESS),
        ))
    if optional_resolver:
        components.append(component("resolver", ROLE_RESOLVER, required=False))
        services.append(service(
            "resolver", f"{BASE}/capability/resolve", MODE_READ_ONLY,
            (ROLE_RESOLVER,), required=False,
        ))
    components.sort(key=lambda item: item["id"])
    services.sort(key=lambda item: item["id"])
    return {
        "version": 1,
        "profile": PROFILE_CORE,
        "deployment_id": f"{BASE}/node/a",
        "operator": "did:example:operator",
        "components": components,
        "services": services,
        "critical": sorted(critical),
        "context": {},
    }


def observations(value: dict, *, status: str = "READY") -> list[dict]:
    return [
        {
            "component_id": item["id"],
            "adapter": item["adapter"],
            "status": status,
            "critical": [],
        }
        for item in value["components"]
    ]


class DeploymentProfileTests(unittest.TestCase):
    def test_ready_node_advertises_only_backed_capabilities(self):
        value = profile()
        result = evaluate_deployment_readiness(value, observations(value))
        self.assertEqual(result["readiness"], "READY")
        self.assertEqual(set(result["advertised_capabilities"]), {CAP_READ, CAP_WRITE})
        self.assertFalse(result["protected_side_effect_authorized"])
        self.assertFalse(result["endpoint_reachability_established"])

    def test_missing_required_component_is_not_ready(self):
        value = profile(side_effect=False)
        observed = observations(value)
        observed = [item for item in observed if not item["component_id"].endswith("/store")]
        result = evaluate_deployment_readiness(value, observed)
        self.assertEqual(result["readiness"], "NOT_READY")
        self.assertIn("REQUIRED_COMPONENT_NOT_READY", result["reasons"])

    def test_optional_missing_component_degrades_without_blocking(self):
        value = profile(side_effect=False, optional_resolver=True)
        observed = [
            item for item in observations(value)
            if not item["component_id"].endswith("/resolver")
        ]
        result = evaluate_deployment_readiness(value, observed)
        self.assertEqual(result["readiness"], "DEGRADED")
        self.assertNotIn(f"{BASE}/capability/resolve", result["advertised_capabilities"])

    def test_side_effect_service_requires_authorization_gate(self):
        value = profile()
        write_service = next(item for item in value["services"] if item["mode"] == MODE_SIDE_EFFECT)
        write_service["required_roles"] = sorted((ROLE_SIDE_EFFECT_EXECUTOR, ROLE_TRANSPORT_INGRESS))
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            validate_deployment_profile(value)
        self.assertEqual(caught.exception.code, "SIDE_EFFECT_AUTHORIZATION_GATE_REQUIRED")

    def test_secret_like_context_field_is_rejected(self):
        value = profile(side_effect=False)
        value["context"] = {f"{BASE}/context/api-key": "do-not-put-secrets-here"}
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            validate_deployment_profile(value)
        self.assertEqual(caught.exception.code, "SECRET_MATERIAL_FIELD_FORBIDDEN")

    def test_conflicting_component_observations_are_rejected(self):
        value = profile(side_effect=False)
        observed = observations(value)
        conflicting = dict(observed[0])
        conflicting["status"] = "FAILED"
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            evaluate_deployment_readiness(value, observed + [conflicting])
        self.assertEqual(caught.exception.code, "COMPONENT_OBSERVATION_CONFLICT")

    def test_unknown_critical_semantics_fail_closed_until_understood(self):
        value = profile(side_effect=False, critical=(CRITICAL,))
        blocked = evaluate_deployment_readiness(value, observations(value))
        self.assertEqual(blocked["readiness"], "NOT_READY")
        accepted = evaluate_deployment_readiness(value, observations(value), (CRITICAL,))
        self.assertEqual(accepted["readiness"], "READY")

    def test_adapter_binding_mismatch_blocks_required_component(self):
        value = profile(side_effect=False)
        observed = observations(value)
        observed[0] = {**observed[0], "adapter": f"{BASE}/adapter/unexpected"}
        result = evaluate_deployment_readiness(value, observed)
        self.assertEqual(result["readiness"], "NOT_READY")
        self.assertIn("ADAPTER_BINDING_MISMATCH", result["component_trace"][0]["reasons"])

    def test_result_fingerprint_detects_tampering(self):
        value = profile(side_effect=False)
        result = evaluate_deployment_readiness(value, observations(value))
        tampered = dict(result)
        tampered["readiness"] = "DEGRADED"
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            validate_deployment_result(tampered)
        self.assertEqual(caught.exception.code, "DEPLOYMENT_RESULT_INTEGRITY_MISMATCH")

    def test_reuse_requires_exact_observation_binding(self):
        value = profile(side_effect=False)
        observed = observations(value)
        result = evaluate_deployment_readiness(value, observed)
        exact = evaluate_deployment_reuse(result, value, observed)
        self.assertEqual(exact["reuse_status"], "REUSABLE")
        changed = [dict(item) for item in observed]
        changed[0]["status"] = "DEGRADED"
        reused = evaluate_deployment_reuse(result, value, changed)
        self.assertEqual(reused["reuse_status"], "NOT_REUSABLE")
        self.assertIn("DEPLOYMENT_OBSERVATIONS_CHANGED", reused["reasons"])

    def test_unknown_global_critical_suppresses_capability_advertisement(self):
        value = profile(side_effect=False, critical=(CRITICAL,))
        result = evaluate_deployment_readiness(value, observations(value))
        self.assertEqual(result["readiness"], "NOT_READY")
        self.assertEqual(result["advertised_capabilities"], ())
        self.assertEqual(result["degraded_capabilities"], ())

    def test_descriptor_validation_does_not_establish_secret_absence(self):
        value = profile(side_effect=False)
        result = evaluate_deployment_readiness(value, observations(value))
        self.assertFalse(result["secret_material_absence_established"])


    def test_noncollection_components_fail_explicitly(self):
        value = profile(side_effect=False)
        value["components"] = 7
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            validate_deployment_profile(value)
        self.assertEqual(caught.exception.code, "INVALID_DEPLOYMENT_COLLECTION")

    def test_noncollection_observations_fail_explicitly(self):
        value = profile(side_effect=False)
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            evaluate_deployment_readiness(value, 7)
        self.assertEqual(caught.exception.code, "INVALID_DEPLOYMENT_COLLECTION")

    def test_unhashable_service_mode_is_an_explicit_input_error(self):
        value = profile(side_effect=False)
        value["services"][0]["mode"] = []
        with self.assertRaises(MarketplaceDeploymentError) as caught:
            validate_deployment_profile(value)
        self.assertEqual(caught.exception.code, "INVALID_DEPLOYMENT_SERVICE")



if __name__ == "__main__":
    unittest.main()
