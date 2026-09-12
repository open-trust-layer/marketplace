from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.authoring import ProductListingAuthoringFields
from marketplace.application.listing import UNIT_ITEM
from marketplace.application.postgres_state import (
    ApplicationStateCollisionError,
    PreparedApplicationRecord,
)
from marketplace.reference.memory_application_v1 import (
    MemoryApplicationStateStore,
    build_reference_memory_marketplace_application_launch_plan,
)
from marketplace.runtime.contracts import StoreDisposition
from tools import marketplace_localhost


class _Provider:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, int]] = []

    def run(self, *, application: object, host: str, port: int) -> None:
        self.calls.append((application, host, port))


class MarketplaceMvpDemoLauncherTests(unittest.TestCase):
    def test_memory_store_preserves_duplicate_collision_and_sync_semantics(self) -> None:
        store = MemoryApplicationStateStore()
        first = PreparedApplicationRecord("r1_demo", b"one", ())
        stored = store.put(first)
        self.assertIs(stored.disposition, StoreDisposition.STORED)
        self.assertEqual(stored.change_seq, 1)
        duplicate = store.put(first)
        self.assertIs(duplicate.disposition, StoreDisposition.DUPLICATE)
        self.assertIsNone(duplicate.change_seq)
        with self.assertRaises(ApplicationStateCollisionError):
            store.put(PreparedApplicationRecord("r1_demo", b"two", ()))
        self.assertEqual(store.get("r1_demo"), first)
        page = store.sync_since(0, limit=8)
        self.assertEqual(tuple(change.record_id for change in page.changes), ("r1_demo",))
        self.assertEqual(page.next_cursor, 1)
        self.assertFalse(page.has_more)

    def test_memory_reference_composition_supports_real_listing_browse(self) -> None:
        plan = build_reference_memory_marketplace_application_launch_plan(
            host="127.0.0.1",
            port=18080,
            index_html=b"<!doctype html>",
            app_js=b"'use strict';",
            styles_css=b"body{}",
        )
        plan.composition.initialize()
        result = plan.composition.authoring.create_product_listing(
            ProductListingAuthoringFields(
                seller_principal="did:example:seller",
                subject_uri="urn:example:item:bicycle",
                title="Utrecht bicycle",
                description="Local in-memory MVP demo listing",
                consideration_coefficient=125,
                consideration_scale=2,
                currency_code="EUR",
                quantity_coefficient=1,
                quantity_scale=0,
                unit_uri=UNIT_ITEM,
                latitude_e6=52_090_737,
                longitude_e6=5_121_420,
            )
        )
        page = plan.composition.api.list_intents(limit=8)
        self.assertIs(result.disposition, StoreDisposition.STORED)
        self.assertEqual(len(page.record_ids), 1)
        self.assertIsNotNone(plan.composition.api.get_intent(page.record_ids[0]))
        self.assertIsNone(page.next_cursor)

    def test_demo_execution_uses_no_postgres_or_environment(self) -> None:
        provider = _Provider()
        assets = (b"<!doctype html>", b"'use strict';", b"body{}")
        with (
            patch.object(marketplace_localhost, "_real_asset_reader", return_value=lambda path: {
                "web/index.html": assets[0],
                "web/app.js": assets[1],
                "web/styles.css": assets[2],
            }[path]),
            patch.object(marketplace_localhost, "_real_uvicorn_provider", return_value=provider),
            patch.object(marketplace_localhost, "_real_environment_getter", side_effect=AssertionError),
            patch.object(marketplace_localhost, "_build_psycopg_connection_factory", side_effect=AssertionError),
            patch.object(marketplace_localhost, "_load_mvp_flight_runner", return_value=lambda: None),
        ):
            marketplace_localhost._execute_demo_localhost(
                18080,
                marketplace_localhost.DEMO_LOCALHOST_EXECUTION_OPT_IN,
            )
        self.assertEqual(len(provider.calls), 1)
        _, host, port = provider.calls[0]
        self.assertEqual((host, port), ("127.0.0.1", 18080))

    def test_demo_execution_gate_fails_before_asset_or_provider_selection(self) -> None:
        with (
            patch.object(marketplace_localhost, "_real_asset_reader", side_effect=AssertionError),
            patch.object(marketplace_localhost, "_real_uvicorn_provider", side_effect=AssertionError),
            patch.object(marketplace_localhost, "_load_mvp_flight_runner", side_effect=AssertionError),
        ):
            with self.assertRaises(marketplace_localhost.MarketplaceLocalhostBootstrapError) as caught:
                marketplace_localhost._execute_demo_localhost(18080, "wrong")
        self.assertEqual(caught.exception.code, "MVP_DEMO_EXECUTION_OPT_IN_REQUIRED")

    def test_cli_exposes_demo_mode_without_changing_dry_run(self) -> None:
        parser = marketplace_localhost._parser()
        args = parser.parse_args([
            "--port",
            "18080",
            "--execute-demo-localhost",
            marketplace_localhost.DEMO_LOCALHOST_EXECUTION_OPT_IN,
        ])
        self.assertEqual(
            args.execute_demo_localhost,
            marketplace_localhost.DEMO_LOCALHOST_EXECUTION_OPT_IN,
        )


if __name__ == "__main__":
    unittest.main()
