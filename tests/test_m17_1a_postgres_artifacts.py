from __future__ import annotations

import ast
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "postgres_state.py"
PYPROJECT = ROOT / "pyproject.toml"
DOC = ROOT / "docs" / "m17-1a-postgres-application-state.md"
RETENTION_POLICY = ROOT / "docs" / "RETENTION_POLICY.md"


class M17PostgresArtifactTests(unittest.TestCase):
    def test_postgres_provider_is_exact_optional_dependency_only(self):
        document = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        project = document["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(
            project["optional-dependencies"],
            {"postgres": ["psycopg[binary]==3.3.5"]},
        )

    def test_packaged_application_source_remains_connection_injected_and_network_inert(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
        self.assertNotIn("psycopg", imported_roots)
        self.assertNotIn("socket", imported_roots)
        self.assertNotIn("urllib", imported_roots)
        self.assertNotIn("requests", imported_roots)
        self.assertNotIn("subprocess", imported_roots)
        self.assertNotIn("threading", imported_roots)
        lowered = text.lower()
        self.assertNotIn("psycopg.connect", lowered)
        self.assertNotIn("create_pool", lowered)
        self.assertNotIn("database_url", lowered)
        self.assertNotIn("dsn=", lowered)

    def test_migration_schema_is_postgres_native_and_does_not_promote_application_state_to_truth(self):
        from marketplace.application.postgres_state import POSTGRES_APPLICATION_STATE_MIGRATIONS

        sql = "\n".join(
            statement
            for migration in POSTGRES_APPLICATION_STATE_MIGRATIONS
            for statement in migration.statements
        )
        required = (
            "marketplace_app_schema_migrations",
            "marketplace_app_records",
            "marketplace_app_response_links",
            "marketplace_app_changes",
            "marketplace_app_sync_state",
            "BYTEA",
            "TIMESTAMPTZ",
            "GENERATED ALWAYS AS IDENTITY",
            "ON DELETE CASCADE",
        )
        for marker in required:
            self.assertIn(marker, sql)
        lowered = sql.lower()
        for forbidden in (
            "protocol_truth",
            "global_completeness",
            "current_proposal",
            "accepted_response",
            "ownership",
            "legitimacy",
            "ranking_score",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_application_public_surface_exports_shared_state_api(self):
        from marketplace import application

        for name in (
            "MarketplaceApplicationStateService",
            "PostgresApplicationStateStore",
            "PreparedApplicationRecord",
            "APPLICATION_STATE_RETENTION_CLASS",
        ):
            self.assertTrue(hasattr(application, name), name)

    def test_retention_policy_records_authorized_mvp_application_profile(self):
        text = RETENTION_POLICY.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_STATE_MVP",
            "30 days",
            "PostgreSQL",
            "source-level",
            "no production deployment",
        ):
            self.assertIn(marker, text)

    def test_product_persistence_document_is_required(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_STATE_MVP",
            "30 days",
            "PostgreSQL",
            "Proposal",
            "response_to",
            "application sync cursor",
            "not protocol truth",
            "no live database",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()