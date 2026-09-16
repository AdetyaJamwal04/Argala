import logging
import os
import sqlite3
from typing import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Default SQLite database path in the working directory
DB_DIR = os.environ.get("GATEWAY_DATA_DIR", "data")
DB_PATH = os.path.join(DB_DIR, "argala.db")
LEGACY_DB_PATH = os.path.join(DB_DIR, "aegisedge.db")


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and configures an SQLite connection with WAL mode and defensive busy timeout.
    """
    os.makedirs(DB_DIR, exist_ok=True)

    # Seamless migration from legacy DB file if present
    if os.path.exists(LEGACY_DB_PATH) and not os.path.exists(DB_PATH):
        try:
            import shutil
            shutil.copy2(LEGACY_DB_PATH, DB_PATH)
            logger.info("Migrated legacy database '%s' to '%s'", LEGACY_DB_PATH, DB_PATH)
        except Exception as e:
            logger.warning("Could not auto-migrate legacy database: %s", e)

    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row

    # Performance & Concurrency Pragmas
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()

    return conn


@contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for atomic database transactions with auto-commit/rollback."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Initializes database tables and performance indexes.
    Idempotent: safe to run multiple times during startup.
    """
    with db_session() as conn:
        cursor = conn.cursor()

        # 1. Durable Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            idempotency_key TEXT UNIQUE,
            capability TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            result TEXT,
            error TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            worker_id TEXT,
            lease_expires_at REAL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            completed_at REAL
        );
        """)

        # Performance indexes for fast queue polling and idempotency lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_lease ON jobs(status, lease_expires_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_idempotency ON jobs(idempotency_key);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);")

        # 2. Gateway State Table (For persistent Emergency Lockdown & Operational state)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gateway_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL NOT NULL
        );
        """)

        # 3. Revocation Ledger Table (For revoked principals, nonces, and session tokens)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS revocation_ledger (
            id TEXT PRIMARY KEY,
            revocation_type TEXT NOT NULL,
            target TEXT NOT NULL,
            reason TEXT,
            revoked_at REAL NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_revocation_target ON revocation_ledger(target);")

        cursor.close()
        logger.info("Initialized SQLite database in WAL mode at: %s", DB_PATH)
