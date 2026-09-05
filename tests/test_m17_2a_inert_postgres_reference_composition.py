from __future__ import annotations

from pathlib import Path
import unittest

from marketplace.application.postgres_query import PostgresIntentQuery
from marketplace.application.postgres_state import (
    DEFAULT_APPLICATION_STATE_RETENTION_SECONDS,
    PostgresApplicationStateStore,
)
from marketplace.reference.postgres_application_v1 import (
    build_reference_postgres_marketplace_application_launch_plan,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "postgres_application_v1.py"
PACKAGE = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
DOC = ROOT / "docs" / "m17-2a-inert-postgres-reference-composition.md"


class M17InertPostgresReferenceCompositionTests(unittest.TestCase):
    def test_factory_binds_one_connection_factory_and_clock_without_calling_them(self):
        calls: list[str] = []

        def connection_factory():
            calls.append("connection")
            raise AssertionError("connection factory must remain inert during composition")

        def clock():
            calls.append("clock")
            raise AssertionError("clock must remain inert during composition")

        plan = build_reference_postgres_marketplace_application_launch_plan(
            connection_factory=connection_factory,
            clock=clock,
            host="127.0.0.1",
            port=8080,
            index_html=b"<html></html>",
            app_js=b"",
            styles_css=b"",
        )

        self.assertEqual(calls, [])
        self.assertEqual(plan.host, "127.0.0.1")
        self.assertEqual(plan.port, 8080)

        store = plan.composition.state._store
        query = plan.composition.api._intent_query
        self.assertIs(type(store), PostgresApplicationStateStore)
        self.assertIs(type(query), PostgresIntentQuery)
        self.assertIs(store._connection_factory, connection_factory)
        self.assertIs(query._connection_factory, connection_factory)
        self.assertIs(store._clock, clock)
        self.assertIs(query._clock, clock)
        self.assertEqual(
            store.retention_seconds,
            float(DEFAULT_APPLICATION_STATE_RETENTION_SECONDS),
        )

    def test_factory_does_not_expose_retention_or_provider_selection(self):
        text = SOURCE.read_text(encoding="utf-8-sig")
        signature = text.split(
            "def build_reference_postgres_marketplace_application_launch_plan(", 1
        )[1].split(") -> MarketplaceApplicationLaunchPlan:", 1)[0]
        self.assertNotIn("retention_seconds", signature)
        self.assertNotIn("provider", signature)
        self.assertNotIn("dsn", signature.lower())
        self.assertNotIn("password", signature.lower())

    def test_source_has_no_activation_configuration_or_filesystem_authority(self):
        text = SOURCE.read_text(encoding="utf-8-sig")
        for forbidden in (
            "import psycopg",
            "import socket",
            "socket.",
            "subprocess",
            "os.environ",
            "getenv(",
            "Path(",
            "open(",
            ".initialize(",
            "apply_migrations(",
            "UvicornLoopbackServerProvider",
            "run_marketplace_application_foreground",
        ):
            self.assertNotIn(forbidden, text)

    def test_generic_application_layer_remains_reference_independent(self):
        for path in APPLICATION.glob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            self.assertNotIn("marketplace.reference", source, path.name)
            self.assertNotIn("from ..reference", source, path.name)
            self.assertNotIn("from marketplace.reference", source, path.name)

    def test_reference_package_exports_composition_root(self):
        text = PACKAGE.read_text(encoding="utf-8-sig")
        self.assertIn(
            "build_reference_postgres_marketplace_application_launch_plan",
            text,
        )

    def test_document_records_inert_authority_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8-sig")
        for marker in (
            "M17.2A",
            "same injected connection factory and clock",
            "no PostgreSQL connection",
            "no schema migration",
            "no filesystem asset loading",
            "no server activation",
            "separate exact-head governance boundary",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
