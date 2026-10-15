"""SQLite access layer: thread-local connections, migrations, unit of work.

All SQL lives in app/repositories and this module. To migrate to PostgreSQL, provide another
`Database` implementation exposing `unit_of_work()` and re-implement the repositories; the services,
the AI engine and the API depend only on those interfaces.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List

from app.core.errors import ConfigurationError, DatabaseError
from app.database.migrations import LATEST_SCHEMA_VERSION, MIGRATIONS
from app.utils.timeutil import utc_now_iso


def sqlite_path_from_url(url: str, root: Path) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ConfigurationError(
            f"Unsupported DATABASE_URL '{url.split(':')[0]}://...'. The bundled adapter supports sqlite:/// only; "
            "see docs/database.md for the PostgreSQL migration path.")
    raw = url[len(prefix):]
    path = Path(raw)
    return path if path.is_absolute() else (root / path)


class UnitOfWork:
    """Groups repositories on one connection so a failed analysis never leaves half-written data."""

    def __init__(self, conn: sqlite3.Connection):
        from app.repositories import (AnalyticsRepository, AuditRepository, FactRepository, InferenceRepository,
                                      ReportRepository, RuleRepository, TransactionRepository, UserRepository)
        self.conn = conn
        self.users = UserRepository(conn)
        self.transactions = TransactionRepository(conn)
        self.facts = FactRepository(conn)
        self.rules = RuleRepository(conn)
        self.inference = InferenceRepository(conn)
        self.audit = AuditRepository(conn)
        self.reports = ReportRepository(conn)
        self.analytics = AnalyticsRepository(conn)


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._local = threading.local()
        self._connections: List[sqlite3.Connection] = []
        self._lock = threading.Lock()

    # -- connections -----------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.path), timeout=10, isolation_level=None, check_same_thread=False)
        except (sqlite3.Error, OSError) as exc:
            raise DatabaseError(f"Cannot open database at {self.path}: {exc}. Check that the directory exists and is writable.") from exc
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 8000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        with self._lock:
            self._connections.append(conn)
        return conn

    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def close_all(self) -> None:
        with self._lock:
            for c in self._connections:
                try:
                    c.close()
                except sqlite3.Error:
                    pass
            self._connections.clear()
        self._local = threading.local()

    @contextmanager
    def unit_of_work(self) -> Iterator[UnitOfWork]:
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not start a database transaction: {exc}") from exc
        try:
            yield UnitOfWork(conn)
            conn.execute("COMMIT")
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise

    def read(self) -> UnitOfWork:
        """Repositories for read-only use (no explicit transaction)."""
        return UnitOfWork(self.connection())

    # -- schema ----------------------------------------------------------------------------
    def schema_version(self) -> int:
        conn = self.connection()
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
        if not row:
            return 0
        v = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()["v"]
        return int(v or 0)

    def initialize(self) -> int:
        """Create or upgrade the schema. Refuses to run against a newer, unknown schema."""
        conn = self.connection()
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, description TEXT NOT NULL, applied_at TEXT NOT NULL)")
        current = self.schema_version()
        if current > LATEST_SCHEMA_VERSION:
            raise DatabaseError(f"Database schema v{current} is newer than this application (v{LATEST_SCHEMA_VERSION}). Upgrade the application.")
        for version, description, script in MIGRATIONS:
            if version <= current:
                continue
            try:
                conn.execute("BEGIN IMMEDIATE")
                for statement in [s.strip() for s in script.split(";") if s.strip()]:
                    conn.execute(statement)
                conn.execute("INSERT INTO schema_version(version, description, applied_at) VALUES (?,?,?)",
                             (version, description, utc_now_iso()))
                conn.execute("COMMIT")
            except sqlite3.Error as exc:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise DatabaseError(f"Migration {version} failed and was rolled back: {exc}") from exc
        return self.schema_version()

    def verify_schema(self) -> List[str]:
        """Return a list of problems (missing tables) - empty means the schema is valid."""
        required = {"users", "transactions", "transaction_features", "facts", "rules", "rule_executions",
                    "inference_results", "recommendations", "audit_logs", "reports", "schema_version"}
        have = {r["name"] for r in self.connection().execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return [f"missing table: {t}" for t in sorted(required - have)]

    def ping(self) -> bool:
        try:
            self.connection().execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def backup_to(self, destination: Path) -> None:
        dest = sqlite3.connect(str(destination))
        try:
            self.connection().backup(dest)
        finally:
            dest.close()
