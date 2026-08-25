"""Shared manifest for Marketplace conformance acceptance tooling."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PIN_RE = re.compile(r"^[0-9a-f]{40}$")
PIN_FILE = Path("conformance/olp-source-pin.txt")


@dataclass(frozen=True)
class ConformanceSuite:
    key: str
    title: str
    validator: str
    generator: str
    vector_file: str
    expected_count: int


SUITES: tuple[ConformanceSuite, ...] = (
    ConformanceSuite("m3", "Record Representation", "validate_record_vectors.py", "generate_record_vectors.py", "record-representation-v1.json", 33),
    ConformanceSuite("m4", "Lifecycle & Negotiation", "validate_lifecycle_vectors.py", "generate_lifecycle_vectors.py", "lifecycle-negotiation-v1.json", 26),
    ConformanceSuite("m5", "Matching & Discovery", "validate_matching_vectors.py", "generate_matching_vectors.py", "matching-discovery-v1.json", 31),
    ConformanceSuite("m6", "Fulfillment & Performance", "validate_fulfillment_vectors.py", "generate_fulfillment_vectors.py", "fulfillment-performance-v1.json", 47),
    ConformanceSuite("m7", "Settlement Interfaces", "validate_settlement_vectors.py", "generate_settlement_vectors.py", "settlement-interfaces-v1.json", 57),
    ConformanceSuite("m8", "Federation Transport", "validate_federation_vectors.py", "generate_federation_vectors.py", "federation-transport-v1.json", 93),
    ConformanceSuite("m9", "Trust Evaluation", "validate_trust_evaluation_vectors.py", "generate_trust_evaluation_vectors.py", "trust-evaluation-v1.json", 56),
    ConformanceSuite("m10", "Privacy & Selective Disclosure", "validate_privacy_vectors.py", "generate_privacy_vectors.py", "privacy-selective-disclosure-v1.json", 52),
    ConformanceSuite("m11", "Safety, Policy & Authorization", "validate_policy_vectors.py", "generate_policy_vectors.py", "safety-policy-authorization-v1.json", 77),
    ConformanceSuite("m13", "Dispute Resolution", "validate_dispute_resolution_vectors.py", "generate_dispute_resolution_vectors.py", "dispute-resolution-v1.json", 82),
    ConformanceSuite("m14", "Deployment Profiles", "validate_deployment_vectors.py", "generate_deployment_vectors.py", "deployment-profiles-v1.json", 87),
    ConformanceSuite("m15", "Domain Evaluator Methods", "validate_domain_evaluator_vectors.py", "generate_domain_evaluator_vectors.py", "domain-evaluator-methods-v1.json", 104),
)

EXPECTED_TOTAL = sum(suite.expected_count for suite in SUITES)


def read_olp_pin(repo_root: Path) -> str:
    """Read and validate the single Marketplace OLP compatibility source pin."""
    path = repo_root / PIN_FILE
    try:
        pin = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ValueError(f"missing OLP source pin file: {path}") from exc
    if not _PIN_RE.fullmatch(pin):
        raise ValueError(f"invalid OLP source pin in {path}: expected 40 lowercase hex characters")
    return pin
