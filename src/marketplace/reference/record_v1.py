"""Non-normative Marketplace Record Representation v1 validation helpers.

This module validates Marketplace-specific semantic content only. OLP remains
responsible for RecordV1 validation, canonical identity encoding, hashing,
proofs, relationships, and lifecycle semantics.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.model.bundle import ResourceRefV1
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.values import is_absolute_uri, validate_record_value

BASE = "https://open-trust-layer.github.io/marketplace/semantics/v1"
CORE_PROFILE = f"{BASE}/profile/core-v1"
PROPOSAL_PROFILE = f"{BASE}/profile/proposal-v1"
TYPE_INTENT = f"{BASE}/record/market-intent"
TYPE_AGREEMENT = f"{BASE}/record/market-agreement"
TYPE_EVENT = f"{BASE}/record/market-event"
RECORD_TYPES = {TYPE_INTENT, TYPE_AGREEMENT, TYPE_EVENT}

_LOCAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class MarketplaceConformanceError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceConformanceError(code, message)


def _map(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        fail("TYPE_MISMATCH", f"{path} MUST be a map")
    if any(not isinstance(k, str) for k in value):
        fail("MAP_KEY_TYPE", f"{path} keys MUST be text strings")
    return value


def _array(value: Any, path: str, *, nonempty: bool = False) -> tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        fail("TYPE_MISMATCH", f"{path} MUST be an array")
    out = tuple(value)
    if nonempty and not out:
        fail("EMPTY_ARRAY", f"{path} MUST be non-empty")
    return out


def _keys(value: Mapping[str, Any], allowed: set[str], required: set[str], path: str) -> None:
    missing = required - set(value)
    if missing:
        fail("MISSING_FIELD", f"{path} missing {sorted(missing)!r}")
    unknown = set(value) - allowed
    if unknown:
        fail("UNKNOWN_FIELD", f"{path} unknown fields {sorted(unknown)!r}")


def _uri(value: Any, path: str) -> str:
    if not is_absolute_uri(value):
        fail("INVALID_URI", f"{path} MUST be an absolute URI")
    return value


def _text(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        fail("INVALID_TEXT", f"{path} MUST be {'non-empty ' if nonempty else ''}text")
    try:
        validate_record_value(value, path=path)
    except Exception as exc:
        fail("INVALID_TEXT", f"{path} is not valid OLP text: {exc}")
    return value


def _semantic_map(value: Any, path: str, *, allow_empty: bool = True) -> Mapping[str, Any]:
    m = _map(value, path)
    if not allow_empty and not m:
        fail("EMPTY_MAP", f"{path} MUST be non-empty")
    for key, item in m.items():
        _uri(key, f"{path} key")
        try:
            validate_record_value(item, path=f"{path}[{key!r}]")
        except Exception as exc:
            fail("INVALID_OLP_VALUE", f"{path}[{key!r}] is not an OLP value: {exc}")
    return m


def _canonical_set(items: Sequence[Any], path: str) -> tuple[Any, ...]:
    encoded = [olp_encode(item) for item in items]
    if len(set(encoded)) != len(encoded):
        fail("DUPLICATE_SET_MEMBER", f"{path} contains duplicates")
    if encoded != sorted(encoded):
        fail("NON_CANONICAL_ORDER", f"{path} MUST be sorted by OLP-CIE-1 bytes")
    return tuple(items)


def _sorted_unique_text(items: Sequence[Any], path: str) -> tuple[str, ...]:
    vals = tuple(_text(v, f"{path}[]") for v in items)
    if len(vals) != len(set(vals)):
        fail("DUPLICATE_SET_MEMBER", f"{path} contains duplicates")
    if vals != tuple(sorted(vals, key=lambda s: s.encode("utf-8"))):
        fail("NON_CANONICAL_ORDER", f"{path} MUST be UTF-8 byte sorted")
    return vals


def validate_record_ref(value: Any, path: str, *, allow_proof: bool = False) -> EvidenceRefV1:
    try:
        ref = EvidenceRefV1.from_value(value)
    except Exception as exc:
        fail("INVALID_EVIDENCE_REF", f"{path}: {exc}")
    if not allow_proof and ref.kind != EvidenceKind.RECORD:
        fail("WRONG_REFERENCE_KIND", f"{path} MUST reference an OLP Record")
    return ref


def validate_resource_ref(value: Any, path: str) -> ResourceRefV1:
    try:
        return ResourceRefV1.from_value(value)
    except Exception as exc:
        fail("INVALID_RESOURCE_REF", f"{path}: {exc}")


def validate_party(value: Any, path: str = "party") -> None:
    m = _map(value, path)
    _keys(m, {"principal", "role"}, {"principal"}, path)
    _uri(m["principal"], f"{path}.principal")
    if "role" in m:
        _uri(m["role"], f"{path}.role")


def validate_subject(value: Any, path: str = "subject") -> None:
    m = _map(value, path)
    _keys(m, {"uri", "record_ref", "resource_ref", "qualifiers"}, set(), path)
    targets = [k for k in ("uri", "record_ref", "resource_ref") if k in m]
    if len(targets) != 1:
        fail("SUBJECT_TARGET_CARDINALITY", f"{path} MUST contain exactly one target")
    if "uri" in m:
        _uri(m["uri"], f"{path}.uri")
    if "record_ref" in m:
        validate_record_ref(m["record_ref"], f"{path}.record_ref")
    if "resource_ref" in m:
        validate_resource_ref(m["resource_ref"], f"{path}.resource_ref")
    if "qualifiers" in m:
        _semantic_map(m["qualifiers"], f"{path}.qualifiers", allow_empty=False)


def validate_action(value: Any, path: str = "action") -> None:
    m = _map(value, path)
    _keys(m, {"id", "parameters"}, {"id"}, path)
    _uri(m["id"], f"{path}.id")
    if "parameters" in m:
        _semantic_map(m["parameters"], f"{path}.parameters", allow_empty=False)


def validate_terms(value: Any, path: str = "terms") -> None:
    _semantic_map(value, path, allow_empty=True)


def validate_constraint(value: Any, path: str = "constraint") -> None:
    m = _map(value, path)
    _keys(m, {"id", "mode", "value"}, {"id", "mode"}, path)
    _uri(m["id"], f"{path}.id")
    if m["mode"] not in {"mandatory", "preferred", "negotiable", "informational"}:
        fail("INVALID_ENUM", f"{path}.mode is invalid")
    if "value" in m:
        try:
            validate_record_value(m["value"], path=f"{path}.value")
        except Exception as exc:
            fail("INVALID_OLP_VALUE", f"{path}.value: {exc}")


def validate_decimal(value: Any, path: str = "decimal") -> None:
    m = _map(value, path)
    _keys(m, {"coefficient", "scale"}, {"coefficient", "scale"}, path)
    c, s = m["coefficient"], m["scale"]
    if isinstance(c, bool) or not isinstance(c, int):
        fail("INVALID_DECIMAL", f"{path}.coefficient MUST be integer")
    try:
        validate_record_value(c, path=f"{path}.coefficient")
    except Exception as exc:
        fail("INVALID_DECIMAL", f"{path}.coefficient is outside the OLP integer domain: {exc}")
    if isinstance(s, bool) or not isinstance(s, int) or not 0 <= s <= 18:
        fail("INVALID_DECIMAL", f"{path}.scale MUST be integer 0..18")
    if c == 0 and s != 0:
        fail("NON_CANONICAL_DECIMAL", f"{path}: zero MUST use scale 0")
    if s > 0 and c % 10 == 0:
        fail("NON_CANONICAL_DECIMAL", f"{path}: trailing decimal zero is forbidden")


def validate_quantity(value: Any, path: str = "quantity") -> None:
    m = _map(value, path)
    _keys(m, {"value", "unit"}, {"value", "unit"}, path)
    validate_decimal(m["value"], f"{path}.value")
    _uri(m["unit"], f"{path}.unit")


def validate_value_expression(value: Any, path: str = "value_expression") -> None:
    m = _map(value, path)
    kind = m.get("kind")
    if kind == "monetary":
        _keys(m, {"kind", "amount", "currency_code", "currency_uri"}, {"kind", "amount"}, path)
        validate_decimal(m["amount"], f"{path}.amount")
        currencies = [k for k in ("currency_code", "currency_uri") if k in m]
        if len(currencies) != 1:
            fail("CURRENCY_CARDINALITY", f"{path} MUST identify exactly one currency")
        if "currency_code" in m and (not isinstance(m["currency_code"], str) or not _CURRENCY_RE.fullmatch(m["currency_code"])):
            fail("INVALID_CURRENCY", f"{path}.currency_code MUST be three uppercase ASCII letters")
        if "currency_uri" in m:
            _uri(m["currency_uri"], f"{path}.currency_uri")
    elif kind == "quantity":
        _keys(m, {"kind", "quantity"}, {"kind", "quantity"}, path)
        validate_quantity(m["quantity"], f"{path}.quantity")
    elif kind == "semantic":
        _keys(m, {"kind", "semantic", "value"}, {"kind", "semantic", "value"}, path)
        _uri(m["semantic"], f"{path}.semantic")
        try:
            validate_record_value(m["value"], path=f"{path}.value")
        except Exception as exc:
            fail("INVALID_OLP_VALUE", f"{path}.value: {exc}")
    else:
        fail("INVALID_ENUM", f"{path}.kind is invalid")


def _timestamp(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
        fail("INVALID_TIMESTAMP", f"{path} MUST use YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        fail("INVALID_TIMESTAMP", f"{path}: {exc}")


def validate_temporal(value: Any, path: str = "temporal") -> None:
    m = _map(value, path)
    _keys(m, {"not_before", "not_after"}, set(), path)
    if not m:
        fail("EMPTY_MAP", f"{path} MUST contain a bound")
    lo = _timestamp(m["not_before"], f"{path}.not_before") if "not_before" in m else None
    hi = _timestamp(m["not_after"], f"{path}.not_after") if "not_after" in m else None
    if lo is not None and hi is not None and lo > hi:
        fail("INVALID_INTERVAL", f"{path}.not_before MUST NOT exceed not_after")


def validate_location(value: Any, path: str = "location") -> None:
    m = _map(value, path)
    _keys(m, {"scheme", "value"}, {"scheme", "value"}, path)
    _uri(m["scheme"], f"{path}.scheme")
    try:
        validate_record_value(m["value"], path=f"{path}.value")
    except Exception as exc:
        fail("INVALID_OLP_VALUE", f"{path}.value: {exc}")


def validate_evidence_requirement(value: Any, path: str = "evidence_requirement") -> None:
    m = _map(value, path)
    _keys(m, {"profile", "mode", "subject"}, {"profile", "mode"}, path)
    _uri(m["profile"], f"{path}.profile")
    if m["mode"] not in {"required", "preferred"}:
        fail("INVALID_ENUM", f"{path}.mode is invalid")
    if "subject" in m:
        validate_subject(m["subject"], f"{path}.subject")


def validate_settlement_preference(value: Any, path: str = "settlement_preference") -> None:
    m = _map(value, path)
    _keys(m, {"method", "mode", "parameters"}, {"method", "mode"}, path)
    _uri(m["method"], f"{path}.method")
    if m["mode"] not in {"accepted", "preferred", "required", "excluded"}:
        fail("INVALID_ENUM", f"{path}.mode is invalid")
    if "parameters" in m:
        _semantic_map(m["parameters"], f"{path}.parameters", allow_empty=False)


def validate_acceptance_criterion(value: Any, path: str = "acceptance_criterion") -> None:
    m = _map(value, path)
    _keys(m, {"criterion", "mode", "parameters"}, {"criterion", "mode"}, path)
    _uri(m["criterion"], f"{path}.criterion")
    if m["mode"] not in {"required", "informational"}:
        fail("INVALID_ENUM", f"{path}.mode is invalid")
    if "parameters" in m:
        _semantic_map(m["parameters"], f"{path}.parameters", allow_empty=False)


def validate_profile_binding(value: Any, path: str = "profile_binding") -> None:
    m = _map(value, path)
    _keys(m, {"profile", "parameters"}, {"profile"}, path)
    _uri(m["profile"], f"{path}.profile")
    if "parameters" in m:
        _semantic_map(m["parameters"], f"{path}.parameters", allow_empty=False)


def validate_commitment(value: Any, path: str = "commitment") -> None:
    m = _map(value, path)
    _keys(m, {"id", "party", "action", "subjects", "terms", "acceptance_criteria"}, {"id", "party", "action"}, path)
    if not isinstance(m["id"], str) or not _LOCAL_ID_RE.fullmatch(m["id"]):
        fail("INVALID_LOCAL_ID", f"{path}.id is invalid")
    validate_party(m["party"], f"{path}.party")
    validate_action(m["action"], f"{path}.action")
    if "subjects" in m:
        vals = _array(m["subjects"], f"{path}.subjects", nonempty=True)
        for i, item in enumerate(vals): validate_subject(item, f"{path}.subjects[{i}]")
        _canonical_set(vals, f"{path}.subjects")
    if "terms" in m:
        validate_terms(m["terms"], f"{path}.terms")
    if "acceptance_criteria" in m:
        vals = _array(m["acceptance_criteria"], f"{path}.acceptance_criteria", nonempty=True)
        for i, item in enumerate(vals): validate_acceptance_criterion(item, f"{path}.acceptance_criteria[{i}]")
        _canonical_set(vals, f"{path}.acceptance_criteria")


def validate_commitment_ref(value: Any, path: str = "commitment_ref") -> None:
    m = _map(value, path)
    _keys(m, {"record", "id"}, {"record", "id"}, path)
    validate_record_ref(m["record"], f"{path}.record")
    if not isinstance(m["id"], str) or not _LOCAL_ID_RE.fullmatch(m["id"]):
        fail("INVALID_LOCAL_ID", f"{path}.id is invalid")


def validate_outcome(value: Any, path: str = "outcome") -> None:
    m = _map(value, path)
    _keys(m, {"type", "details"}, {"type"}, path)
    _uri(m["type"], f"{path}.type")
    if "details" in m:
        try: validate_record_value(m["details"], path=f"{path}.details")
        except Exception as exc: fail("INVALID_OLP_VALUE", f"{path}.details: {exc}")


def _validate_extensions(m: Mapping[str, Any], path: str) -> None:
    extensions = m.get("extensions", {})
    critical = m.get("critical", ())
    if "extensions" in m:
        _semantic_map(extensions, f"{path}.extensions", allow_empty=False)
    if "critical" in m:
        vals = _sorted_unique_text(_array(critical, f"{path}.critical", nonempty=True), f"{path}.critical")
        for uri in vals:
            _uri(uri, f"{path}.critical[]")
            if uri not in extensions:
                fail("CRITICAL_EXTENSION_MISSING", f"{path}: critical URI is not present in extensions")


def _validate_common_record(record: RecordV1) -> Mapping[str, Any]:
    try:
        record.validate()
    except Exception as exc:
        fail("INVALID_OLP_RECORD", str(exc))
    if record.type not in RECORD_TYPES:
        fail("UNSUPPORTED_MARKET_RECORD_TYPE", f"unsupported Marketplace type {record.type!r}")
    if CORE_PROFILE not in record.profiles:
        fail("CORE_PROFILE_REQUIRED", "Marketplace core-v1 profile is required")
    for profile in record.profiles:
        _uri(profile, "record.profiles[]")
    return _map(record.content, "content")


def _validate_intent(record: RecordV1, m: Mapping[str, Any]) -> None:
    allowed = {"version", "issuer", "subjects", "action", "terms", "constraints", "commitments", "evidence_requirements", "validity", "settlement_preferences", "profile_bindings", "response_to", "extensions", "critical"}
    _keys(m, allowed, {"version", "issuer", "subjects", "action", "terms"}, "content")
    if m["version"] != 1 or isinstance(m["version"], bool): fail("UNSUPPORTED_CONTENT_VERSION", "content.version MUST equal integer 1")
    validate_party(m["issuer"], "content.issuer")
    subjects = _array(m["subjects"], "content.subjects", nonempty=True)
    for i, item in enumerate(subjects): validate_subject(item, f"content.subjects[{i}]")
    _canonical_set(subjects, "content.subjects")
    validate_action(m["action"], "content.action")
    validate_terms(m["terms"], "content.terms")
    for key, fn in (("constraints", validate_constraint), ("evidence_requirements", validate_evidence_requirement), ("settlement_preferences", validate_settlement_preference), ("profile_bindings", validate_profile_binding)):
        if key in m:
            vals = _array(m[key], f"content.{key}", nonempty=True)
            for i, item in enumerate(vals): fn(item, f"content.{key}[{i}]")
            _canonical_set(vals, f"content.{key}")
    if "commitments" in m:
        commitments = _array(m["commitments"], "content.commitments", nonempty=True)
        for i, item in enumerate(commitments): validate_commitment(item, f"content.commitments[{i}]")
        ids = tuple(item["id"] for item in commitments)
        _sorted_unique_text(ids, "content.commitments ids")
        issuer_principal = m["issuer"]["principal"]
        for c in commitments:
            if c["party"]["principal"] != issuer_principal:
                fail("INTENT_COMMITMENT_PARTY_MISMATCH", "intent commitment party principal MUST equal issuer principal")
    if "validity" in m: validate_temporal(m["validity"], "content.validity")
    if PROPOSAL_PROFILE in record.profiles:
        if "response_to" not in m: fail("PROPOSAL_RESPONSE_REQUIRED", "proposal profile requires response_to")
    elif "response_to" in m:
        fail("PROPOSAL_PROFILE_REQUIRED", "response_to requires proposal-v1 profile")
    if "response_to" in m:
        vals = _array(m["response_to"], "content.response_to", nonempty=True)
        for i, item in enumerate(vals): validate_record_ref(item, f"content.response_to[{i}]")
        _canonical_set(vals, "content.response_to")
    _validate_extensions(m, "content")


def _validate_agreement(record: RecordV1, m: Mapping[str, Any]) -> None:
    allowed = {"version", "parties", "subjects", "actions", "terms", "commitments", "source_records", "evidence_requirements", "settlement_preferences", "profile_bindings", "extensions", "critical"}
    required = {"version", "parties", "subjects", "actions", "terms", "commitments"}
    _keys(m, allowed, required, "content")
    if m["version"] != 1 or isinstance(m["version"], bool): fail("UNSUPPORTED_CONTENT_VERSION", "content.version MUST equal integer 1")
    for key, fn in (("parties", validate_party), ("subjects", validate_subject), ("actions", validate_action)):
        vals = _array(m[key], f"content.{key}", nonempty=True)
        for i, item in enumerate(vals): fn(item, f"content.{key}[{i}]")
        _canonical_set(vals, f"content.{key}")
    validate_terms(m["terms"], "content.terms")
    commitments = _array(m["commitments"], "content.commitments", nonempty=True)
    for i, item in enumerate(commitments): validate_commitment(item, f"content.commitments[{i}]")
    ids = tuple(item["id"] for item in commitments)
    _sorted_unique_text(ids, "content.commitments ids")
    party_principals = {p["principal"] for p in m["parties"]}
    for c in commitments:
        if c["party"]["principal"] not in party_principals:
            fail("COMMITMENT_PARTY_NOT_BOUND", "commitment party principal MUST appear in agreement parties")
    if "source_records" in m:
        vals = _array(m["source_records"], "content.source_records", nonempty=True)
        for i, item in enumerate(vals): validate_record_ref(item, f"content.source_records[{i}]")
        _canonical_set(vals, "content.source_records")
    for key, fn in (("evidence_requirements", validate_evidence_requirement), ("settlement_preferences", validate_settlement_preference), ("profile_bindings", validate_profile_binding)):
        if key in m:
            vals = _array(m[key], f"content.{key}", nonempty=True)
            for i, item in enumerate(vals): fn(item, f"content.{key}[{i}]")
            _canonical_set(vals, f"content.{key}")
    _validate_extensions(m, "content")


def _validate_event(record: RecordV1, m: Mapping[str, Any]) -> None:
    allowed = {"version", "issuer", "event", "occurred_at", "subjects", "related_records", "commitment_refs", "parties", "outcome", "evidence", "profile_bindings", "extensions", "critical"}
    _keys(m, allowed, {"version", "issuer", "event"}, "content")
    if m["version"] != 1 or isinstance(m["version"], bool): fail("UNSUPPORTED_CONTENT_VERSION", "content.version MUST equal integer 1")
    validate_party(m["issuer"], "content.issuer")
    _uri(m["event"], "content.event")
    if "occurred_at" in m: _timestamp(m["occurred_at"], "content.occurred_at")
    present_context = False
    if "subjects" in m:
        vals = _array(m["subjects"], "content.subjects", nonempty=True); present_context = True
        for i, item in enumerate(vals): validate_subject(item, f"content.subjects[{i}]")
        _canonical_set(vals, "content.subjects")
    if "related_records" in m:
        vals = _array(m["related_records"], "content.related_records", nonempty=True); present_context = True
        for i, item in enumerate(vals): validate_record_ref(item, f"content.related_records[{i}]")
        _canonical_set(vals, "content.related_records")
    if "commitment_refs" in m:
        vals = _array(m["commitment_refs"], "content.commitment_refs", nonempty=True); present_context = True
        for i, item in enumerate(vals): validate_commitment_ref(item, f"content.commitment_refs[{i}]")
        _canonical_set(vals, "content.commitment_refs")
    if not present_context: fail("EVENT_CONTEXT_REQUIRED", "MarketEvent requires subjects, related_records, or commitment_refs")
    if "parties" in m:
        vals = _array(m["parties"], "content.parties", nonempty=True)
        for i, item in enumerate(vals): validate_party(item, f"content.parties[{i}]")
        _canonical_set(vals, "content.parties")
    if "outcome" in m: validate_outcome(m["outcome"], "content.outcome")
    if "evidence" in m:
        vals = _array(m["evidence"], "content.evidence", nonempty=True)
        for i, item in enumerate(vals): validate_record_ref(item, f"content.evidence[{i}]", allow_proof=True)
        _canonical_set(vals, "content.evidence")
    if "profile_bindings" in m:
        vals = _array(m["profile_bindings"], "content.profile_bindings", nonempty=True)
        for i, item in enumerate(vals): validate_profile_binding(item, f"content.profile_bindings[{i}]")
        _canonical_set(vals, "content.profile_bindings")
    _validate_extensions(m, "content")


def validate_market_record(record: RecordV1) -> None:
    m = _validate_common_record(record)
    if record.type == TYPE_INTENT: _validate_intent(record, m)
    elif record.type == TYPE_AGREEMENT: _validate_agreement(record, m)
    elif record.type == TYPE_EVENT: _validate_event(record, m)


STRUCTURE_VALIDATORS = {
    "PartyBindingV1": validate_party,
    "SubjectBindingV1": validate_subject,
    "ActionDescriptorV1": validate_action,
    "TermsV1": validate_terms,
    "ConstraintV1": validate_constraint,
    "DecimalV1": validate_decimal,
    "QuantityV1": validate_quantity,
    "ValueExpressionV1": validate_value_expression,
    "TemporalConditionV1": validate_temporal,
    "LocationConditionV1": validate_location,
    "EvidenceRequirementV1": validate_evidence_requirement,
    "SettlementPreferenceV1": validate_settlement_preference,
    "AcceptanceCriterionV1": validate_acceptance_criterion,
    "ProfileBindingV1": validate_profile_binding,
    "CommitmentV1": validate_commitment,
    "CommitmentRefV1": validate_commitment_ref,
    "OutcomeV1": validate_outcome,
}
