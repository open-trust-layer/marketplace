from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from marketplace.application.api import IntentIndexPage
from marketplace.application.launch import (
    MarketplaceApplicationLaunchPlan,
    build_marketplace_application_launch_plan,
)
from marketplace.application.postgres_state import ExpiryResult
from marketplace.application.runtime_server import (
    EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
    MarketplaceLocalRuntimeError,
    run_marketplace_application_foreground,
)


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-1n-foreground-loopback-server-boundary.md"
SOURCE = ROOT / "src" / "marketplace" / "application" / "runtime_server.py"


class MinimalStore:
    def initialize(self):
        return ExpiryResult((), ())


class StaticIntentQuery:
    def list_intent_ids(self, *, cursor=None, limit=64):
        return IntentIndexPage(("r-root",), None)


class FakeServerProvider:
    def __init__(self, *, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.calls: list[tuple[object, str, int]] = []

    def run(self, *, application: object, host: str, port: int) -> None:
        self.calls.append((application, host, port))
        if self.failure is not None:
            raise self.failure


def decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_json(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_plan() -> MarketplaceApplicationLaunchPlan:
    return build_marketplace_application_launch_plan(
        host="127.0.0.1",
        port=8080,
        store=MinimalStore(),
        intent_query=StaticIntentQuery(),
        prepare_record=lambda record: record,
        decode_record=lambda payload: payload,
        response_parent_ids=lambda record: (),
        is_intent_record=lambda record: True,
        decode_record_json=decode_json,
        encode_record_json=encode_json,
        build_product_listing_record=lambda draft: object(),
        index_html=b"<!doctype html><title>Marketplace</title>",
        app_js=b"console.log('marketplace');\n",
        styles_css=b"body { margin: 0; }\n",
    )


class M17ForegroundLoopbackServerBoundaryTests(unittest.TestCase):
    def test_exact_execute_token_delegates_once_to_injected_provider(self):
        plan = make_plan()
        provider = FakeServerProvider()

        result = run_marketplace_application_foreground(
            plan=plan,
            provider=provider,
            execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
        )

        self.assertIsNone(result)
        self.assertEqual(len(provider.calls), 1)
        application, host, port = provider.calls[0]
        self.assertIs(application, plan.asgi)
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, 8080)

    def test_invalid_execute_token_fails_before_provider_invocation(self):
        for token in (None, "", "EXECUTE", b"EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER"):
            with self.subTest(token=token):
                provider = FakeServerProvider()
                with self.assertRaises(PermissionError) as caught:
                    run_marketplace_application_foreground(
                        plan=make_plan(),
                        provider=provider,
                        execute_token=token,  # type: ignore[arg-type]
                    )
                self.assertEqual(
                    str(caught.exception),
                    "MARKETPLACE_LOOPBACK_SERVER_EXECUTION_NOT_AUTHORIZED",
                )
                self.assertEqual(provider.calls, [])

    def test_runtime_boundary_revalidates_exact_plan_loopback_host_and_port(self):
        plan = make_plan()
        invalid_cases = (
            {"host": "0.0.0.0"},
            {"host": "localhost"},
            {"host": b"127.0.0.1"},
            {"port": True},
            {"port": 0},
            {"port": 65536},
            {"port": "8080"},
        )
        for kwargs in invalid_cases:
            with self.subTest(kwargs=kwargs):
                provider = FakeServerProvider()
                forged = replace(plan, **kwargs)
                with self.assertRaises((TypeError, ValueError)):
                    run_marketplace_application_foreground(
                        plan=forged,
                        provider=provider,
                        execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
                    )
                self.assertEqual(provider.calls, [])

    def test_non_exact_plan_and_non_provider_fail_before_execution(self):
        provider = FakeServerProvider()
        with self.assertRaises(TypeError):
            run_marketplace_application_foreground(
                plan=object(),  # type: ignore[arg-type]
                provider=provider,
                execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(provider.calls, [])

        with self.assertRaises(TypeError):
            run_marketplace_application_foreground(
                plan=make_plan(),
                provider=object(),  # type: ignore[arg-type]
                execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
            )

    def test_provider_failure_is_non_reflective_and_not_retried(self):
        provider = FakeServerProvider(failure=RuntimeError("provider secret detail"))
        with self.assertRaises(MarketplaceLocalRuntimeError) as caught:
            run_marketplace_application_foreground(
                plan=make_plan(),
                provider=provider,
                execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(str(caught.exception), "MARKETPLACE_LOOPBACK_SERVER_PROVIDER_FAILED")
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(len(provider.calls), 1)

    def test_source_and_document_keep_concrete_runtime_authority_outside_this_slice(self):
        source = SOURCE.read_text(encoding="utf-8")
        lowered = source.lower()
        for forbidden in (
            "import socket",
            "from socket",
            "uvicorn",
            "hypercorn",
            "daphne",
            "subprocess",
            "threading",
            "create_task",
            "os.environ",
            "getenv(",
            "path(",
            "open(",
            "psycopg",
        ):
            self.assertNotIn(forbidden, lowered)

        self.assertTrue(DOC.is_file())
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "explicit foreground loopback server execution boundary",
            "127.0.0.1",
            "injected server provider",
            "no concrete ASGI server dependency",
            "no real socket activation",
            "no live PostgreSQL activation",
            "no runtime filesystem asset loading",
            "separate runtime authorization",
        ):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
