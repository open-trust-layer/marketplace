from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest

from marketplace.application.api import IntentIndexPage
from marketplace.application.postgres_state import ExpiryResult
from marketplace.application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MarketplaceApplicationLaunchPlan,
    build_marketplace_application_launch_plan,
)


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-1m-inert-runtime-launch-contract.md"
SOURCE = ROOT / "src" / "marketplace" / "application" / "launch.py"
INDEX = b"<!doctype html><title>Marketplace</title>"
APP_JS = b"console.log('marketplace');\n"
STYLES = b"body { margin: 0; }\n"


class MinimalStore:
    def __init__(self) -> None:
        self.initialize_calls = 0

    def initialize(self):
        self.initialize_calls += 1
        return ExpiryResult((), ())


class StaticIntentQuery:
    def __init__(self) -> None:
        self.calls = 0

    def list_intent_ids(self, *, cursor=None, limit=64):
        self.calls += 1
        return IntentIndexPage(("r-root",), None)


def decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_plan(*, host=LOOPBACK_LAUNCH_HOST, port=8080, index_html=INDEX, app_js=APP_JS, styles_css=STYLES):
    store = MinimalStore()
    query = StaticIntentQuery()
    plan = build_marketplace_application_launch_plan(
        host=host,
        port=port,
        store=store,
        intent_query=query,
        prepare_record=lambda record: record,
        decode_record=lambda payload: payload,
        response_parent_ids=lambda record: (),
        is_intent_record=lambda record: True,
        decode_record_json=decode_json,
        encode_record_json=encode_json,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )
    return plan, store, query


class M17InertRuntimeLaunchContractTests(unittest.TestCase):
    def test_plan_binds_existing_composition_and_asgi_without_initialization(self):
        plan, store, query = build_plan()
        self.assertIs(type(plan), MarketplaceApplicationLaunchPlan)
        self.assertEqual(plan.host, "127.0.0.1")
        self.assertEqual(plan.port, 8080)
        self.assertIs(plan.asgi._site, plan.composition.site)
        self.assertIs(plan.composition.site._application_http, plan.composition.http)
        self.assertEqual(store.initialize_calls, 0)
        self.assertEqual(query.calls, 0)

    def test_plan_is_frozen_and_keeps_launch_metadata_as_data_only(self):
        plan, _, _ = build_plan()
        with self.assertRaises(FrozenInstanceError):
            plan.port = 9090
        self.assertEqual(plan.host, LOOPBACK_LAUNCH_HOST)
        self.assertEqual(plan.port, 8080)

    def test_only_exact_loopback_host_and_bounded_exact_port_are_accepted(self):
        for host in ("0.0.0.0", "localhost", "::1", "127.0.0.2", b"127.0.0.1", None):
            with self.subTest(host=host):
                with self.assertRaises((TypeError, ValueError)):
                    build_plan(host=host)
        for port in (True, False, 0, -1, 65536, "8080", None):
            with self.subTest(port=port):
                with self.assertRaises((TypeError, ValueError)):
                    build_plan(port=port)

    def test_assets_remain_exact_bounded_caller_injected_bytes(self):
        for field in ("index_html", "app_js", "styles_css"):
            with self.subTest(field=field, case="wrong-type"):
                kwargs = {field: "not-bytes"}
                with self.assertRaises(TypeError):
                    build_plan(**kwargs)
            with self.subTest(field=field, case="empty"):
                kwargs = {field: b""}
                with self.assertRaises(ValueError):
                    build_plan(**kwargs)

    def test_source_and_document_preserve_zero_io_launch_boundary(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "import socket",
            "from socket",
            "uvicorn",
            "hypercorn",
            "daphne",
            "subprocess",
            "os.environ",
            "getenv(",
            "Path(",
            "open(",
            "psycopg.connect",
        ):
            self.assertNotIn(forbidden, text.lower() if forbidden in {"uvicorn", "hypercorn", "daphne"} else text)
        self.assertTrue(DOC.is_file())
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "inert application runtime launch contract",
            "127.0.0.1",
            "no ASGI server activation",
            "no socket/network activation",
            "no live PostgreSQL connection",
            "no runtime filesystem asset loading",
            "no environment or secret loading",
        ):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
