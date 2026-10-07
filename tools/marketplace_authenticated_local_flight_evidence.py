"""Strict offline validator for authenticated local-flight acceptance evidence.

This tool validates a JSON evidence record produced after an operator-authorized
loopback browser flight. It performs no network, browser, database, signing,
deployment, payment, or settlement operation.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Final


PROFILE: Final = "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1"
LOOPBACK_HOST: Final = "127.0.0.1"
FORMATION_SUFFICIENT: Final = "EVIDENCE_SUFFICIENT_FOR_PROFILE"
COMMITMENT_ID: Final = "seller-delivery"
EVIDENCE_KIND: Final = "CLAIMED_COMPLETE_PERFORMANCE"
DISPOSITIONS: Final = frozenset({"STORED", "DUPLICATE"})
MAX_EVIDENCE_BYTES: Final = 64 * 1024

_TOP_KEYS = frozenset(
    {
        "profile",
        "main_commit",
        "ci_run_number",
        "runtime_host",
        "seller_authenticated",
        "buyer_authenticated",
        "listing_record_id",
        "proposal_record_id",
        "acceptance_record_id",
        "agreement_record_id",
        "formation_evidence",
        "missing_principals",
        "agreement_publication",
        "completion",
        "universal_truth",
        "payment_or_settlement_evaluated",
        "public_network_exposed",
        "public_deployment",
    }
)
_PUBLICATION_KEYS = frozenset({"agreement_record_id", "disposition", "change_seq"})
_COMPLETION_KEYS = frozenset(
    {
        "record_id",
        "agreement_record_id",
        "commitment_id",
        "evidence_kind",
        "disposition",
        "change_seq",
    }
)
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class AuthenticatedLocalFlightEvidenceError(ValueError):
    """Stable validation failure without reflecting input values."""

    def __init__(self, code: str) -> None:
        super().__init__("authenticated local-flight evidence validation failed")
        self.code = code


def _fail(code: str) -> None:
    raise AuthenticatedLocalFlightEvidenceError(code)


def _exact_mapping(value: object, keys: frozenset[str], code: str) -> dict[str, object]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _record_id(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 512:
        _fail("EVIDENCE_RECORD_ID_INVALID")
    for character in value:
        point = ord(character)
        if point < 33 or point > 126 or character in "/?#":
            _fail("EVIDENCE_RECORD_ID_INVALID")
    return value


def _disposition(value: object) -> str:
    if type(value) is not str or value not in DISPOSITIONS:
        _fail("EVIDENCE_DISPOSITION_INVALID")
    return value


def _change_seq(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 1:
        _fail("EVIDENCE_CHANGE_SEQ_INVALID")
    return value


def _required_bool(document: dict[str, object], key: str, expected: bool, code: str) -> None:
    value = document[key]
    if type(value) is not bool or value is not expected:
        _fail(code)


def validate_authenticated_local_flight_evidence(value: object) -> dict[str, object]:
    """Validate and return the exact reviewed evidence document."""

    document = _exact_mapping(value, _TOP_KEYS, "EVIDENCE_DOCUMENT_INVALID")

    if document["profile"] != PROFILE:
        _fail("EVIDENCE_PROFILE_INVALID")
    if type(document["main_commit"]) is not str or _COMMIT_SHA.fullmatch(document["main_commit"]) is None:
        _fail("EVIDENCE_MAIN_COMMIT_INVALID")
    if type(document["ci_run_number"]) is not int or document["ci_run_number"] < 1:
        _fail("EVIDENCE_CI_RUN_INVALID")
    if document["runtime_host"] != LOOPBACK_HOST:
        _fail("EVIDENCE_RUNTIME_HOST_INVALID")

    _required_bool(document, "seller_authenticated", True, "EVIDENCE_SELLER_AUTH_INVALID")
    _required_bool(document, "buyer_authenticated", True, "EVIDENCE_BUYER_AUTH_INVALID")

    identity_keys = (
        "listing_record_id",
        "proposal_record_id",
        "acceptance_record_id",
        "agreement_record_id",
    )
    identities = tuple(_record_id(document[key]) for key in identity_keys)
    if len(set(identities)) != len(identities):
        _fail("EVIDENCE_RECORD_ID_COLLISION")

    if document["formation_evidence"] != FORMATION_SUFFICIENT:
        _fail("EVIDENCE_FORMATION_INVALID")
    if document["missing_principals"] != []:
        _fail("EVIDENCE_MISSING_PRINCIPALS_INVALID")

    agreement_id = document["agreement_record_id"]
    publication = _exact_mapping(
        document["agreement_publication"],
        _PUBLICATION_KEYS,
        "EVIDENCE_PUBLICATION_INVALID",
    )
    if _record_id(publication["agreement_record_id"]) != agreement_id:
        _fail("EVIDENCE_AGREEMENT_MISMATCH")
    _disposition(publication["disposition"])
    _change_seq(publication["change_seq"])

    completion = _exact_mapping(
        document["completion"],
        _COMPLETION_KEYS,
        "EVIDENCE_COMPLETION_INVALID",
    )
    completion_record_id = _record_id(completion["record_id"])
    if completion_record_id in set(identities):
        _fail("EVIDENCE_RECORD_ID_COLLISION")
    if _record_id(completion["agreement_record_id"]) != agreement_id:
        _fail("EVIDENCE_AGREEMENT_MISMATCH")
    if completion["commitment_id"] != COMMITMENT_ID:
        _fail("EVIDENCE_COMMITMENT_INVALID")
    if completion["evidence_kind"] != EVIDENCE_KIND:
        _fail("EVIDENCE_KIND_INVALID")
    _disposition(completion["disposition"])
    _change_seq(completion["change_seq"])

    _required_bool(document, "universal_truth", False, "EVIDENCE_TRUTH_CLAIM_INVALID")
    _required_bool(
        document,
        "payment_or_settlement_evaluated",
        False,
        "EVIDENCE_PAYMENT_BOUNDARY_INVALID",
    )
    _required_bool(
        document,
        "public_network_exposed",
        False,
        "EVIDENCE_NETWORK_BOUNDARY_INVALID",
    )
    _required_bool(
        document,
        "public_deployment",
        False,
        "EVIDENCE_DEPLOYMENT_BOUNDARY_INVALID",
    )
    return document


def load_authenticated_local_flight_evidence(path_value: str | Path) -> dict[str, object]:
    path = Path(path_value)
    try:
        payload = path.read_bytes()
    except OSError:
        _fail("EVIDENCE_FILE_UNAVAILABLE")
    if len(payload) > MAX_EVIDENCE_BYTES:
        _fail("EVIDENCE_FILE_TOO_LARGE")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("EVIDENCE_JSON_INVALID")
    return validate_authenticated_local_flight_evidence(value)


def render_authenticated_local_flight_evidence(document: dict[str, object]) -> str:
    reviewed = validate_authenticated_local_flight_evidence(document)
    publication = reviewed["agreement_publication"]
    completion = reviewed["completion"]
    assert type(publication) is dict
    assert type(completion) is dict
    lines = (
        f"profile={PROFILE}",
        "status=PASS",
        f"main_commit={reviewed['main_commit']}",
        f"ci_run_number={reviewed['ci_run_number']}",
        f"runtime_host={LOOPBACK_HOST}",
        f"agreement_record_id={reviewed['agreement_record_id']}",
        f"agreement_publication_disposition={publication['disposition']}",
        f"agreement_publication_change_seq={publication['change_seq']}",
        f"completion_record_id={completion['record_id']}",
        f"completion_disposition={completion['disposition']}",
        f"completion_change_seq={completion['change_seq']}",
        f"commitment_id={COMMITMENT_ID}",
        f"evidence_kind={EVIDENCE_KIND}",
        "universal_truth=false",
        "payment_or_settlement_evaluated=false",
        "public_network_exposed=false",
        "public_deployment=false",
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: marketplace_authenticated_local_flight_evidence.py <evidence.json>", file=sys.stderr)
        return 2
    try:
        document = load_authenticated_local_flight_evidence(arguments[0])
    except AuthenticatedLocalFlightEvidenceError as error:
        print(f"status=FAIL code={error.code}", file=sys.stderr)
        return 1
    print(render_authenticated_local_flight_evidence(document))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
