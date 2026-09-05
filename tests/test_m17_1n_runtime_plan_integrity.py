from __future__ import annotations

from dataclasses import replace
import json
import unittest

import marketplace.application as application_package
from marketplace.application.api import IntentIndexPage
from marketplace.application.launch import build_marketplace_application_launch_plan
from marketplace.application.postgres_state import ExpiryResult
from marketplace.application.runtime_server import (
    EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
    run_marketplace_application_foreground,
)


class MinimalStore:
    def initialize(self):
        return ExpiryResult((), ())


class StaticIntentQuery:
    def list_intent_ids(self, *, cursor=None, limit=64):
        return IntentIndexPage(("r-root",), None)


class FakeServerProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, int]] = []

    def run(self, *, application: object, host: str, port: int) -> None:
        self.calls.append((application, host, port))


def _decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def _encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_genuine_plan(*, port: int = 8080):
    return build_marketplace_application_launch_plan(
        host="127.0.0.1",
        port=port,
        store=MinimalStore(),
        intent_query=StaticIntentQuery(),
        prepare_record=lambda record: record,
        decode_record=lambda payload: payload,
        response_parent_ids=lambda record: (),
        is_intent_record=lambda record: True,
        decode_record_json=_decode_json,
        encode_record_json=_encode_json,
        build_product_listing_record=lambda draft: object(),
        build_proposal_record=lambda draft: object(),
        index_html=b"<!doctype html><title>Marketplace</title>",
        app_js=b"console.log('marketplace');\n",
        styles_css=b"body { margin: 0; }\n",
    )


class M17RuntimePlanIntegrityTests(unittest.TestCase):
    def test_genuine_m17_1m_plan_graph_executes_once(self):
        plan = build_genuine_plan()
        provider = FakeServerProvider()

        run_marketplace_application_foreground(
            plan=plan,
            provider=provider,
            execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
        )

        self.assertEqual(provider.calls, [(plan.asgi, "127.0.0.1", 8080)])

    def test_forged_plan_component_types_fail_before_provider_invocation(self):
        plan = build_genuine_plan()
        forged_cases = (
            replace(plan, composition=object()),
            replace(plan, asgi=object()),
        )
        for forged in forged_cases:
            with self.subTest(forged=forged):
                provider = FakeServerProvider()
                with self.assertRaises(TypeError):
                    run_marketplace_application_foreground(
                        plan=forged,
                        provider=provider,
                        execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
                    )
                self.assertEqual(provider.calls, [])

    def test_exact_but_cross_bound_asgi_graph_fails_before_provider_invocation(self):
        plan = build_genuine_plan(port=8080)
        other = build_genuine_plan(port=8081)
        forged = replace(plan, asgi=other.asgi)
        provider = FakeServerProvider()

        with self.assertRaises(ValueError) as caught:
            run_marketplace_application_foreground(
                plan=forged,
                provider=provider,
                execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
            )

        self.assertEqual(str(caught.exception), "launch ASGI adapter is not bound to launch composition")
        self.assertEqual(provider.calls, [])

    def test_application_package_exports_runtime_boundary(self):
        names = (
            "EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER",
            "MarketplaceAsgiServerProvider",
            "MarketplaceLocalRuntimeError",
            "run_marketplace_application_foreground",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertTrue(hasattr(application_package, name))
                self.assertIn(name, application_package.__all__)


if __name__ == "__main__":
    unittest.main()
