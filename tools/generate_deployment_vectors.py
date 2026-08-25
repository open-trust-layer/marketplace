"""Generate Marketplace deployment-profile v1 conformance vectors."""
from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from marketplace_deployment_v1 import (
    MAX_COMPONENTS,
    MAX_CONTEXT_ENTRIES,
    MAX_OBSERVATIONS,
    MAX_SERVICES,
    MODE_READ_ONLY,
    MODE_SIDE_EFFECT,
    PROFILE_CORE,
    ROLE_EVIDENCE_STORE,
    ROLE_POLICY_AUTHORIZATION,
    ROLE_RESOLVER,
    ROLE_SIDE_EFFECT_EXECUTOR,
    ROLE_TRANSPORT_INGRESS,
    deployment_config_fingerprint,
    evaluate_deployment_readiness,
    evaluate_deployment_reuse,
    validate_deployment_profile,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance" / "vectors" / "deployment-profiles-v1.json"
BASE = "https://example.test/deployment"
CAP_READ = f"{BASE}/capability/read"
CAP_WRITE = f"{BASE}/capability/write"
CAP_RESOLVE = f"{BASE}/capability/resolve"
CRITICAL = f"{BASE}/critical/runtime-v1"


def olp_commit() -> str:
    import olp
    repo = Path(olp.__file__).resolve().parents[2]
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def jsonable(value):
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    return value


def component(name: str, role: str, *, required: bool = True, critical=()) -> dict:
    return {
        "id": f"{BASE}/component/{name}",
        "role": role,
        "adapter": f"{BASE}/adapter/{name}",
        "required": required,
        "critical": sorted(critical),
    }


def service(
    name: str, capability: str, mode: str, roles: tuple[str, ...],
    *, required: bool = True, endpoints=None, critical=(),
) -> dict:
    return {
        "id": f"{BASE}/service/{name}",
        "capability": capability,
        "mode": mode,
        "required": required,
        "required_roles": sorted(roles),
        "endpoints": sorted(endpoints if endpoints is not None else [f"https://node.example/{name}"]),
        "critical": sorted(critical),
    }


def profile(
    *, side_effect: bool = True, optional_resolver: bool = False,
    critical=(), component_critical=(), service_critical=(), context=None,
) -> dict:
    components = [
        component("ingress", ROLE_TRANSPORT_INGRESS, critical=component_critical),
        component("store", ROLE_EVIDENCE_STORE),
    ]
    services = [service(
        "read", CAP_READ, MODE_READ_ONLY,
        (ROLE_EVIDENCE_STORE, ROLE_TRANSPORT_INGRESS), critical=service_critical,
    )]
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
            "resolver", CAP_RESOLVE, MODE_READ_ONLY, (ROLE_RESOLVER,), required=False,
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
        "context": context or {},
    }


def observations(value: dict, *, status: str = "READY", observation_critical=()) -> list[dict]:
    return [
        {
            "component_id": item["id"],
            "adapter": item["adapter"],
            "status": status,
            "critical": sorted(observation_critical),
        }
        for item in value["components"]
    ]


def build() -> dict:
    cases: list[dict] = []
    negative_cases: list[dict] = []

    def add(case_id: str, kind: str, payload: dict, expected) -> None:
        cases.append({"id": case_id, "kind": kind, **payload, "expected": jsonable(expected)})

    def negative(case_id: str, kind: str, payload: dict, code: str) -> None:
        negative_cases.append({"id": case_id, "kind": kind, **payload, "expected_error": code})

    base_read = profile(side_effect=False)
    base_write = profile()
    base_optional = profile(side_effect=False, optional_resolver=True)
    add("profile-read-only-valid", "profile", {"profile": base_read}, {
        "profile": validate_deployment_profile(base_read),
        "fingerprint": deployment_config_fingerprint(base_read),
    })
    add("profile-side-effect-valid", "profile", {"profile": base_write}, {
        "profile": validate_deployment_profile(base_write),
        "fingerprint": deployment_config_fingerprint(base_write),
    })

    def evaluation(case_id: str, value: dict, observed, understood=()) -> dict:
        result = evaluate_deployment_readiness(value, observed, understood)
        add(case_id, "evaluation", {
            "profile": value,
            "observations": observed,
            "understood_critical": list(understood),
        }, result)
        return result

    ready_read = evaluation("evaluation-read-only-ready", base_read, observations(base_read))
    ready_write = evaluation("evaluation-side-effect-ready", base_write, observations(base_write))

    missing_required = [
        item for item in observations(base_read)
        if not item["component_id"].endswith("/store")
    ]
    evaluation("evaluation-missing-required-component", base_read, missing_required)
    evaluation("evaluation-required-degraded", base_read, observations(base_read, status="DEGRADED"))
    evaluation("evaluation-required-failed", base_read, observations(base_read, status="FAILED"))
    evaluation("evaluation-required-unknown", base_read, observations(base_read, status="UNKNOWN"))

    missing_optional = [
        item for item in observations(base_optional)
        if not item["component_id"].endswith("/resolver")
    ]
    evaluation("evaluation-optional-component-missing", base_optional, missing_optional)
    optional_failed = observations(base_optional)
    for item in optional_failed:
        if item["component_id"].endswith("/resolver"):
            item["status"] = "FAILED"
    evaluation("evaluation-optional-component-failed", base_optional, optional_failed)

    adapter_mismatch = observations(base_read)
    adapter_mismatch[0]["adapter"] = f"{BASE}/adapter/unexpected"
    evaluation("evaluation-adapter-binding-mismatch", base_read, adapter_mismatch)

    top_critical = profile(side_effect=False, critical=(CRITICAL,))
    evaluation("evaluation-top-critical-unknown", top_critical, observations(top_critical))
    evaluation("evaluation-top-critical-understood", top_critical, observations(top_critical), (CRITICAL,))

    component_critical = profile(side_effect=False, component_critical=(CRITICAL,))
    evaluation("evaluation-component-critical-unknown", component_critical, observations(component_critical))
    evaluation("evaluation-component-critical-understood", component_critical, observations(component_critical), (CRITICAL,))

    service_critical = profile(side_effect=False, service_critical=(CRITICAL,))
    evaluation("evaluation-service-critical-unknown", service_critical, observations(service_critical))
    evaluation("evaluation-service-critical-understood", service_critical, observations(service_critical), (CRITICAL,))

    observation_critical_profile = profile(side_effect=False)
    critical_observed = observations(observation_critical_profile, observation_critical=(CRITICAL,))
    evaluation("evaluation-observation-critical-unknown", observation_critical_profile, critical_observed)
    evaluation("evaluation-observation-critical-understood", observation_critical_profile, critical_observed, (CRITICAL,))

    duplicate_observed = observations(base_read)
    duplicate_observed.append(deepcopy(duplicate_observed[0]))
    evaluation("evaluation-duplicate-observation", base_read, duplicate_observed)

    empty_endpoint_profile = profile(side_effect=False)
    empty_endpoint_profile["services"][0]["endpoints"] = []
    evaluation("evaluation-offline-service-without-endpoint", empty_endpoint_profile, observations(empty_endpoint_profile))

    context_profile = profile(
        side_effect=False,
        context={f"{BASE}/context/region": "eu", f"{BASE}/context/replicas": 2},
    )
    evaluation("evaluation-context-metadata", context_profile, observations(context_profile))

    multi_store = profile(side_effect=False)
    multi_store["components"].append(component("store-backup", ROLE_EVIDENCE_STORE, required=False))
    multi_store["components"].sort(key=lambda item: item["id"])
    multi_observed = observations(multi_store)
    for item in multi_observed:
        if item["component_id"].endswith("/store"):
            item["status"] = "FAILED"
    evaluation("evaluation-redundant-role-one-ready", multi_store, multi_observed)

    mixed_degraded = observations(base_read)
    mixed_degraded[0]["status"] = "DEGRADED"
    evaluation("evaluation-service-backing-degraded", base_read, mixed_degraded)

    evaluation("evaluation-optional-path-fully-ready", base_optional, observations(base_optional))

    duplicate_capability = profile(side_effect=False)
    duplicate_capability["services"].append(service(
        "read-alt", CAP_READ, MODE_READ_ONLY,
        (ROLE_EVIDENCE_STORE, ROLE_TRANSPORT_INGRESS), required=False,
        endpoints=("https://node.example/alt",),
    ))
    duplicate_capability["services"].sort(key=lambda item: item["id"])
    evaluation("evaluation-capability-deduplicated", duplicate_capability, observations(duplicate_capability))

    multi_endpoint = profile(side_effect=False)
    multi_endpoint["services"][0]["endpoints"] = sorted((
        "https://node.example/read-a", "https://node.example/read-b",
    ))
    evaluation("evaluation-multiple-endpoints", multi_endpoint, observations(multi_endpoint))

    reversed_observations = list(reversed(observations(base_write)))
    evaluation("evaluation-observation-order-neutral", base_write, reversed_observations)

    add("reuse-exact-input", "reuse", {
        "prior_result": jsonable(ready_read),
        "profile": base_read,
        "observations": observations(base_read),
        "understood_critical": [],
    }, evaluate_deployment_reuse(ready_read, base_read, observations(base_read)))

    changed_observed = observations(base_read)
    changed_observed[0]["status"] = "DEGRADED"
    add("reuse-changed-observation", "reuse", {
        "prior_result": jsonable(ready_read),
        "profile": base_read,
        "observations": changed_observed,
        "understood_critical": [],
    }, evaluate_deployment_reuse(ready_read, base_read, changed_observed))

    changed_profile = deepcopy(base_read)
    changed_profile["context"] = {f"{BASE}/context/region": "us"}
    add("reuse-changed-configuration", "reuse", {
        "prior_result": jsonable(ready_read),
        "profile": changed_profile,
        "observations": observations(changed_profile),
        "understood_critical": [],
    }, evaluate_deployment_reuse(ready_read, changed_profile, observations(changed_profile)))

    bad = deepcopy(base_read); bad["extra"] = True
    negative("profile-unknown-field", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_PROFILE")
    bad = deepcopy(base_read); bad["version"] = True
    negative("profile-version-bool", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_PROFILE")
    bad = deepcopy(base_read); bad["profile"] = f"{BASE}/profile/other"
    negative("profile-unsupported-profile", "profile", {"profile": bad}, "UNSUPPORTED_DEPLOYMENT_PROFILE")
    bad = deepcopy(base_read); bad["deployment_id"] = "relative"
    negative("profile-invalid-deployment-id", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_URI")
    bad = deepcopy(base_read); bad["operator"] = "operator"
    negative("profile-invalid-operator", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_URI")
    bad = deepcopy(base_read); bad["components"] = []
    negative("profile-empty-components", "profile", {"profile": bad}, "EMPTY_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["services"] = []
    negative("profile-empty-services", "profile", {"profile": bad}, "EMPTY_DEPLOYMENT_SET")

    bad = deepcopy(base_read); bad["components"] = list(reversed(bad["components"]))
    negative("profile-unsorted-components", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["components"].append(deepcopy(bad["components"][0])); bad["components"].sort(key=lambda x: x["id"])
    negative("profile-duplicate-component-id", "profile", {"profile": bad}, "DUPLICATE_DEPLOYMENT_ID")

    bad = deepcopy(base_read); bad["components"][0].pop("critical")
    negative("component-missing-field", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_COMPONENT")
    bad = deepcopy(base_read); bad["components"][0]["required"] = "yes"
    negative("component-required-not-bool", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_COMPONENT")
    for field in ("id", "role", "adapter"):
        bad = deepcopy(base_read); bad["components"][0][field] = "relative"
        negative(f"component-invalid-{field}", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_URI")
    bad = deepcopy(base_read); bad["components"][0]["critical"] = [CRITICAL, CRITICAL]
    negative("component-duplicate-critical", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")

    bad = deepcopy(base_write); bad["services"] = list(reversed(bad["services"]))
    negative("profile-unsorted-services", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["services"].append(deepcopy(bad["services"][0])); bad["services"].sort(key=lambda x: x["id"])
    negative("profile-duplicate-service-id", "profile", {"profile": bad}, "DUPLICATE_DEPLOYMENT_ID")
    bad = deepcopy(base_read); bad["services"][0].pop("critical")
    negative("service-missing-field", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_SERVICE")
    bad = deepcopy(base_read); bad["services"][0]["required"] = "yes"
    negative("service-required-not-bool", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_SERVICE")
    bad = deepcopy(base_read); bad["services"][0]["mode"] = "MAGIC"
    negative("service-invalid-mode", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_SERVICE")
    for field in ("id", "capability"):
        bad = deepcopy(base_read); bad["services"][0][field] = "relative"
        negative(f"service-invalid-{field}", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_URI")
    bad = deepcopy(base_read); bad["services"][0]["required_roles"] = []
    negative("service-empty-required-roles", "profile", {"profile": bad}, "EMPTY_DEPLOYMENT_SET")
    role = base_read["services"][0]["required_roles"][0]
    bad = deepcopy(base_read); bad["services"][0]["required_roles"] = [role, role]
    negative("service-duplicate-required-role", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["services"][0]["required_roles"] = list(reversed(bad["services"][0]["required_roles"]))
    negative("service-unsorted-required-roles", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["services"][0]["endpoints"] = ["relative"]
    negative("service-invalid-endpoint", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_URI")
    bad = deepcopy(base_read); endpoint = bad["services"][0]["endpoints"][0]; bad["services"][0]["endpoints"] = [endpoint, endpoint]
    negative("service-duplicate-endpoint", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["services"][0]["critical"] = [CRITICAL, CRITICAL]
    negative("service-duplicate-critical", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")

    bad = deepcopy(base_write)
    write = next(item for item in bad["services"] if item["mode"] == MODE_SIDE_EFFECT)
    write["required_roles"] = sorted((ROLE_SIDE_EFFECT_EXECUTOR, ROLE_TRANSPORT_INGRESS))
    negative("service-side-effect-missing-authorization-role", "profile", {"profile": bad}, "SIDE_EFFECT_AUTHORIZATION_GATE_REQUIRED")
    bad = deepcopy(base_write)
    write = next(item for item in bad["services"] if item["mode"] == MODE_SIDE_EFFECT)
    write["required_roles"] = sorted((ROLE_POLICY_AUTHORIZATION, ROLE_TRANSPORT_INGRESS))
    negative("service-side-effect-missing-executor-role", "profile", {"profile": bad}, "SIDE_EFFECT_AUTHORIZATION_GATE_REQUIRED")
    bad = deepcopy(base_read); bad["services"][0]["required_roles"] = sorted((ROLE_EVIDENCE_STORE, ROLE_RESOLVER))
    negative("service-unbacked-role", "profile", {"profile": bad}, "UNBACKED_SERVICE_ROLE")

    bad = deepcopy(base_read); bad["critical"] = [CRITICAL, CRITICAL]
    negative("profile-duplicate-critical", "profile", {"profile": bad}, "NONCANONICAL_DEPLOYMENT_SET")
    bad = deepcopy(base_read); bad["context"] = []
    negative("profile-context-not-map", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_CONTEXT")
    bad = deepcopy(base_read); bad["context"] = {f"{BASE}/context/api-key": "redacted"}
    negative("profile-secret-like-context-key", "profile", {"profile": bad}, "SECRET_MATERIAL_FIELD_FORBIDDEN")
    bad = deepcopy(base_read); bad["context"] = {f"{BASE}/context/config": {"password": "redacted"}}
    negative("profile-nested-secret-like-key", "profile", {"profile": bad}, "SECRET_MATERIAL_FIELD_FORBIDDEN")
    bad = deepcopy(base_read); bad["context"] = {"relative": "x"}
    negative("profile-invalid-context-key", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_URI")

    observed = observations(base_read)
    bad_observation = deepcopy(observed[0]); bad_observation.pop("critical")
    negative("observation-missing-field", "evaluation", {
        "profile": base_read, "observations": [bad_observation], "understood_critical": [],
    }, "INVALID_COMPONENT_OBSERVATION")
    bad_observation = deepcopy(observed[0]); bad_observation["status"] = "MAYBE"
    negative("observation-invalid-status", "evaluation", {
        "profile": base_read, "observations": [bad_observation], "understood_critical": [],
    }, "INVALID_COMPONENT_STATUS")
    bad_observation = deepcopy(observed[0]); bad_observation["component_id"] = "relative"
    negative("observation-invalid-component-id", "evaluation", {
        "profile": base_read, "observations": [bad_observation], "understood_critical": [],
    }, "INVALID_DEPLOYMENT_URI")
    bad_observation = deepcopy(observed[0]); bad_observation["adapter"] = "relative"
    negative("observation-invalid-adapter", "evaluation", {
        "profile": base_read, "observations": [bad_observation], "understood_critical": [],
    }, "INVALID_DEPLOYMENT_URI")
    bad_observation = deepcopy(observed[0]); bad_observation["critical"] = [CRITICAL, CRITICAL]
    negative("observation-duplicate-critical", "evaluation", {
        "profile": base_read, "observations": [bad_observation], "understood_critical": [],
    }, "NONCANONICAL_DEPLOYMENT_SET")
    bad_observation = deepcopy(observed[0]); bad_observation["component_id"] = f"{BASE}/component/unknown"
    negative("observation-unknown-component", "evaluation", {
        "profile": base_read, "observations": [bad_observation], "understood_critical": [],
    }, "UNKNOWN_COMPONENT_OBSERVATION")

    bad = deepcopy(base_read); bad["components"] = 7
    negative("profile-components-not-collection", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_COLLECTION")
    negative("observations-not-collection", "evaluation", {
        "profile": base_read, "observations": 7, "understood_critical": [],
    }, "INVALID_DEPLOYMENT_COLLECTION")
    bad = deepcopy(base_read); bad["services"][0]["mode"] = []
    negative("service-mode-unhashable", "profile", {"profile": bad}, "INVALID_DEPLOYMENT_SERVICE")

    conflict = deepcopy(observed[0]); conflict["status"] = "FAILED"
    negative("observation-conflict", "evaluation", {
        "profile": base_read, "observations": [observed[0], conflict], "understood_critical": [],
    }, "COMPONENT_OBSERVATION_CONFLICT")
    negative("understood-critical-duplicate", "evaluation", {
        "profile": base_read,
        "observations": observations(base_read),
        "understood_critical": [CRITICAL, CRITICAL],
    }, "NONCANONICAL_DEPLOYMENT_SET")
    negative("understood-critical-invalid-uri", "evaluation", {
        "profile": base_read,
        "observations": observations(base_read),
        "understood_critical": ["relative"],
    }, "INVALID_DEPLOYMENT_URI")

    tampered = jsonable(ready_read); tampered["readiness"] = "DEGRADED"
    negative("reuse-tampered-result", "reuse", {
        "prior_result": tampered,
        "profile": base_read,
        "observations": observations(base_read),
        "understood_critical": [],
    }, "DEPLOYMENT_RESULT_INTEGRITY_MISMATCH")
    tampered = jsonable(ready_write); tampered["protected_side_effect_authorized"] = True
    negative("reuse-tampered-boundary", "reuse", {
        "prior_result": tampered,
        "profile": base_write,
        "observations": observations(base_write),
        "understood_critical": [],
    }, "INVALID_PRIOR_DEPLOYMENT_RESULT")

    negative("synthetic-component-limit", "synthetic-component-limit", {
        "count": MAX_COMPONENTS + 1, "base_profile": base_read,
    }, "DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-service-limit", "synthetic-service-limit", {
        "count": MAX_SERVICES + 1, "base_profile": base_read,
    }, "DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-observation-limit", "synthetic-observation-limit", {
        "count": MAX_OBSERVATIONS + 1, "base_profile": base_read,
    }, "DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-context-limit", "synthetic-context-limit", {
        "count": MAX_CONTEXT_ENTRIES + 1, "base_profile": base_read,
    }, "INVALID_DEPLOYMENT_CONTEXT")
    negative("synthetic-uri-limit", "synthetic-uri-limit", {
        "utf8_bytes": 2049, "base_profile": base_read,
    }, "DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED")
    negative("synthetic-endpoint-limit", "synthetic-endpoint-limit", {
        "count": 257, "base_profile": base_read,
    }, "DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED")

    return {
        "format": "marketplace-deployment-profiles-v1-conformance-vectors",
        "olp_reference_source_commit": olp_commit(),
        "profile": PROFILE_CORE,
        "note": "deployment descriptors and observations are processing metadata; this JSON file is not a Marketplace wire format",
        "cases": cases,
        "negative_cases": negative_cases,
    }


def main() -> int:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT}")
    print(f"positive/evaluation={len(data['cases'])} negative/adversarial={len(data['negative_cases'])} total={len(data['cases']) + len(data['negative_cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
