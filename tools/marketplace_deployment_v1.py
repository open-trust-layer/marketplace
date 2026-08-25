"""Non-normative Marketplace deployment-profile v1 reference helpers.

M14 validates portable runtime composition metadata and evaluates local
component readiness. It does not define a mandatory server, database, cloud,
transport, secret store, trust authority, or authorization decision.
"""
from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Iterable, Mapping
from itertools import islice
from typing import Any

from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.values import is_absolute_uri, validate_record_value

from marketplace_record_v1 import BASE

PROFILE_CORE = f"{BASE}/deployment/profile/core-node-v1"
ROLE_TRANSPORT_INGRESS = f"{BASE}/deployment/role/transport-ingress"
ROLE_TRANSPORT_EGRESS = f"{BASE}/deployment/role/transport-egress"
ROLE_EVIDENCE_STORE = f"{BASE}/deployment/role/evidence-store"
ROLE_RESOLVER = f"{BASE}/deployment/role/resolver"
ROLE_POLICY_AUTHORIZATION = f"{BASE}/deployment/role/policy-authorization"
ROLE_EVALUATOR = f"{BASE}/deployment/role/evaluator"
ROLE_SIDE_EFFECT_EXECUTOR = f"{BASE}/deployment/role/side-effect-executor"
ROLE_DIAGNOSTICS = f"{BASE}/deployment/role/diagnostics"
MODE_READ_ONLY = "READ_ONLY"
MODE_SIDE_EFFECT = "SIDE_EFFECT"
SERVICE_MODES = frozenset({MODE_READ_ONLY, MODE_SIDE_EFFECT})
COMPONENT_STATUSES = frozenset({"READY", "DEGRADED", "FAILED", "UNKNOWN"})
READINESS_STATES = frozenset({"READY", "DEGRADED", "NOT_READY"})

MAX_COMPONENTS = 256
MAX_SERVICES = 256
MAX_SET_ITEMS = 256
MAX_CONTEXT_ENTRIES = 128
MAX_URI_BYTES = 2048
MAX_OBSERVATIONS = 1024

_SECRET_KEY_RE = re.compile(
    r"(?:^|[/:#._-])(secret|password|token|credential|api[-_]?key|private[-_]?key|client[-_]?secret)(?:$|[/?#._=&-])",
    re.IGNORECASE,
)

_BOUNDARY_FIELDS = (
    "endpoint_reachability_established",
    "operator_authority_established",
    "transport_security_established",
    "external_service_availability_established",
    "protected_side_effect_authorized",
    "marketplace_record_identity_affected",
    "secret_material_absence_established",
    "global_marketplace_role_established",
    "result_authentication_established",
)


class MarketplaceDeploymentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceDeploymentError(code, message)

def _b64url_digest(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def _bounded_tuple(values: Iterable[Any], limit: int, path: str) -> tuple[Any, ...]:
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        fail("INVALID_DEPLOYMENT_LIMIT", f"{path} limit MUST be a positive integer")
    if isinstance(values, (str, bytes, bytearray, Mapping)) or not isinstance(values, Iterable):
        fail("INVALID_DEPLOYMENT_COLLECTION", f"{path} MUST be an ordered collection")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail("DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds limit {limit}")
    return items


def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_DEPLOYMENT_URI", f"{path} MUST be an absolute URI")
    if len(value.encode("utf-8")) > MAX_URI_BYTES:
        fail("DEPLOYMENT_RESOURCE_LIMIT_EXCEEDED", f"{path} URI is too long")
    return value


def _sorted_unique_uris(
    values: Iterable[Any], path: str, *, allow_empty: bool = True
) -> tuple[str, ...]:
    items = _bounded_tuple(values, MAX_SET_ITEMS, path)
    if not allow_empty and not items:
        fail("EMPTY_DEPLOYMENT_SET", f"{path} MUST be non-empty")
    out = tuple(_require_uri(item, f"{path}[]") for item in items)
    if len(out) != len(set(out)):
        fail("NONCANONICAL_DEPLOYMENT_SET", f"{path} MUST be duplicate-free")
    if out != tuple(sorted(out, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_DEPLOYMENT_SET", f"{path} MUST be UTF-8 sorted")
    return out

def _reject_secret_like_keys(value: Any, path: str = "deployment") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and _SECRET_KEY_RE.search(key):
                fail("SECRET_MATERIAL_FIELD_FORBIDDEN", f"{path} contains secret-like field {key!r}")
            _reject_secret_like_keys(item, f"{path}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _reject_secret_like_keys(item, f"{path}[{index}]")


def _validate_context(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or len(value) > MAX_CONTEXT_ENTRIES:
        fail("INVALID_DEPLOYMENT_CONTEXT", "context MUST be a bounded map")
    _reject_secret_like_keys(value, "context")
    out: dict[str, Any] = {}
    for key, item in value.items():
        uri = _require_uri(key, "context key")
        try:
            validate_record_value(item, path=f"context[{uri!r}]")
        except Exception as exc:
            fail("INVALID_DEPLOYMENT_CONTEXT", f"invalid OLP context value: {exc}")
        out[uri] = item
    return dict(sorted(out.items(), key=lambda pair: pair[0].encode("utf-8")))


def _validate_component(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DEPLOYMENT_COMPONENT", "component MUST be a map")
    required = {"id", "role", "adapter", "required", "critical"}
    if set(value) != required or not isinstance(value["required"], bool):
        fail("INVALID_DEPLOYMENT_COMPONENT", "component shape is invalid")
    return {
        "id": _require_uri(value["id"], "component.id"),
        "role": _require_uri(value["role"], "component.role"),
        "adapter": _require_uri(value["adapter"], "component.adapter"),
        "required": value["required"],
        "critical": _sorted_unique_uris(value["critical"], "component.critical"),
    }

def _validate_service(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DEPLOYMENT_SERVICE", "service MUST be a map")
    required = {
        "id", "capability", "mode", "required", "required_roles", "endpoints", "critical"
    }
    if set(value) != required or not isinstance(value["required"], bool):
        fail("INVALID_DEPLOYMENT_SERVICE", "service shape is invalid")
    mode = value["mode"]
    if not isinstance(mode, str) or mode not in SERVICE_MODES:
        fail("INVALID_DEPLOYMENT_SERVICE", "service mode is unsupported")
    roles = _sorted_unique_uris(
        value["required_roles"], "service.required_roles", allow_empty=False
    )
    if mode == MODE_SIDE_EFFECT:
        needed = {ROLE_POLICY_AUTHORIZATION, ROLE_SIDE_EFFECT_EXECUTOR}
        if not needed.issubset(roles):
            fail(
                "SIDE_EFFECT_AUTHORIZATION_GATE_REQUIRED",
                "side-effect service MUST depend on policy authorization and side-effect executor roles",
            )
    return {
        "id": _require_uri(value["id"], "service.id"),
        "capability": _require_uri(value["capability"], "service.capability"),
        "mode": mode,
        "required": value["required"],
        "required_roles": roles,
        "endpoints": _sorted_unique_uris(value["endpoints"], "service.endpoints"),
        "critical": _sorted_unique_uris(value["critical"], "service.critical"),
    }


def _require_sorted_unique_items(items: tuple[dict[str, Any], ...], path: str) -> None:
    ids = tuple(item["id"] for item in items)
    if len(ids) != len(set(ids)):
        fail("DUPLICATE_DEPLOYMENT_ID", f"{path} ids MUST be unique")
    if ids != tuple(sorted(ids, key=lambda item: item.encode("utf-8"))):
        fail("NONCANONICAL_DEPLOYMENT_SET", f"{path} MUST be sorted by id")

def validate_deployment_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_DEPLOYMENT_PROFILE", "deployment profile MUST be a map")
    _reject_secret_like_keys(value)
    required = {
        "version", "profile", "deployment_id", "operator", "components",
        "services", "critical", "context",
    }
    if set(value) != required:
        fail("INVALID_DEPLOYMENT_PROFILE", "deployment profile shape is invalid")
    if isinstance(value["version"], bool) or value["version"] != 1:
        fail("INVALID_DEPLOYMENT_PROFILE", "version MUST be exact integer 1")
    profile = _require_uri(value["profile"], "profile")
    if profile != PROFILE_CORE:
        fail("UNSUPPORTED_DEPLOYMENT_PROFILE", "reference helper supports only PROFILE_CORE")
    components_raw = _bounded_tuple(value["components"], MAX_COMPONENTS, "components")
    services_raw = _bounded_tuple(value["services"], MAX_SERVICES, "services")
    if not components_raw or not services_raw:
        fail("EMPTY_DEPLOYMENT_SET", "components and services MUST be non-empty")
    components = tuple(_validate_component(item) for item in components_raw)
    services = tuple(_validate_service(item) for item in services_raw)
    _require_sorted_unique_items(components, "components")
    _require_sorted_unique_items(services, "services")
    roles = {item["role"] for item in components}
    for service in services:
        missing = set(service["required_roles"]) - roles
        if missing:
            fail("UNBACKED_SERVICE_ROLE", "service requires an unconfigured component role")
    return {
        "version": 1,
        "profile": profile,
        "deployment_id": _require_uri(value["deployment_id"], "deployment_id"),
        "operator": _require_uri(value["operator"], "operator"),
        "components": components,
        "services": services,
        "critical": _sorted_unique_uris(value["critical"], "critical"),
        "context": _validate_context(value["context"]),
    }


def deployment_config_fingerprint(value: Any) -> str:
    return _b64url_digest(olp_encode(validate_deployment_profile(value)))

def _validate_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_COMPONENT_OBSERVATION", "component observation MUST be a map")
    required = {"component_id", "adapter", "status", "critical"}
    if set(value) != required:
        fail("INVALID_COMPONENT_OBSERVATION", "component observation shape is invalid")
    status = value["status"]
    if not isinstance(status, str) or status not in COMPONENT_STATUSES:
        fail("INVALID_COMPONENT_STATUS", "component status is unsupported")
    return {
        "component_id": _require_uri(value["component_id"], "observation.component_id"),
        "adapter": _require_uri(value["adapter"], "observation.adapter"),
        "status": status,
        "critical": _sorted_unique_uris(value["critical"], "observation.critical"),
    }


def _normalize_observations(
    values: Iterable[Any], descriptor: Mapping[str, Any]
) -> tuple[tuple[dict[str, Any], ...], int]:
    items = _bounded_tuple(values, MAX_OBSERVATIONS, "observations")
    configured = {item["id"] for item in descriptor["components"]}
    by_component: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for raw in items:
        item = _validate_observation(raw)
        component_id = item["component_id"]
        if component_id not in configured:
            fail("UNKNOWN_COMPONENT_OBSERVATION", "observation names an unconfigured component")
        prior = by_component.get(component_id)
        if prior is None:
            by_component[component_id] = item
        elif prior == item:
            duplicate_count += 1
        else:
            fail("COMPONENT_OBSERVATION_CONFLICT", "same component has conflicting observations")
    ordered = tuple(
        by_component[key]
        for key in sorted(by_component, key=lambda value: value.encode("utf-8"))
    )
    return ordered, duplicate_count


def _component_trace(
    descriptor: Mapping[str, Any],
    observations: tuple[dict[str, Any], ...],
    understood_critical: set[str],
) -> tuple[dict[str, Any], ...]:
    by_component = {item["component_id"]: item for item in observations}
    traces: list[dict[str, Any]] = []
    for component in descriptor["components"]:
        observation = by_component.get(component["id"])
        reasons: list[str] = []
        if observation is None:
            state = "UNKNOWN"
            reasons.append("MISSING_OBSERVATION")
            observation_critical: tuple[str, ...] = ()
            observed_adapter = None
        else:
            observed_adapter = observation["adapter"]
            observation_critical = observation["critical"]
            unknown_critical = (
                set(component["critical"]) | set(observation_critical)
            ) - understood_critical
            if observed_adapter != component["adapter"]:
                state = "FAILED"
                reasons.append("ADAPTER_BINDING_MISMATCH")
            elif unknown_critical:
                state = "UNKNOWN"
                reasons.append("UNKNOWN_CRITICAL_DEPLOYMENT_SEMANTICS")
            else:
                state = observation["status"]
                if state == "DEGRADED":
                    reasons.append("COMPONENT_DEGRADED")
                elif state == "FAILED":
                    reasons.append("COMPONENT_FAILED")
                elif state == "UNKNOWN":
                    reasons.append("COMPONENT_STATUS_UNKNOWN")
        traces.append({
            "component_id": component["id"],
            "role": component["role"],
            "configured_adapter": component["adapter"],
            "observed_adapter": observed_adapter,
            "required": component["required"],
            "critical": component["critical"],
            "observation_critical": observation_critical,
            "state": state,
            "reasons": tuple(sorted(set(reasons))),
        })
    return tuple(traces)

def _role_state(role: str, component_trace: tuple[dict[str, Any], ...]) -> str:
    states = [item["state"] for item in component_trace if item["role"] == role]
    if not states:
        return "FAILED"
    if "READY" in states:
        return "READY"
    if "DEGRADED" in states:
        return "DEGRADED"
    if "UNKNOWN" in states:
        return "UNKNOWN"
    return "FAILED"


def _service_trace(
    descriptor: Mapping[str, Any],
    component_trace: tuple[dict[str, Any], ...],
    understood_critical: set[str],
) -> tuple[dict[str, Any], ...]:
    traces: list[dict[str, Any]] = []
    for service in descriptor["services"]:
        role_states = tuple(
            (role, _role_state(role, component_trace))
            for role in service["required_roles"]
        )
        unknown_critical = set(service["critical"]) - understood_critical
        reasons: list[str] = []
        if unknown_critical:
            state = "UNRESOLVED"
            reasons.append("UNKNOWN_CRITICAL_DEPLOYMENT_SEMANTICS")
        elif any(status == "FAILED" for _, status in role_states):
            state = "UNAVAILABLE"
            reasons.append("REQUIRED_ROLE_FAILED")
        elif any(status == "UNKNOWN" for _, status in role_states):
            state = "UNRESOLVED"
            reasons.append("REQUIRED_ROLE_UNRESOLVED")
        elif any(status == "DEGRADED" for _, status in role_states):
            state = "DEGRADED"
            reasons.append("SERVICE_BACKING_DEGRADED")
        else:
            state = "READY"
        traces.append({
            "service_id": service["id"],
            "capability": service["capability"],
            "mode": service["mode"],
            "required": service["required"],
            "required_roles": service["required_roles"],
            "role_states": role_states,
            "endpoints": service["endpoints"],
            "critical": service["critical"],
            "state": state,
            "reasons": tuple(sorted(set(reasons))),
        })
    return tuple(traces)


def _overall_readiness(
    descriptor: Mapping[str, Any],
    component_trace: tuple[dict[str, Any], ...],
    service_trace: tuple[dict[str, Any], ...],
    understood_critical: set[str],
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if set(descriptor["critical"]) - understood_critical:
        reasons.append("UNKNOWN_CRITICAL_DEPLOYMENT_SEMANTICS")
    required_components = [item for item in component_trace if item["required"]]
    required_services = [item for item in service_trace if item["required"]]
    if any(item["state"] in {"FAILED", "UNKNOWN"} for item in required_components):
        reasons.append("REQUIRED_COMPONENT_NOT_READY")
    if any(item["state"] in {"UNAVAILABLE", "UNRESOLVED"} for item in required_services):
        reasons.append("REQUIRED_SERVICE_NOT_READY")
    if reasons:
        return "NOT_READY", tuple(sorted(set(reasons)))
    degraded = any(item["state"] != "READY" for item in component_trace) or any(
        item["state"] != "READY" for item in service_trace
    )
    if degraded:
        return "DEGRADED", ("OPTIONAL_OR_REQUIRED_PATH_DEGRADED",)
    return "READY", ()

_RESULT_CORE_FIELDS = (
    "version", "profile", "deployment_id", "operator", "understood_critical",
    "component_trace", "service_trace", "advertised_capabilities",
    "degraded_capabilities", "readiness", "reasons", "duplicate_observations",
    "config_fingerprint", "input_fingerprint",
)


def _normalized_input(
    profile: Any,
    observations: Iterable[Any],
    understood_critical: Iterable[Any],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[str, ...], int]:
    descriptor = validate_deployment_profile(profile)
    understood = _sorted_unique_uris(understood_critical, "understood_critical")
    normalized_observations, duplicates = _normalize_observations(observations, descriptor)
    return descriptor, normalized_observations, understood, duplicates


def deployment_input_fingerprint(
    profile: Any,
    observations: Iterable[Any],
    understood_critical: Iterable[Any] = (),
) -> str:
    descriptor, normalized_observations, understood, _ = _normalized_input(
        profile, observations, understood_critical
    )
    return _b64url_digest(olp_encode({
        "profile": descriptor,
        "observations": normalized_observations,
        "understood_critical": understood,
    }))

def evaluate_deployment_readiness(
    profile: Any,
    observations: Iterable[Any],
    understood_critical: Iterable[Any] = (),
) -> dict[str, Any]:
    descriptor, normalized_observations, understood, duplicates = _normalized_input(
        profile, observations, understood_critical
    )
    understood_set = set(understood)
    component_trace = _component_trace(descriptor, normalized_observations, understood_set)
    service_trace = _service_trace(descriptor, component_trace, understood_set)
    readiness, reasons = _overall_readiness(
        descriptor, component_trace, service_trace, understood_set
    )
    global_critical_unresolved = bool(set(descriptor["critical"]) - understood_set)
    advertised = () if global_critical_unresolved else tuple(sorted({
        item["capability"] for item in service_trace if item["state"] == "READY"
    }, key=lambda value: value.encode("utf-8")))
    degraded = () if global_critical_unresolved else tuple(sorted({
        item["capability"] for item in service_trace if item["state"] == "DEGRADED"
    }, key=lambda value: value.encode("utf-8")))
    config_fp = _b64url_digest(olp_encode(descriptor))
    input_fp = _b64url_digest(olp_encode({
        "profile": descriptor,
        "observations": normalized_observations,
        "understood_critical": understood,
    }))
    core = {
        "version": 1,
        "profile": descriptor["profile"],
        "deployment_id": descriptor["deployment_id"],
        "operator": descriptor["operator"],
        "understood_critical": understood,
        "component_trace": component_trace,
        "service_trace": service_trace,
        "advertised_capabilities": advertised,
        "degraded_capabilities": degraded,
        "readiness": readiness,
        "reasons": reasons,
        "duplicate_observations": duplicates,
        "config_fingerprint": config_fp,
        "input_fingerprint": input_fp,
    }
    result_fp = _b64url_digest(olp_encode(core))
    return {
        **core,
        "result_fingerprint": result_fp,
        **{field: False for field in _BOUNDARY_FIELDS},
    }

def validate_deployment_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("INVALID_PRIOR_DEPLOYMENT_RESULT", "deployment result MUST be a map")
    required = set(_RESULT_CORE_FIELDS) | set(_BOUNDARY_FIELDS) | {"result_fingerprint"}
    if set(value) != required:
        fail("INVALID_PRIOR_DEPLOYMENT_RESULT", "deployment result shape is invalid")
    if value["readiness"] not in READINESS_STATES:
        fail("INVALID_PRIOR_DEPLOYMENT_RESULT", "deployment readiness is unsupported")
    if any(value[field] is not False for field in _BOUNDARY_FIELDS):
        fail("INVALID_PRIOR_DEPLOYMENT_RESULT", "deployment result boundary flags are inconsistent")
    core = {field: value[field] for field in _RESULT_CORE_FIELDS}
    expected = _b64url_digest(olp_encode(core))
    if value["result_fingerprint"] != expected:
        fail("DEPLOYMENT_RESULT_INTEGRITY_MISMATCH", "result fingerprint does not match result content")
    return dict(value)


def evaluate_deployment_reuse(
    prior_result: Any,
    current_profile: Any,
    current_observations: Iterable[Any],
    understood_critical: Iterable[Any] = (),
) -> dict[str, Any]:
    prior = validate_deployment_result(prior_result)
    current_config = deployment_config_fingerprint(current_profile)
    current_input = deployment_input_fingerprint(
        current_profile, current_observations, understood_critical
    )
    reasons: list[str] = []
    if prior["config_fingerprint"] != current_config:
        reasons.append("DEPLOYMENT_CONFIGURATION_CHANGED")
    if prior["input_fingerprint"] != current_input:
        reasons.append("DEPLOYMENT_OBSERVATIONS_CHANGED")
    return {
        "reuse_status": "REUSABLE" if not reasons else "NOT_REUSABLE",
        "reasons": tuple(reasons),
        "current_config_fingerprint": current_config,
        "current_input_fingerprint": current_input,
        "prior_result_fingerprint": prior["result_fingerprint"],
        "prior_result_authentication_evaluated": False,
        "reuse_establishes_external_reachability": False,
        "reuse_authorizes_protected_side_effect": False,
    }
