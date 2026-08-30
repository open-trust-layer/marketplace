"""Manual one-shot M62 loopback acceptance harness.

Import, help, validation, and dry-run are network-inert. Real socket selection occurs
only after the exact execution opt-in token is validated. This tool is not a service,
daemon, deployment entry point, or substitute for fresh NETWORK_EXTERNAL authority.
"""
from __future__ import annotations

import argparse
import sys
import time

from olp import RecordV1

from marketplace.reference import (
    CORE_PROFILE,
    TYPE_INTENT,
    federation_v1,
    record_identity_text,
    validate_market_record,
)
from marketplace.reference.inbound_http_v1 import (
    decode_inbound_control_envelope_json,
    encode_prepared_inbound_response_json,
)
from marketplace.reference.record_serving_v1 import (
    make_record_transport_envelope,
    market_record_transport_payload,
    verify_prepared_record_transport_envelope,
)
from marketplace.runtime.federation import FederationOperationProfile
from marketplace.runtime.inbound_federation import (
    BoundedInboundFederationResponder,
    InboundFederationPageMaterial,
)
from marketplace.runtime.inbound_http import InboundFederationHttpRoute
from marketplace.runtime.inbound_http_end_to_end_composition import (
    BoundedInboundHttpEndToEndSourceCompositionRoot,
)
from marketplace.runtime.inbound_http_execution_gate import (
    LOOPBACK_EXECUTION_OPT_IN,
    BoundedInboundHttpLoopbackExecutionGate,
    InboundHttpLoopbackExecutionGateError,
)
from marketplace.runtime.inbound_record import BoundedInboundRecordResponder

SOURCE = "urn:open-trust-layer:marketplace:m62-loopback-acceptance"
AUTHORITY = "marketplace.loopback.test"
SNAPSHOT_PATH = "/v1/federation/snapshot"
SYNC_PATH = "/v1/federation/sync"
ACTION = "https://open-trust-layer.github.io/marketplace/runtime/v1/action/m62-acceptance"
SUBJECT = "urn:open-trust-layer:marketplace:m62-acceptance-record"


def _sample_record() -> RecordV1:
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {
                "version": 1,
                "issuer": {"principal": "did:example:m62-loopback"},
                "subjects": [{"uri": SUBJECT}],
                "action": {"id": ACTION},
                "terms": {},
            },
            "profiles": [CORE_PROFILE],
        }
    )


class _ExactRecordSource:
    __slots__ = ("_record",)

    def __init__(self, value: RecordV1) -> None:
        self._record = value

    def get(self, record_id: str):
        return self._record if record_id == record_identity_text(self._record) else None


def _capabilities() -> dict[str, object]:
    caps = sorted(
        [federation_v1.CAP_SNAPSHOT, federation_v1.CAP_SYNC],
        key=lambda value: value.encode("utf-8"),
    )
    return {
        "version": 1,
        "source": SOURCE,
        "implemented": caps,
        "enabled": caps,
        "configured": caps,
        "limits": {
            "max_page_records": federation_v1.MAX_PAGE_RECORDS,
            "max_cursor_bytes": federation_v1.MAX_CURSOR_BYTES,
            "max_submission_records": federation_v1.MAX_SUBMISSION_RECORDS,
        },
    }


def _profiles() -> tuple[FederationOperationProfile, ...]:
    return (
        FederationOperationProfile(
            federation_v1.OP_SNAPSHOT,
            federation_v1.MSG_SNAPSHOT_REQUEST,
            federation_v1.MSG_SNAPSHOT_RESULT,
        ),
        FederationOperationProfile(
            federation_v1.OP_SYNC,
            federation_v1.MSG_SYNC_REQUEST,
            federation_v1.MSG_SYNC_RESULT,
        ),
    )


def _federation_responder() -> BoundedInboundFederationResponder:
    return BoundedInboundFederationResponder(
        local_source=SOURCE,
        validate_transport_envelope=federation_v1.validate_transport_envelope,
        validate_exchange_request=federation_v1.validate_exchange_request,
        scope_fingerprint=federation_v1.scope_fingerprint,
        negotiate_capabilities=federation_v1.negotiate_capabilities,
        capability_advertisement=_capabilities(),
        evaluate_exchange_page=federation_v1.evaluate_exchange_page,
        validate_exchange_result=federation_v1.validate_exchange_result,
        make_transport_envelope=federation_v1.make_transport_envelope,
        validate_record=validate_market_record,
        record_identity_text=record_identity_text,
        authorize_disclosure=lambda _context: True,
        page_source=lambda _context: InboundFederationPageMaterial(
            records=(), source_completeness="PARTIAL_SOURCE", page_truncated=False
        ),
        operation_profiles=_profiles(),
    )


def _record_responder() -> BoundedInboundRecordResponder:
    sample = _sample_record()
    return BoundedInboundRecordResponder(
        local_source=SOURCE,
        record_source=_ExactRecordSource(sample),
        authorize_disclosure=lambda _context: True,
        validate_record=validate_market_record,
        record_identity=record_identity_text,
        prepare_payload=market_record_transport_payload,
        make_record_envelope=make_record_transport_envelope,
        verify_record_envelope=verify_prepared_record_transport_envelope,
    )


def build_source_root(port: int) -> BoundedInboundHttpEndToEndSourceCompositionRoot:
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("port MUST be an exact integer in 1024..65535")
    routes = (
        InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT),
        InboundFederationHttpRoute(SYNC_PATH, federation_v1.OP_SYNC),
    )
    return BoundedInboundHttpEndToEndSourceCompositionRoot(
        federation_responder=_federation_responder(),
        record_responder=_record_responder(),
        control_routes=routes,
        decode_transport_envelope_json=decode_inbound_control_envelope_json,
        encode_transport_envelope_json=encode_prepared_inbound_response_json,
        authority=AUTHORITY,
        clock=time.monotonic,
        port=port,
    )


def _real_socket_constructor():
    import socket

    return socket.socket


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Explicit one-shot loopback acceptance for the reviewed M59 -> M55 graph. "
            "Dry-run is network-inert; execution requires the exact opt-in token."
        )
    )
    parser.add_argument("--port", type=int, required=True, help="loopback port 1024..65535")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="compose only; no socket selection")
    mode.add_argument(
        "--execute-one-loopback-network-session",
        metavar="TOKEN",
        help="NETWORK_EXTERNAL path; TOKEN must be the exact documented opt-in value",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if type(args.port) is not int or not 1024 <= args.port <= 65535:
        print("M62_PORT_INVALID", file=sys.stderr)
        return 2
    root = build_source_root(args.port)
    gate = BoundedInboundHttpLoopbackExecutionGate(source_composition_root=root)
    try:
        if args.dry_run:
            gate.dry_run()
            print("M62_DRY_RUN_READY")
            return 0
        token = args.execute_one_loopback_network_session
        if type(token) is not str or token != LOOPBACK_EXECUTION_OPT_IN:
            print("LOOPBACK_EXECUTION_OPT_IN_REQUIRED", file=sys.stderr)
            return 2
        try:
            constructor = _real_socket_constructor()
        except Exception:
            print("LOOPBACK_EXECUTION_SOCKET_SELECTION_FAILED", file=sys.stderr)
            return 1
        gate.execute_once(opt_in=token, constructor=constructor)
        print("M62_ONE_SHOT_LOOPBACK_SESSION_COMPLETE")
        return 0
    except InboundHttpLoopbackExecutionGateError as exc:
        print(exc.code, file=sys.stderr)
        return 1
    finally:
        gate.close()


if __name__ == "__main__":
    raise SystemExit(main())
