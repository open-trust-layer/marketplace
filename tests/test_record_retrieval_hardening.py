from __future__ import annotations

import ast
import unittest
from pathlib import Path

from olp import RecordV1, record_identity_text

from marketplace.reference import CORE_PROFILE, TYPE_INTENT, federation_v1
from marketplace.runtime.network_policy import FederationEgressPolicy, authorize_federation_endpoint
from marketplace.runtime.record_retrieval import (
    RECORD_RETRIEVAL_OPERATION,
    AuthorizedHttpsRecordRetriever,
    RecordRetrievalTransportError,
)

HOST = "records.example.com"


def sample_record_id() -> str:
    record = RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {
                "version": 1,
                "issuer": {"principal": "did:example:m27-hardening"},
                "subjects": [{"uri": "urn:example:m27-hardening"}],
                "action": {"id": "https://example.test/actions/request"},
                "terms": {},
            },
            "profiles": [CORE_PROFILE],
        }
    )
    return record_identity_text(record)


class CountingResolver:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, hostname: str, port: int):
        self.calls += 1
        return ("1.1.1.1",)


class FailingConnector:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        raise OSError("synthetic connector failure")


class RecordRetrievalHardeningTests(unittest.TestCase):
    def policy(self) -> FederationEgressPolicy:
        return FederationEgressPolicy(
            policy_id="https://open-trust-layer.github.io/marketplace/policy/m27-hardening-v1",
            policy_version=1,
            allowed_hosts=(HOST,),
        )

    def endpoint(self, record_id: str) -> str:
        return f"https://{HOST}/olp/v1/records/{record_id}"

    def authorization(self, record_id: str):
        return authorize_federation_endpoint(
            endpoint=self.endpoint(record_id),
            allowed_operations=(RECORD_RETRIEVAL_OPERATION,),
            authorization_id="m27-hardening",
            issued_at_epoch=1_000,
            expires_at_epoch=1_120,
            policy=self.policy(),
        )

    def test_noncanonical_base64url_record_identity_fails_before_dns(self):
        # Shape-valid text with non-canonical pad bits. Pinned OLP rejects the
        # same presentation; M27 now rejects it before any external lookup.
        noncanonical = "r1_" + ("A" * 42) + "B"
        resolver = CountingResolver()
        retriever = AuthorizedHttpsRecordRetriever(
            policy=self.policy(),
            decode_envelope_json=lambda body: body,
            resolver=resolver,
            connector=FailingConnector(),
            wall_clock=lambda: 1_050.0,
            monotonic_clock=lambda: 10.0,
        )
        with self.assertRaises(RecordRetrievalTransportError) as caught:
            retriever.retrieve(
                endpoint=self.endpoint(noncanonical),
                authorization=None,  # must remain unreachable
                expected_record_identity=noncanonical,
            )
        self.assertEqual(caught.exception.code, "INVALID_EXPECTED_RECORD_IDENTITY")
        self.assertEqual(resolver.calls, 0)

    def test_connector_failure_is_exactly_one_attempt_and_never_retried(self):
        record_id = sample_record_id()
        connector = FailingConnector()
        retriever = AuthorizedHttpsRecordRetriever(
            policy=self.policy(),
            decode_envelope_json=lambda body: body,
            resolver=lambda host, port: ("1.1.1.1",),
            connector=connector,
            wall_clock=lambda: 1_050.0,
            monotonic_clock=lambda: 10.0,
        )
        with self.assertRaises(RecordRetrievalTransportError) as caught:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity=record_id,
            )
        self.assertEqual(caught.exception.code, "TLS_CONNECTION_FAILED")
        self.assertEqual(connector.calls, 1)

    def test_m27_local_operation_does_not_enter_m8_core_operation_set(self):
        self.assertNotIn(
            RECORD_RETRIEVAL_OPERATION,
            {federation_v1.OP_SNAPSHOT, federation_v1.OP_SYNC, federation_v1.OP_SUBMISSION},
        )

    def test_m27_runtime_reuses_m26_network_path_and_has_no_parallel_network_client(self):
        path = Path(__file__).resolve().parents[1] / "src/marketplace/runtime/record_retrieval.py"
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source)

        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        for forbidden in (
            "socket",
            "ssl",
            "urllib.request",
            "http.client",
            "requests",
            "httpx",
            "aiohttp",
            "netrc",
            "os",
            "subprocess",
        ):
            self.assertNotIn(forbidden, imported)

        self.assertIn("https_transport", imported)
        self.assertIn("network_policy", imported)
        for forbidden_call in ("eval", "exec", "compile", "open", "__import__"):
            self.assertNotIn(f"{forbidden_call}(", source)


if __name__ == "__main__":
    unittest.main()
