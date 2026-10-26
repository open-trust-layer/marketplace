"""Operator-only, non-mutating evaluator schema-readiness check for #525.

A restricted DB identity PASS does not establish rights needed for migrations.
This check asks PostgreSQL's privilege catalogs only. It never executes DDL,
DML, migrations, expiry cleanup or application startup. It cannot prove that
the later write transaction or complete browser flight will succeed.
"""
from __future__ import annotations

import argparse
import os
from typing import Callable

from tools.marketplace_evaluator_operator_db_probe import (
    DATABASE,
    HOST,
    PASSWORD_ENV,
    PORT,
    USER,
    assess_connection,
)

EXECUTION_TOKEN = "EXECUTE_MARKETPLACE_EVALUATOR_LOCAL_SCHEMA_READINESS_V1"
_SCHEMA = "public"

SCHEMA_QUERY = (
    "SELECT current_schema(), "
    "has_schema_privilege(current_schema(), 'CREATE')"
)
EXPECTED_TABLES = frozenset((
    "marketplace_app_schema_migrations",
    "marketplace_app_records",
    "marketplace_app_response_links",
    "marketplace_app_changes",
    "marketplace_app_sync_state",
    "marketplace_agreement_assent_schema_migrations",
    "marketplace_agreement_assent_evidence",
))
# Includes only fixed reviewed Marketplace footprint, not the contents of
# user, buyer, seller, record or authentication tables.
TABLE_QUERY = (
    "SELECT c.relname, "
    "pg_catalog.pg_get_userbyid(c.relowner) = current_user, "
    "(has_table_privilege(c.oid, 'SELECT') AND "
    "has_table_privilege(c.oid, 'INSERT') AND "
    "has_table_privilege(c.oid, 'UPDATE') AND "
    "has_table_privilege(c.oid, 'DELETE')) "
    "FROM pg_catalog.pg_class AS c "
    "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
    "WHERE n.nspname = current_schema() "
    "AND c.relkind IN ('r', 'p') "
    "AND c.relname IN ("
    + ", ".join("'" + item + "'" for item in sorted(EXPECTED_TABLES))
    + ") ORDER BY c.relname"
)


def assess_schema_readiness(connection: object) -> str | None:
    """Fixed code on failure, None on catalog readiness, without performing writes."""
    existing_status = assess_connection(connection)
    if existing_status is not None:
        return existing_status
    try:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_QUERY)
            row = cursor.fetchone()
            if type(row) not in (tuple, list) or len(row) != 2 or row[0] != _SCHEMA:
                return "EVALUATOR_SCHEMA_NOT_PUBLIC"
            if row[1] is not True:
                return "EVALUATOR_SCHEMA_CREATE_PRIVILEGE_MISSING"
            cursor.execute(TABLE_QUERY)
            rows = cursor.fetchall()
            if type(rows) not in (list, tuple) or len(rows) > len(EXPECTED_TABLES):
                return "EVALUATOR_SCHEMA_FOOTPRINT_UNVERIFIED"
            seen: set[str] = set()
            for row in rows:
                if type(row) not in (tuple, list) or len(row) != 3:
                    return "EVALUATOR_SCHEMA_FOOTPRINT_UNVERIFIED"
                name, owner, dml = row
                if type(name) is not str or name not in EXPECTED_TABLES or name in seen:
                    return "EVALUATOR_SCHEMA_FOOTPRINT_UNVERIFIED"
                seen.add(name)
                if owner is not True:
                    return "EVALUATOR_EXISTING_TABLE_OWNERSHIP_MISMATCH"
                if dml is not True:
                    return "EVALUATOR_EXISTING_TABLE_PRIVILEGES_MISSING"
    except Exception:
        return "EVALUATOR_SCHEMA_READINESS_CHECK_FAILED"
    return None


def execute_schema_readiness(
    password: object, *, connector: Callable[..., object]
) -> str | None:
    """Use the same locked-down evaluator DB identity as the existing probe."""
    if type(password) is not str or not 30 <= len(password) <= 4096:
        return "OPERATOR_CREDENTIAL_UNAVAILABLE"
    if any(char in password for char in ("\x00", "\r", "\n")):
        return "OPERATOR_CREDENTIAL_UNAVAILABLE"
    try:
        with connector(
            host=HOST,
            port=PORT,
            dbname=DATABASE,
            user=USER,
            password=password,
            connect_timeout=6,
            options="-c default_transaction_read_only=on -c statement_timeout=5000",
        ) as connection:
            return assess_schema_readiness(connection)
    except Exception:
        return "EVALUATOR_SCHEMA_READINESS_CHECK_FAILED"


class _RedactedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=BLOCKED code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedParser(description="Operator-only read-only schema catalog check")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute-schema-readiness")
    args = parser.parse_args(argv)
    if args.dry_run:
        print(
            "status=INERT_SCHEMA_READINESS_READY "
            "postgres_connection_invoked=false schema_mutation=false server_invoked=false"
        )
        return 0
    if args.execute_schema_readiness != EXECUTION_TOKEN:
        print("status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED")
        return 1
    password = os.environ.get(PASSWORD_ENV)
    if type(password) is not str or not 30 <= len(password) <= 4096:
        print("status=BLOCKED code=OPERATOR_CREDENTIAL_UNAVAILABLE")
        return 1
    try:
        import psycopg
        result = execute_schema_readiness(password, connector=psycopg.connect)
    except Exception:
        result = "EVALUATOR_SCHEMA_READINESS_CHECK_FAILED"
    finally:
        del password
    if result is not None:
        print("status=BLOCKED code=" + result)
        return 1
    print(
        "status=LOCAL_EVALUATOR_SCHEMA_READINESS_VERIFIED "
        "host=127.0.0.1 port=15432 schema=public "
        "catalog_only=true schema_mutation=false runtime_acceptance=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
