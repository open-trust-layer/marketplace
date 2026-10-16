"""Explicit operator-only, read-only PostgreSQL identity probe for #525.

No authentication provisioning, application startup or database mutations.
The password is received only through a child-process environment variable
established by the local operator, never via CLI arguments or stdout.
"""
from __future__ import annotations

import argparse
import os
from typing import Callable

EXECUTION_TOKEN = "EXECUTE_MARKETPLACE_EVALUATOR_LOCAL_DB_PROBE_V1"
PASSWORD_ENV = "MARKETPLACE_EVALUATOR_DB_PASSWORD"
HOST = "127.0.0.1"
PORT = 15432
USER = "marketplace_evaluator"
DATABASE = "marketplace_evaluator"
IDENTITY_QUERY = (
    "SELECT current_user, current_database(), "
    "host(inet_server_addr()), inet_server_port(), "
    "current_setting('transaction_read_only')"
)
ROLE_QUERY = (
    "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
    "FROM pg_catalog.pg_roles WHERE rolname = current_user"
)


def assess_connection(connection: object) -> str | None:
    """None means exact restricted identity and read-only mode were observed."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(IDENTITY_QUERY)
            if cursor.fetchone() != (USER, DATABASE, HOST, PORT, "on"):
                return "DATABASE_IDENTITY_OR_READONLY_MISMATCH"
            cursor.execute(ROLE_QUERY)
            if cursor.fetchone() != (False, False, False, False, False):
                return "DATABASE_ROLE_NOT_RESTRICTED"
    except Exception:
        return "DATABASE_PROBE_FAILED"
    return None


def execute_operator_probe(
    password: object, *, connector: Callable[..., object]
) -> str | None:
    """Connect only to the known private evaluator, with bounded read-only SQL."""
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
            return assess_connection(connection)
    except Exception:
        return "DATABASE_PROBE_FAILED"


class _RedactedParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "status=BLOCKED code=ARGUMENT_INVALID\n")


def main(argv: list[str] | None = None) -> int:
    parser = _RedactedParser(description="Local operator-only evaluator SQL check")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute-operator-probe")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(
            "status=INERT_OPERATOR_PROBE_REVIEWED "
            "credential_opened=false postgres_connection_invoked=false "
            "server_invoked=false browser_invoked=false"
        )
        return 0
    if args.execute_operator_probe != EXECUTION_TOKEN:
        print("status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED")
        return 1

    password = os.environ.get(PASSWORD_ENV)
    if type(password) is not str or not 30 <= len(password) <= 4096:
        print("status=BLOCKED code=OPERATOR_CREDENTIAL_UNAVAILABLE")
        return 1

    # Import the optional adapter only after explicit operator execution opt-in.
    try:
        import psycopg
        result = execute_operator_probe(password, connector=psycopg.connect)
    except Exception:
        result = "DATABASE_PROBE_FAILED"
    finally:
        del password

    if result is not None:
        print(f"status=BLOCKED code={result}")
        return 1
    print(
        "status=LOCAL_EVALUATOR_RESTRICTED_READONLY_VERIFIED "
        "host=127.0.0.1 port=15432 identity=marketplace_evaluator "
        "credential_emitted=false schema_mutation=false "
        "browser_invoked=false server_invoked=false runtime_acceptance=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
