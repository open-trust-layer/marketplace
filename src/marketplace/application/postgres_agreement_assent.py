"""PostgreSQL adapter for bounded Agreement assent coordination evidence.

Construction is inert: callers inject the DB-API connection factory and clock.
The stored value is bounded public coordination material, not a Marketplace
RecordV1 and not trusted formation evidence by persistence alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from .agreement_assent_coordination import (
    AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS,
    DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS,
    MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES,
    MAX_AGREEMENT_ASSENT_EXPIRY_BATCH,
    MAX_AGREEMENT_ASSENT_PARTIES,
    MAX_AGREEMENT_ASSENT_PROOF_BYTES,
    MAX_AGREEMENT_ASSENT_RETENTION_SECONDS,
    AgreementAssentCoordinationCollisionError,
    AgreementAssentCoordinationError,
    AgreementAssentExpiryResult,
    AgreementAssentPutResult,
    PreparedAgreementAssent,
)
from .postgres_state import Clock, Connection, ConnectionFactory, Cursor
from ..runtime.contracts import StoreDisposition


_RECORD_ID = re.compile(r"^r1_[A-Za-z0-9_-]{43}$")
_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_URI_MAX_BYTES = 2048


class AgreementAssentPostgresError(AgreementAssentCoordinationError):
    """Stable non-reflective PostgreSQL assent-coordination failure."""


class AgreementAssentPostgresRetentionError(AgreementAssentPostgresError):
    def __init__(self) -> None:
        super().__init__(
            "AGREEMENT_ASSENT_RETENTION_DELETE_FAILED",
            "expired Agreement assent coordination evidence could not be deleted safely",
        )


@dataclass(frozen=True, slots=True)
class AgreementAssentPostgresMigration:
    version: int
    statements: tuple[str, ...]


POSTGRES_AGREEMENT_ASSENT_MIGRATIONS = (
    AgreementAssentPostgresMigration(
        version=1,
        statements=(
            """
CREATE TABLE IF NOT EXISTS marketplace_agreement_assent_schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    applied_at TIMESTAMPTZ NOT NULL
)
""",
            f"""
CREATE TABLE IF NOT EXISTS marketplace_agreement_assent_evidence (
    agreement_record_id TEXT NOT NULL,
    principal TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    proof_identity BYTEA NOT NULL,
    proof_bytes BYTEA NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (agreement_record_id, principal),
    CHECK (octet_length(proof_identity) = 32),
    CHECK (
        octet_length(proof_bytes) > 0
        AND octet_length(proof_bytes) <= {MAX_AGREEMENT_ASSENT_PROOF_BYTES}
    ),
    CHECK (expires_at > accepted_at),
    CHECK (expires_at <= accepted_at + INTERVAL '30 days')
)
""",
            """
CREATE INDEX IF NOT EXISTS marketplace_agreement_assent_expires_idx
ON marketplace_agreement_assent_evidence
(expires_at, agreement_record_id, principal)
""",
        ),
    ),
)


_SELECT_SCHEMA_VERSIONS = """
SELECT version
FROM marketplace_agreement_assent_schema_migrations
ORDER BY version
"""
_INSERT_SCHEMA_VERSION = """
INSERT INTO marketplace_agreement_assent_schema_migrations
(version, applied_at)
VALUES (%s, %s)
"""
_SCHEMA_FOOTPRINT_CHECK = """
SELECT
    to_regclass('marketplace_agreement_assent_schema_migrations') IS NOT NULL,
    to_regclass('marketplace_agreement_assent_evidence') IS NOT NULL,
    to_regclass('marketplace_agreement_assent_expires_idx') IS NOT NULL
"""
_LOCK_EVIDENCE = """
LOCK TABLE marketplace_agreement_assent_evidence
IN SHARE ROW EXCLUSIVE MODE
"""
_DELETE_EXPIRED = f"""
/* AGREEMENT_ASSENT_RETENTION_MAINTENANCE */
DELETE FROM marketplace_agreement_assent_evidence
WHERE (agreement_record_id, principal) IN (
    SELECT agreement_record_id, principal
    FROM marketplace_agreement_assent_evidence
    WHERE expires_at <= %s
    ORDER BY agreement_record_id, principal
    LIMIT {MAX_AGREEMENT_ASSENT_EXPIRY_BATCH}
    FOR UPDATE SKIP LOCKED
)
RETURNING agreement_record_id, principal
"""
_DELETE_EXPIRED_KEY = """
DELETE FROM marketplace_agreement_assent_evidence
WHERE agreement_record_id = %s
  AND principal = %s
  AND expires_at <= %s
"""
_SELECT_EXISTING_FOR_UPDATE = """
SELECT verification_method, proof_identity, proof_bytes, accepted_at, expires_at
FROM marketplace_agreement_assent_evidence
WHERE agreement_record_id = %s
  AND principal = %s
  AND expires_at > %s
FOR UPDATE
"""
_SELECT_ACTIVE_COUNT = """
SELECT COUNT(*)
FROM marketplace_agreement_assent_evidence
WHERE expires_at > %s
"""
_INSERT_EVIDENCE = """
INSERT INTO marketplace_agreement_assent_evidence
(agreement_record_id, principal, verification_method, proof_identity, proof_bytes,
 accepted_at, expires_at)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
_SELECT_ACTIVE_ONE = """
SELECT verification_method, proof_identity, proof_bytes, accepted_at, expires_at
FROM marketplace_agreement_assent_evidence
WHERE agreement_record_id = %s
  AND principal = %s
  AND expires_at > %s
"""
_SELECT_ACTIVE_FOR_AGREEMENT = """
SELECT principal, verification_method, proof_identity, proof_bytes, accepted_at, expires_at
FROM marketplace_agreement_assent_evidence
WHERE agreement_record_id = %s
  AND expires_at > %s
ORDER BY principal COLLATE "C"
LIMIT %s
"""


def _review_record_id(value: object) -> str:
    if type(value) is not str or _RECORD_ID.fullmatch(value) is None:
        raise ValueError("agreement_record_id is invalid")
    return value


def _review_uri(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("URI is invalid")
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise ValueError("URI is invalid") from None
    if len(raw) > _URI_MAX_BYTES or _URI.fullmatch(value) is None:
        raise ValueError("URI is invalid")
    return value


class PostgresAgreementAssentCoordinationStore:
    """Bounded PostgreSQL coordination store over an injected connection."""

    retention_class = AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS

    def __init__(
        self,
        *,
        connection_factory: ConnectionFactory,
        clock: Clock,
        retention_seconds: int = DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS,
        max_entries: int = MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES,
    ) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory MUST be callable")
        if not callable(clock):
            raise TypeError("clock MUST be callable")
        if (
            type(retention_seconds) is not int
            or isinstance(retention_seconds, bool)
            or not 1 <= retention_seconds <= MAX_AGREEMENT_ASSENT_RETENTION_SECONDS
        ):
            raise ValueError("retention_seconds MUST be an exact integer within 30 days")
        if (
            type(max_entries) is not int
            or isinstance(max_entries, bool)
            or not 1 <= max_entries <= MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES
        ):
            raise ValueError("max_entries is outside the reviewed coordination bound")
        self._connection_factory = connection_factory
        self._clock = clock
        self._retention_seconds = retention_seconds
        self._max_entries = max_entries

    @property
    def retention_seconds(self) -> int:
        return self._retention_seconds

    def _now(self) -> datetime:
        try:
            value = self._clock()
        except Exception:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_CLOCK_INVALID",
                "Agreement assent coordination clock is invalid",
            ) from None
        if (
            type(value) is not datetime
            or value.tzinfo is None
            or value.utcoffset() is None
            or value.microsecond != 0
        ):
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_CLOCK_INVALID",
                "Agreement assent coordination clock must return whole aware seconds",
            )
        reviewed = value.astimezone(timezone.utc)
        if reviewed.timestamp() < 0:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_CLOCK_INVALID",
                "Agreement assent coordination clock is outside the reviewed range",
            )
        return reviewed

    @staticmethod
    def _epoch_seconds(value: object) -> int:
        if (
            type(value) is not datetime
            or value.tzinfo is None
            or value.utcoffset() is None
            or value.microsecond != 0
        ):
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                "Agreement assent database time is invalid",
            )
        reviewed = value.astimezone(timezone.utc)
        seconds = int(reviewed.timestamp())
        if seconds < 0:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                "Agreement assent database time is invalid",
            )
        return seconds

    def _expiry(self, now: datetime) -> datetime:
        return now + timedelta(seconds=self._retention_seconds)

    def _open(self) -> tuple[Connection, Cursor]:
        try:
            connection = self._connection_factory()
        except Exception:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_CONNECTION_FAILED",
                "Agreement assent database connection could not be established",
            ) from None
        try:
            cursor = connection.cursor()
        except Exception:
            try:
                connection.close()
            except Exception:
                raise AgreementAssentPostgresError(
                    "AGREEMENT_ASSENT_DATABASE_CONNECTION_CLEANUP_FAILED",
                    "partial Agreement assent database connection cleanup failed",
                ) from None
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_CONNECTION_FAILED",
                "Agreement assent database connection could not be established",
            ) from None
        return connection, cursor

    @staticmethod
    def _rollback(connection: Connection) -> None:
        try:
            connection.rollback()
        except Exception:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_TRANSACTION_ROLLBACK_FAILED",
                "Agreement assent database rollback failed",
            ) from None

    @staticmethod
    def _close(cursor: Cursor | None, connection: Connection | None) -> None:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    @staticmethod
    def _prepared_from_row(
        agreement_record_id: str,
        principal: str,
        row: object,
    ) -> PreparedAgreementAssent:
        if type(row) not in (tuple, list) or len(row) != 3:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                "Agreement assent database row is invalid",
            )
        try:
            return PreparedAgreementAssent(
                agreement_record_id=agreement_record_id,
                principal=principal,
                verification_method=row[0],
                proof_identity=row[1],
                proof_bytes=row[2],
            )
        except Exception:
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                "Agreement assent database row is invalid",
            ) from None

    def _review_window(
        self,
        accepted_at: object,
        expires_at: object,
        now: datetime,
    ) -> tuple[int, int]:
        accepted = self._epoch_seconds(accepted_at)
        expires = self._epoch_seconds(expires_at)
        current = self._epoch_seconds(now)
        if (
            not 0 < expires - accepted <= self._retention_seconds
            or accepted > current
            or expires <= current
        ):
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                "Agreement assent database retention window is invalid",
            )
        return accepted, expires

    def _expire_due_cursor(
        self,
        cursor: Cursor,
        now: datetime,
    ) -> AgreementAssentExpiryResult:
        try:
            cursor.execute(_DELETE_EXPIRED, (now,))
            rows = cursor.fetchall()
            keys: list[tuple[str, str]] = []
            for row in rows:
                if type(row) not in (tuple, list) or len(row) != 2:
                    raise AgreementAssentPostgresRetentionError()
                try:
                    keys.append((_review_record_id(row[0]), _review_uri(row[1])))
                except Exception:
                    raise AgreementAssentPostgresRetentionError() from None
            return AgreementAssentExpiryResult(tuple(keys))
        except AgreementAssentPostgresRetentionError:
            raise
        except Exception:
            raise AgreementAssentPostgresRetentionError() from None

    def apply_migrations(self) -> tuple[int, ...]:
        """Apply only the dedicated assent schema in one transaction."""
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            first = POSTGRES_AGREEMENT_ASSENT_MIGRATIONS[0]
            cursor.execute(first.statements[0])
            cursor.execute(_SELECT_SCHEMA_VERSIONS)
            rows = cursor.fetchall()
            versions = tuple(row[0] for row in rows)
            if any(type(value) is not int or value <= 0 for value in versions):
                raise AgreementAssentPostgresError(
                    "AGREEMENT_ASSENT_SCHEMA_VERSION_INVALID",
                    "Agreement assent database returned an invalid schema version",
                )
            supported = {
                migration.version
                for migration in POSTGRES_AGREEMENT_ASSENT_MIGRATIONS
            }
            if any(version not in supported for version in versions):
                raise AgreementAssentPostgresError(
                    "AGREEMENT_ASSENT_SCHEMA_VERSION_UNSUPPORTED",
                    "Agreement assent database contains an unsupported schema version",
                )
            applied = set(versions)
            now = self._now()
            for index, migration in enumerate(POSTGRES_AGREEMENT_ASSENT_MIGRATIONS):
                if migration.version in applied:
                    continue
                statements = migration.statements[1:] if index == 0 else migration.statements
                for statement in statements:
                    cursor.execute(statement)
                cursor.execute(_INSERT_SCHEMA_VERSION, (migration.version, now))
                applied.add(migration.version)
            cursor.execute(_SCHEMA_FOOTPRINT_CHECK)
            footprint = cursor.fetchone()
            if (
                type(footprint) not in (tuple, list)
                or len(footprint) != 3
                or any(value is not True for value in footprint)
            ):
                raise AgreementAssentPostgresError(
                    "AGREEMENT_ASSENT_SCHEMA_INTEGRITY_INVALID",
                    "Agreement assent database schema footprint is incomplete",
                )
            connection.commit()
            return tuple(sorted(applied))
        except AgreementAssentCoordinationError:
            if connection is not None:
                self._rollback(connection)
            raise
        except Exception:
            if connection is not None:
                self._rollback(connection)
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_MIGRATION_FAILED",
                "Agreement assent database migration failed",
            ) from None
        finally:
            self._close(cursor, connection)

    def initialize(self) -> AgreementAssentExpiryResult:
        self.apply_migrations()
        return self.expire_due()

    def put(self, prepared: PreparedAgreementAssent) -> AgreementAssentPutResult:
        if type(prepared) is not PreparedAgreementAssent:
            raise TypeError("prepared MUST be exact PreparedAgreementAssent")
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            now = self._now()
            cursor.execute(_LOCK_EVIDENCE)
            self._expire_due_cursor(cursor, now)
            cursor.execute(
                _DELETE_EXPIRED_KEY,
                (prepared.agreement_record_id, prepared.principal, now),
            )
            cursor.execute(
                _SELECT_EXISTING_FOR_UPDATE,
                (prepared.agreement_record_id, prepared.principal, now),
            )
            row = cursor.fetchone()
            if row is not None:
                if type(row) not in (tuple, list) or len(row) != 5:
                    raise AgreementAssentPostgresError(
                        "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                        "Agreement assent database row is invalid",
                    )
                existing = self._prepared_from_row(
                    prepared.agreement_record_id,
                    prepared.principal,
                    row[:3],
                )
                accepted, expires = self._review_window(row[3], row[4], now)
                if existing != prepared:
                    raise AgreementAssentCoordinationCollisionError()
                connection.commit()
                return AgreementAssentPutResult(
                    StoreDisposition.DUPLICATE,
                    accepted,
                    expires,
                )
            cursor.execute(_SELECT_ACTIVE_COUNT, (now,))
            count_row = cursor.fetchone()
            if (
                type(count_row) not in (tuple, list)
                or len(count_row) != 1
                or type(count_row[0]) is not int
                or isinstance(count_row[0], bool)
                or count_row[0] < 0
            ):
                raise AgreementAssentPostgresError(
                    "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                    "Agreement assent database count is invalid",
                )
            if count_row[0] >= self._max_entries:
                raise AgreementAssentCoordinationError(
                    "AGREEMENT_ASSENT_COORDINATION_CAPACITY_EXCEEDED",
                    "Agreement assent coordination capacity is exhausted",
                )
            expires_at = self._expiry(now)
            cursor.execute(
                _INSERT_EVIDENCE,
                (
                    prepared.agreement_record_id,
                    prepared.principal,
                    prepared.verification_method,
                    prepared.proof_identity,
                    prepared.proof_bytes,
                    now,
                    expires_at,
                ),
            )
            connection.commit()
            return AgreementAssentPutResult(
                StoreDisposition.STORED,
                self._epoch_seconds(now),
                self._epoch_seconds(expires_at),
            )
        except AgreementAssentCoordinationError:
            if connection is not None:
                self._rollback(connection)
            raise
        except Exception:
            if connection is not None:
                self._rollback(connection)
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_OPERATION_FAILED",
                "Agreement assent database operation failed",
            ) from None
        finally:
            self._close(cursor, connection)

    def peek(
        self,
        agreement_record_id: str,
        principal: str,
    ) -> PreparedAgreementAssent | None:
        reviewed_id = _review_record_id(agreement_record_id)
        reviewed_principal = _review_uri(principal)
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            now = self._now()
            cursor.execute(
                _SELECT_ACTIVE_ONE,
                (reviewed_id, reviewed_principal, now),
            )
            row = cursor.fetchone()
            if row is None:
                result = None
            else:
                if type(row) not in (tuple, list) or len(row) != 5:
                    raise AgreementAssentPostgresError(
                        "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                        "Agreement assent database row is invalid",
                    )
                self._review_window(row[3], row[4], now)
                result = self._prepared_from_row(
                    reviewed_id,
                    reviewed_principal,
                    row[:3],
                )
            connection.commit()
            return result
        except AgreementAssentCoordinationError:
            if connection is not None:
                self._rollback(connection)
            raise
        except Exception:
            if connection is not None:
                self._rollback(connection)
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_OPERATION_FAILED",
                "Agreement assent database operation failed",
            ) from None
        finally:
            self._close(cursor, connection)

    def list_for_agreement(
        self,
        agreement_record_id: str,
        *,
        limit: int = MAX_AGREEMENT_ASSENT_PARTIES,
    ) -> tuple[PreparedAgreementAssent, ...]:
        reviewed_id = _review_record_id(agreement_record_id)
        if (
            type(limit) is not int
            or isinstance(limit, bool)
            or not 1 <= limit <= MAX_AGREEMENT_ASSENT_PARTIES
        ):
            raise ValueError("limit is outside the reviewed party bound")
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            now = self._now()
            cursor.execute(
                _SELECT_ACTIVE_FOR_AGREEMENT,
                (reviewed_id, now, limit + 1),
            )
            rows = cursor.fetchall()
            if len(rows) > limit:
                raise AgreementAssentCoordinationError(
                    "AGREEMENT_ASSENT_EVIDENCE_LIMIT_EXCEEDED",
                    "Agreement assent evidence exceeds the reviewed party bound",
                )
            values: list[PreparedAgreementAssent] = []
            for row in rows:
                if type(row) not in (tuple, list) or len(row) != 6:
                    raise AgreementAssentPostgresError(
                        "AGREEMENT_ASSENT_DATABASE_ROW_INVALID",
                        "Agreement assent database row is invalid",
                    )
                self._review_window(row[4], row[5], now)
                values.append(
                    self._prepared_from_row(
                        reviewed_id,
                        _review_uri(row[0]),
                        row[1:4],
                    )
                )
            connection.commit()
            return tuple(values)
        except AgreementAssentCoordinationError:
            if connection is not None:
                self._rollback(connection)
            raise
        except Exception:
            if connection is not None:
                self._rollback(connection)
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_OPERATION_FAILED",
                "Agreement assent database operation failed",
            ) from None
        finally:
            self._close(cursor, connection)

    def expire_due(self) -> AgreementAssentExpiryResult:
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            result = self._expire_due_cursor(cursor, self._now())
            connection.commit()
            return result
        except AgreementAssentCoordinationError:
            if connection is not None:
                self._rollback(connection)
            raise
        except Exception:
            if connection is not None:
                self._rollback(connection)
            raise AgreementAssentPostgresError(
                "AGREEMENT_ASSENT_DATABASE_OPERATION_FAILED",
                "Agreement assent database operation failed",
            ) from None
        finally:
            self._close(cursor, connection)


__all__ = [
    "AgreementAssentPostgresError",
    "AgreementAssentPostgresMigration",
    "AgreementAssentPostgresRetentionError",
    "POSTGRES_AGREEMENT_ASSENT_MIGRATIONS",
    "PostgresAgreementAssentCoordinationStore",
]
