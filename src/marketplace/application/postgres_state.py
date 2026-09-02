"""PostgreSQL-first Marketplace application coordination state.

This module is deliberately connection-injected.  It defines reviewed PostgreSQL SQL
and bounded application-state semantics without opening sockets, choosing hosts, or
provisioning a database.  Canonical record bytes must be prepared by the existing
Marketplace/OLP validation boundary before they reach this store.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from ..runtime.contracts import StoreDisposition

APPLICATION_STATE_RETENTION_CLASS = "MARKETPLACE_APPLICATION_STATE_MVP"
DEFAULT_APPLICATION_STATE_RETENTION_SECONDS = 30 * 24 * 60 * 60
MAX_APPLICATION_STATE_RETENTION_SECONDS = DEFAULT_APPLICATION_STATE_RETENTION_SECONDS
MAX_CANONICAL_RECORD_BYTES = 256 * 1024
MAX_RESPONSE_TO_REFS = 32
MAX_SYNC_PAGE_SIZE = 256
MAX_RESPONSE_PAGE_SIZE = 256
MAX_EXPIRY_BATCH = 256


class ApplicationStateStoreError(RuntimeError):
    """Stable application persistence failure without database/payload reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ApplicationStateCollisionError(ApplicationStateStoreError):
    def __init__(self) -> None:
        super().__init__(
            "RECORD_IDENTITY_COLLISION",
            "record identity is already bound to nonmatching canonical content",
        )


class ApplicationStateRetentionError(ApplicationStateStoreError):
    def __init__(self) -> None:
        super().__init__(
            "RETENTION_DELETE_FAILED",
            "expired local application state could not be deleted safely",
        )


@dataclass(frozen=True, slots=True)
class PreparedApplicationRecord:
    """Validated/canonical application persistence input.

    The database adapter intentionally does not validate Marketplace semantics itself;
    callers must construct this only after existing Marketplace validation, exact OLP
    Record Identity derivation, and canonical serialization have succeeded.
    """

    record_id: str
    canonical_record: bytes
    response_to: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.record_id) is not str or not self.record_id:
            raise ValueError("record_id MUST be non-empty exact text")
        if type(self.canonical_record) is not bytes:
            raise TypeError("canonical_record MUST be exact bytes")
        if not self.canonical_record:
            raise ValueError("canonical_record MUST NOT be empty")
        if len(self.canonical_record) > MAX_CANONICAL_RECORD_BYTES:
            raise ValueError("canonical_record exceeds the reviewed byte bound")
        if type(self.response_to) is not tuple:
            raise TypeError("response_to MUST be an exact tuple")
        if len(self.response_to) > MAX_RESPONSE_TO_REFS:
            raise ValueError("response_to exceeds the reviewed reference bound")
        if any(type(value) is not str or not value for value in self.response_to):
            raise ValueError("response_to entries MUST be non-empty exact text")
        if len(set(self.response_to)) != len(self.response_to):
            raise ValueError("response_to MUST NOT contain duplicate identities")


@dataclass(frozen=True, slots=True)
class ApplicationStatePutResult:
    disposition: StoreDisposition
    change_seq: int | None


@dataclass(frozen=True, slots=True)
class SyncChange:
    seq: int
    record_id: str
    change_kind: str


@dataclass(frozen=True, slots=True)
class SyncPage:
    changes: tuple[SyncChange, ...]
    next_cursor: int
    has_more: bool


@dataclass(frozen=True, slots=True)
class ExpiryResult:
    deleted_record_ids: tuple[str, ...]
    tombstone_sequences: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PostgresMigration:
    version: int
    statements: tuple[str, ...]


POSTGRES_APPLICATION_STATE_MIGRATIONS = (
    PostgresMigration(
        version=1,
        statements=(
            """
CREATE TABLE IF NOT EXISTS marketplace_app_schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    applied_at TIMESTAMPTZ NOT NULL
)
""",
            """
CREATE TABLE IF NOT EXISTS marketplace_app_records (
    record_id TEXT PRIMARY KEY,
    canonical_record BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    CHECK (octet_length(canonical_record) > 0)
)
""",
            """
CREATE TABLE IF NOT EXISTS marketplace_app_response_links (
    parent_record_id TEXT NOT NULL,
    response_record_id TEXT NOT NULL REFERENCES marketplace_app_records(record_id) ON DELETE CASCADE,
    PRIMARY KEY (parent_record_id, response_record_id)
)
""",
            """
CREATE TABLE IF NOT EXISTS marketplace_app_changes (
    seq BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id TEXT NOT NULL,
    change_kind TEXT NOT NULL CHECK (change_kind IN ('UPSERT', 'DELETE')),
    changed_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
)
""",
            """
CREATE TABLE IF NOT EXISTS marketplace_app_sync_state (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    floor_seq BIGINT NOT NULL CHECK (floor_seq >= 0)
)
""",
            """
INSERT INTO marketplace_app_sync_state (singleton, floor_seq)
VALUES (TRUE, 0)
ON CONFLICT (singleton) DO NOTHING
""",
            """
CREATE INDEX IF NOT EXISTS marketplace_app_records_expires_idx
ON marketplace_app_records (expires_at, record_id)
""",
            """
CREATE INDEX IF NOT EXISTS marketplace_app_response_parent_idx
ON marketplace_app_response_links (parent_record_id, response_record_id)
""",
            """
CREATE INDEX IF NOT EXISTS marketplace_app_changes_expires_idx
ON marketplace_app_changes (expires_at, seq)
""",
        ),
    ),
)


class Cursor(Protocol):
    def execute(self, sql: str, params: object = None) -> None: ...
    def fetchall(self): ...
    def fetchone(self): ...
    def close(self) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...


ConnectionFactory = Callable[[], Connection]
Clock = Callable[[], datetime]


_SELECT_SCHEMA_VERSIONS = "SELECT version FROM marketplace_app_schema_migrations ORDER BY version"
_INSERT_SCHEMA_VERSION = "INSERT INTO marketplace_app_schema_migrations (version, applied_at) VALUES (%s, %s)"
_SCHEMA_FOOTPRINT_CHECK = """
SELECT
    to_regclass('marketplace_app_schema_migrations') IS NOT NULL,
    to_regclass('marketplace_app_records') IS NOT NULL,
    to_regclass('marketplace_app_response_links') IS NOT NULL,
    to_regclass('marketplace_app_changes') IS NOT NULL,
    to_regclass('marketplace_app_sync_state') IS NOT NULL,
    to_regclass('marketplace_app_records_expires_idx') IS NOT NULL,
    to_regclass('marketplace_app_response_parent_idx') IS NOT NULL,
    to_regclass('marketplace_app_changes_expires_idx') IS NOT NULL
"""


_SELECT_RECORD_FOR_UPDATE = """
SELECT record_id, canonical_record
FROM marketplace_app_records
WHERE record_id = %s
FOR UPDATE
"""

_INSERT_RECORD = """
INSERT INTO marketplace_app_records
(record_id, canonical_record, created_at, last_used_at, expires_at)
VALUES (%s, %s, %s, %s, %s)
"""

_SELECT_RESPONSE_PARENTS = """
SELECT parent_record_id
FROM marketplace_app_response_links
WHERE response_record_id = %s
ORDER BY parent_record_id
"""

_INSERT_RESPONSE_LINK = """
INSERT INTO marketplace_app_response_links
(parent_record_id, response_record_id)
VALUES (%s, %s)
"""

_REFRESH_RECORD = """
UPDATE marketplace_app_records
SET last_used_at = %s, expires_at = %s
WHERE record_id = %s
"""

_INSERT_CHANGE = """
INSERT INTO marketplace_app_changes
(record_id, change_kind, changed_at, expires_at)
VALUES (%s, %s, %s, %s)
RETURNING seq
"""

_SELECT_RECORD = """
SELECT canonical_record
FROM marketplace_app_records
WHERE record_id = %s
"""

_SELECT_RESPONSES = """
SELECT response_record_id
FROM marketplace_app_response_links
WHERE parent_record_id = %s
ORDER BY response_record_id
LIMIT %s
"""

_SELECT_SYNC_FLOOR = "SELECT floor_seq FROM marketplace_app_sync_state WHERE singleton = TRUE"
_SELECT_SYNC_CHANGES = """
SELECT seq, record_id, change_kind
FROM marketplace_app_changes
WHERE seq > %s
ORDER BY seq
LIMIT %s
"""

_DELETE_EXPIRED_RECORDS_MAINTENANCE = """
/* M17_RETENTION_MAINTENANCE */
DELETE FROM marketplace_app_records
WHERE record_id IN (
    SELECT record_id
    FROM marketplace_app_records
    WHERE expires_at <= %s
    ORDER BY record_id
    LIMIT %s
    FOR UPDATE SKIP LOCKED
)
RETURNING record_id
"""

_DELETE_EXPIRED_RECORDS = """
DELETE FROM marketplace_app_records
WHERE record_id IN (
    SELECT record_id
    FROM marketplace_app_records
    WHERE expires_at <= %s
    ORDER BY record_id
    LIMIT %s
    FOR UPDATE SKIP LOCKED
)
RETURNING record_id
"""

_DELETE_EXPIRED_CHANGES_MAINTENANCE = """
/* M17_CHANGE_RETENTION_MAINTENANCE */
DELETE FROM marketplace_app_changes
WHERE seq IN (
    SELECT seq
    FROM marketplace_app_changes
    WHERE expires_at <= %s
    ORDER BY seq
    LIMIT %s
    FOR UPDATE SKIP LOCKED
)
RETURNING seq
"""

_ADVANCE_SYNC_FLOOR = """
UPDATE marketplace_app_sync_state
SET floor_seq = GREATEST(floor_seq, %s)
WHERE singleton = TRUE
"""


class PostgresApplicationStateStore:
    """Bounded PostgreSQL application state over an injected DB-API connection."""

    retention_class = APPLICATION_STATE_RETENTION_CLASS

    def __init__(
        self,
        *,
        connection_factory: ConnectionFactory,
        clock: Clock,
        retention_seconds: float = DEFAULT_APPLICATION_STATE_RETENTION_SECONDS,
    ) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory MUST be callable")
        if not callable(clock):
            raise TypeError("clock MUST be callable")
        if isinstance(retention_seconds, bool) or not isinstance(retention_seconds, (int, float)):
            raise TypeError("retention_seconds MUST be numeric")
        if retention_seconds <= 0 or retention_seconds > MAX_APPLICATION_STATE_RETENTION_SECONDS:
            raise ValueError("application-state retention MUST be >0 and <=30 days")
        self._connection_factory = connection_factory
        self._clock = clock
        self._retention_seconds = float(retention_seconds)

    @property
    def retention_seconds(self) -> float:
        return self._retention_seconds

    def _now(self) -> datetime:
        value = self._clock()
        if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
            raise ApplicationStateStoreError(
                "CLOCK_INVALID",
                "application-state clock must return an aware datetime",
            )
        return value.astimezone(timezone.utc)

    def _expiry(self, now: datetime) -> datetime:
        return now + timedelta(seconds=self._retention_seconds)

    def _open(self) -> tuple[Connection, Cursor]:
        try:
            connection = self._connection_factory()
            cursor = connection.cursor()
            return connection, cursor
        except Exception:
            raise ApplicationStateStoreError(
                "DATABASE_CONNECTION_FAILED",
                "application database connection could not be established",
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

    def apply_migrations(self) -> tuple[int, ...]:
        """Apply the exact reviewed PostgreSQL schema in one bounded transaction."""
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            first = POSTGRES_APPLICATION_STATE_MIGRATIONS[0]
            cursor.execute(first.statements[0])
            cursor.execute(_SELECT_SCHEMA_VERSIONS)
            rows = cursor.fetchall()
            versions = tuple(row[0] for row in rows)
            if any(type(value) is not int or value <= 0 for value in versions):
                raise ApplicationStateStoreError(
                    "SCHEMA_VERSION_INVALID",
                    "application database returned an invalid schema version",
                )
            supported = {migration.version for migration in POSTGRES_APPLICATION_STATE_MIGRATIONS}
            if any(version not in supported for version in versions):
                raise ApplicationStateStoreError(
                    "SCHEMA_VERSION_UNSUPPORTED",
                    "application database contains an unsupported schema version",
                )
            applied = set(versions)
            now = self._now()
            for migration_index, migration in enumerate(POSTGRES_APPLICATION_STATE_MIGRATIONS):
                if migration.version in applied:
                    continue
                statements = migration.statements[1:] if migration_index == 0 else migration.statements
                for statement in statements:
                    cursor.execute(statement)
                cursor.execute(_INSERT_SCHEMA_VERSION, (migration.version, now))
                applied.add(migration.version)
            cursor.execute(_SCHEMA_FOOTPRINT_CHECK)
            footprint = cursor.fetchone()
            if (
                type(footprint) not in (tuple, list)
                or len(footprint) != 8
                or any(value is not True for value in footprint)
            ):
                raise ApplicationStateStoreError(
                    "SCHEMA_INTEGRITY_INVALID",
                    "application database schema footprint is incomplete or inconsistent",
                )
            connection.commit()
            return tuple(sorted(applied))
        except ApplicationStateStoreError:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise ApplicationStateStoreError(
                "MIGRATION_FAILED",
                "application database migration failed",
            ) from None
        finally:
            self._close(cursor, connection)

    def initialize(self) -> ExpiryResult:
        """Apply schema then perform mandatory startup expiry cleanup."""
        self.apply_migrations()
        return self.expire_due()

    def _expire_sync_metadata_cursor(self, cursor: Cursor, now: datetime) -> None:
        try:
            cursor.execute(
                _DELETE_EXPIRED_CHANGES_MAINTENANCE,
                (now, MAX_EXPIRY_BATCH),
            )
            rows = cursor.fetchall()
            sequences = tuple(row[0] for row in rows)
            if any(type(value) is not int or value <= 0 for value in sequences):
                raise ApplicationStateRetentionError()
            if sequences:
                cursor.execute(_ADVANCE_SYNC_FLOOR, (max(sequences),))
        except ApplicationStateRetentionError:
            raise
        except Exception:
            raise ApplicationStateRetentionError() from None

    def _expire_due_cursor(
        self,
        cursor: Cursor,
        now: datetime,
        *,
        automatic: bool,
    ) -> ExpiryResult:
        sql = _DELETE_EXPIRED_RECORDS_MAINTENANCE if automatic else _DELETE_EXPIRED_RECORDS
        try:
            cursor.execute(sql, (now, MAX_EXPIRY_BATCH))
            deleted = tuple(row[0] for row in cursor.fetchall())
            if any(type(value) is not str or not value for value in deleted):
                raise ApplicationStateRetentionError()
            sequences: list[int] = []
            tombstone_expiry = self._expiry(now)
            for record_id in deleted:
                cursor.execute(
                    _INSERT_CHANGE,
                    (record_id, "DELETE", now, tombstone_expiry),
                )
                row = cursor.fetchone()
                if type(row) not in (tuple, list) or len(row) != 1 or type(row[0]) is not int:
                    raise ApplicationStateRetentionError()
                sequences.append(row[0])
            self._expire_sync_metadata_cursor(cursor, now)
            return ExpiryResult(deleted, tuple(sequences))
        except ApplicationStateRetentionError:
            raise
        except Exception:
            raise ApplicationStateRetentionError() from None

    def put(self, prepared: PreparedApplicationRecord) -> ApplicationStatePutResult:
        if type(prepared) is not PreparedApplicationRecord:
            raise TypeError("prepared MUST be exact PreparedApplicationRecord")
        now = self._now()
        expires = self._expiry(now)
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            self._expire_due_cursor(cursor, now, automatic=True)
            cursor.execute(_SELECT_RECORD_FOR_UPDATE, (prepared.record_id,))
            existing = cursor.fetchone()
            if existing is not None:
                if type(existing) not in (tuple, list) or len(existing) != 2:
                    raise ApplicationStateStoreError(
                        "DATABASE_RESULT_INVALID",
                        "application database returned an invalid record row",
                    )
                existing_bytes = existing[1]
                if type(existing_bytes) is not bytes:
                    existing_bytes = bytes(existing_bytes)
                if existing_bytes != prepared.canonical_record:
                    raise ApplicationStateCollisionError()
                cursor.execute(_SELECT_RESPONSE_PARENTS, (prepared.record_id,))
                parents = tuple(row[0] for row in cursor.fetchall())
                if parents != tuple(sorted(prepared.response_to)):
                    raise ApplicationStateStoreError(
                        "APPLICATION_INDEX_COLLISION",
                        "canonical record and application response index disagree",
                    )
                cursor.execute(_REFRESH_RECORD, (now, expires, prepared.record_id))
                self._expire_due_cursor(cursor, now, automatic=True)
                connection.commit()
                return ApplicationStatePutResult(StoreDisposition.DUPLICATE, None)

            cursor.execute(
                _INSERT_RECORD,
                (prepared.record_id, prepared.canonical_record, now, now, expires),
            )
            for parent_id in sorted(prepared.response_to):
                cursor.execute(_INSERT_RESPONSE_LINK, (parent_id, prepared.record_id))
            cursor.execute(
                _INSERT_CHANGE,
                (prepared.record_id, "UPSERT", now, expires),
            )
            row = cursor.fetchone()
            if type(row) not in (tuple, list) or len(row) != 1 or type(row[0]) is not int:
                raise ApplicationStateStoreError(
                    "DATABASE_RESULT_INVALID",
                    "application database returned an invalid change sequence",
                )
            change_seq = row[0]
            self._expire_due_cursor(cursor, now, automatic=True)
            connection.commit()
            return ApplicationStatePutResult(StoreDisposition.STORED, change_seq)
        except ApplicationStateStoreError:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise ApplicationStateStoreError(
                "DATABASE_OPERATION_FAILED",
                "application database operation failed",
            ) from None
        finally:
            self._close(cursor, connection)

    def get(self, record_id: str) -> PreparedApplicationRecord | None:
        if type(record_id) is not str or not record_id:
            raise ValueError("record_id MUST be non-empty exact text")
        now = self._now()
        expires = self._expiry(now)
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            cursor.execute(_SELECT_RECORD, (record_id,))
            row = cursor.fetchone()
            if row is None:
                connection.commit()
                return None
            if type(row) not in (tuple, list) or len(row) != 1:
                raise ApplicationStateStoreError(
                    "DATABASE_RESULT_INVALID", "application database returned an invalid record row"
                )
            canonical = row[0]
            if type(canonical) is not bytes:
                canonical = bytes(canonical)
            cursor.execute(_REFRESH_RECORD, (now, expires, record_id))
            cursor.execute(_SELECT_RESPONSE_PARENTS, (record_id,))
            parents = tuple(row[0] for row in cursor.fetchall())
            result = PreparedApplicationRecord(record_id, canonical, parents)
            connection.commit()
            return result
        except ApplicationStateStoreError:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise ApplicationStateStoreError(
                "DATABASE_OPERATION_FAILED", "application database operation failed"
            ) from None
        finally:
            self._close(cursor, connection)

    def list_response_ids(self, parent_record_id: str, *, limit: int = 64) -> tuple[str, ...]:
        if type(parent_record_id) is not str or not parent_record_id:
            raise ValueError("parent_record_id MUST be non-empty exact text")
        if type(limit) is not int or isinstance(limit, bool) or not 1 <= limit <= MAX_RESPONSE_PAGE_SIZE:
            raise ValueError("limit is outside the reviewed response-page bound")
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            cursor.execute(_SELECT_RESPONSES, (parent_record_id, limit))
            rows = cursor.fetchall()
            values = tuple(row[0] for row in rows)
            if any(type(value) is not str or not value for value in values):
                raise ApplicationStateStoreError(
                    "DATABASE_RESULT_INVALID", "application database returned an invalid response index"
                )
            connection.commit()
            return values
        except ApplicationStateStoreError:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise ApplicationStateStoreError(
                "DATABASE_OPERATION_FAILED", "application database operation failed"
            ) from None
        finally:
            self._close(cursor, connection)

    def sync_since(self, cursor_value: int, *, limit: int = 128) -> SyncPage:
        if type(cursor_value) is not int or isinstance(cursor_value, bool) or cursor_value < 0:
            raise ValueError("sync cursor MUST be a non-negative exact integer")
        if type(limit) is not int or isinstance(limit, bool) or not 1 <= limit <= MAX_SYNC_PAGE_SIZE:
            raise ValueError("limit is outside the reviewed sync-page bound")
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            cursor.execute(_SELECT_SYNC_FLOOR)
            floor_row = cursor.fetchone()
            if type(floor_row) not in (tuple, list) or len(floor_row) != 1 or type(floor_row[0]) is not int:
                raise ApplicationStateStoreError(
                    "DATABASE_RESULT_INVALID", "application database returned an invalid sync floor"
                )
            if cursor_value < floor_row[0]:
                raise ApplicationStateStoreError(
                    "SYNC_CURSOR_EXPIRED",
                    "sync cursor predates retained application coordination metadata",
                )
            cursor.execute(_SELECT_SYNC_CHANGES, (cursor_value, limit + 1))
            rows = cursor.fetchall()
            parsed: list[SyncChange] = []
            for row in rows:
                if type(row) not in (tuple, list) or len(row) != 3:
                    raise ApplicationStateStoreError(
                        "DATABASE_RESULT_INVALID", "application database returned an invalid sync row"
                    )
                seq, record_id, kind = row
                if type(seq) is not int or type(record_id) is not str or not record_id or kind not in {"UPSERT", "DELETE"}:
                    raise ApplicationStateStoreError(
                        "DATABASE_RESULT_INVALID", "application database returned an invalid sync row"
                    )
                parsed.append(SyncChange(seq, record_id, kind))
            has_more = len(parsed) > limit
            selected = tuple(parsed[:limit])
            next_cursor = selected[-1].seq if selected else cursor_value
            connection.commit()
            return SyncPage(selected, next_cursor, has_more)
        except ApplicationStateStoreError:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise ApplicationStateStoreError(
                "DATABASE_OPERATION_FAILED", "application database operation failed"
            ) from None
        finally:
            self._close(cursor, connection)

    def expire_due(self) -> ExpiryResult:
        now = self._now()
        connection: Connection | None = None
        cursor: Cursor | None = None
        try:
            connection, cursor = self._open()
            result = self._expire_due_cursor(cursor, now, automatic=False)
            connection.commit()
            return result
        except ApplicationStateRetentionError:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise
        except Exception:
            if connection is not None:
                try:
                    connection.rollback()
                except Exception:
                    pass
            raise ApplicationStateRetentionError() from None
        finally:
            self._close(cursor, connection)


__all__ = [
    "APPLICATION_STATE_RETENTION_CLASS",
    "DEFAULT_APPLICATION_STATE_RETENTION_SECONDS",
    "MAX_APPLICATION_STATE_RETENTION_SECONDS",
    "POSTGRES_APPLICATION_STATE_MIGRATIONS",
    "ApplicationStateCollisionError",
    "ApplicationStatePutResult",
    "ApplicationStateRetentionError",
    "ApplicationStateStoreError",
    "ExpiryResult",
    "PreparedApplicationRecord",
    "PostgresApplicationStateStore",
    "PostgresMigration",
    "StoreDisposition",
    "SyncChange",
    "SyncPage",
]