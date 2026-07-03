"""
db_guard.py — Database self-healing system for Prokhor bot.

Runs synchronously at startup (before the async event loop) to guarantee
the SQLite schema is always up to date. Safe and idempotent — only ADDS
missing tables and columns, never deletes or modifies existing data.

Public API
----------
ensure_db_schema(conn)  — apply schema; call once before asyncio.run(main())
db_execute(conn, sql, params=())  — execute with automatic schema-retry on
                                    sqlite3.OperationalError
"""

import logging
import sqlite3

log = logging.getLogger(__name__)

# ── In-memory lock: prevent double-execution within the same process ────────
_schema_applied: bool = False

# ── Canonical schema — single source of truth ───────────────────────────────
# "create"  : full CREATE TABLE IF NOT EXISTS DDL
# "columns" : list of (col_name, alter_table_type_and_default) tuples
#             — used to ALTER TABLE ADD COLUMN for columns missing from
#               existing tables. No PRIMARY KEY / UNIQUE here; SQLite
#               does not allow those via ALTER TABLE.
DB_SCHEMA: dict = {
    "fsm_storage": {
        "create": """
            CREATE TABLE IF NOT EXISTS fsm_storage (
                key   TEXT PRIMARY KEY,
                state TEXT,
                data  TEXT NOT NULL DEFAULT '{}'
            )
        """,
        "columns": [
            ("state", "TEXT"),
            ("data",  "TEXT DEFAULT '{}'"),
        ],
    },

    "psychologists": {
        "create": """
            CREATE TABLE IF NOT EXISTS psychologists (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                language   TEXT DEFAULT 'en',
                created_at TEXT,
                timezone   TEXT DEFAULT 'UTC',
                utc_offset INTEGER DEFAULT 0
            )
        """,
        "columns": [
            ("username",   "TEXT"),
            ("language",   "TEXT DEFAULT 'en'"),
            ("created_at", "TEXT"),
            ("timezone",   "TEXT DEFAULT 'UTC'"),
            ("utc_offset", "INTEGER DEFAULT 0"),
        ],
    },

    "clients": {
        "create": """
            CREATE TABLE IF NOT EXISTS clients (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id  INTEGER,
                name             TEXT,
                created_at       TEXT,
                telegram_id      INTEGER,
                invite_token     TEXT,
                language         TEXT DEFAULT 'en',
                is_archived      INTEGER DEFAULT 0,
                timezone         TEXT DEFAULT 'UTC',
                utc_offset       INTEGER DEFAULT 0,
                recurring_paused INTEGER DEFAULT 0,
                UNIQUE(psychologist_id, name)
            )
        """,
        "columns": [
            ("psychologist_id",  "INTEGER"),
            ("name",             "TEXT"),
            ("created_at",       "TEXT"),
            ("telegram_id",      "INTEGER"),
            ("invite_token",     "TEXT"),
            ("language",         "TEXT DEFAULT 'en'"),
            ("is_archived",      "INTEGER DEFAULT 0"),
            ("timezone",         "TEXT DEFAULT 'UTC'"),
            ("utc_offset",       "INTEGER DEFAULT 0"),
            ("recurring_paused", "INTEGER DEFAULT 0"),
        ],
    },

    "notes": {
        "create": """
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id  INTEGER,
                text       TEXT,
                note_type  TEXT DEFAULT 'plain',
                created_at TEXT
            )
        """,
        "columns": [
            ("client_id",  "INTEGER"),
            ("text",       "TEXT"),
            ("note_type",  "TEXT DEFAULT 'plain'"),
            ("created_at", "TEXT"),
        ],
    },

    "checkins": {
        "create": """
            CREATE TABLE IF NOT EXISTS checkins (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                score     INTEGER,
                auto      INTEGER DEFAULT 0,
                timestamp TEXT
            )
        """,
        "columns": [
            ("client_id", "INTEGER"),
            ("score",     "INTEGER"),
            ("auto",      "INTEGER DEFAULT 0"),
            ("timestamp", "TEXT"),
        ],
    },

    "reminders": {
        "create": """
            CREATE TABLE IF NOT EXISTS reminders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                client_name     TEXT,
                time_minutes    INTEGER
            )
        """,
        "columns": [
            ("psychologist_id", "INTEGER"),
            ("client_name",     "TEXT"),
            ("time_minutes",    "INTEGER"),
        ],
    },

    "sessions": {
        "create": """
            CREATE TABLE IF NOT EXISTS sessions (
                id                          INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id             INTEGER,
                client_name                 TEXT,
                scheduled_at                TEXT,
                link                        TEXT,
                reminded_24h                INTEGER DEFAULT 0,
                reminded_1h                 INTEGER DEFAULT 0,
                topic                       TEXT DEFAULT '',
                recurring                   INTEGER DEFAULT 0,
                days_of_week                TEXT DEFAULT '',
                booking_status              TEXT DEFAULT 'confirmed',
                proposed_start_datetime_utc TEXT
            )
        """,
        "columns": [
            ("psychologist_id",             "INTEGER"),
            ("client_name",                 "TEXT"),
            ("scheduled_at",                "TEXT"),
            ("link",                        "TEXT"),
            ("reminded_24h",                "INTEGER DEFAULT 0"),
            ("reminded_1h",                 "INTEGER DEFAULT 0"),
            ("topic",                       "TEXT DEFAULT ''"),
            ("recurring",                   "INTEGER DEFAULT 0"),
            ("days_of_week",                "TEXT DEFAULT ''"),
            ("booking_status",              "TEXT DEFAULT 'confirmed'"),
            ("proposed_start_datetime_utc", "TEXT"),
        ],
    },

    "auto_checkins": {
        "create": """
            CREATE TABLE IF NOT EXISTS auto_checkins (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                client_name     TEXT,
                interval_min    INTEGER,
                last_sent       TEXT,
                UNIQUE(psychologist_id, client_name)
            )
        """,
        "columns": [
            ("psychologist_id", "INTEGER"),
            ("client_name",     "TEXT"),
            ("interval_min",    "INTEGER"),
            ("last_sent",       "TEXT"),
        ],
    },

    "homeworks": {
        "create": """
            CREATE TABLE IF NOT EXISTS homeworks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id  INTEGER NOT NULL,
                text       TEXT NOT NULL,
                created_at TEXT,
                completed  INTEGER DEFAULT 0
            )
        """,
        "columns": [
            ("client_id",  "INTEGER"),
            ("text",       "TEXT"),
            ("created_at", "TEXT"),
            ("completed",  "INTEGER DEFAULT 0"),
        ],
    },

    "client_tags": {
        "create": """
            CREATE TABLE IF NOT EXISTS client_tags (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                tag       TEXT NOT NULL
            )
        """,
        "columns": [
            ("client_id", "INTEGER"),
            ("tag",       "TEXT"),
        ],
    },

    "cohorts": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohorts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id  INTEGER NOT NULL,
                name             TEXT NOT NULL,
                description      TEXT DEFAULT '',
                type             TEXT DEFAULT 'group',
                max_participants INTEGER DEFAULT 12,
                start_date       TEXT,
                end_date         TEXT,
                status           TEXT DEFAULT 'active',
                created_at       TEXT,
                invite_token     TEXT UNIQUE,
                recurring_paused INTEGER DEFAULT 0
            )
        """,
        "columns": [
            ("psychologist_id",  "INTEGER"),
            ("name",             "TEXT"),
            ("description",      "TEXT DEFAULT ''"),
            ("type",             "TEXT DEFAULT 'group'"),
            ("max_participants", "INTEGER DEFAULT 12"),
            ("start_date",       "TEXT"),
            ("end_date",         "TEXT"),
            ("status",           "TEXT DEFAULT 'active'"),
            ("created_at",       "TEXT"),
            ("invite_token",     "TEXT"),
            ("recurring_paused", "INTEGER DEFAULT 0"),
        ],
    },

    "cohort_members": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohort_members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id   INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                name        TEXT,
                joined_at   TEXT,
                status      TEXT DEFAULT 'active',
                UNIQUE(cohort_id, telegram_id)
            )
        """,
        "columns": [
            ("cohort_id",   "INTEGER"),
            ("telegram_id", "INTEGER"),
            ("name",        "TEXT"),
            ("joined_at",   "TEXT"),
            ("status",      "TEXT DEFAULT 'active'"),
        ],
    },

    "cohort_sessions": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohort_sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id      INTEGER NOT NULL,
                session_number INTEGER NOT NULL,
                scheduled_at   TEXT NOT NULL,
                topic          TEXT DEFAULT '',
                link           TEXT DEFAULT '',
                reminded_24h   INTEGER DEFAULT 0,
                reminded_1h    INTEGER DEFAULT 0,
                status         TEXT DEFAULT 'scheduled',
                recurring      INTEGER DEFAULT 0,
                days_of_week   TEXT DEFAULT ''
            )
        """,
        "columns": [
            ("cohort_id",      "INTEGER"),
            ("session_number", "INTEGER"),
            ("scheduled_at",   "TEXT"),
            ("topic",          "TEXT DEFAULT ''"),
            ("link",           "TEXT DEFAULT ''"),
            ("reminded_24h",   "INTEGER DEFAULT 0"),
            ("reminded_1h",    "INTEGER DEFAULT 0"),
            ("status",         "TEXT DEFAULT 'scheduled'"),
            ("recurring",      "INTEGER DEFAULT 0"),
            ("days_of_week",   "TEXT DEFAULT ''"),
        ],
    },

    "cohort_attendance": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohort_attendance (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                member_id  INTEGER NOT NULL,
                status     TEXT DEFAULT 'pending',
                notes      TEXT DEFAULT '',
                UNIQUE(session_id, member_id)
            )
        """,
        "columns": [
            ("session_id", "INTEGER"),
            ("member_id",  "INTEGER"),
            ("status",     "TEXT DEFAULT 'pending'"),
            ("notes",      "TEXT DEFAULT ''"),
        ],
    },

    "cohort_checkin_configs": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohort_checkin_configs (
                cohort_id    INTEGER PRIMARY KEY,
                question     TEXT DEFAULT '',
                interval_h   INTEGER DEFAULT 24,
                enabled      INTEGER DEFAULT 1,
                last_sent_at TEXT
            )
        """,
        "columns": [
            ("question",     "TEXT DEFAULT ''"),
            ("interval_h",   "INTEGER DEFAULT 24"),
            ("enabled",      "INTEGER DEFAULT 1"),
            ("last_sent_at", "TEXT"),
        ],
    },

    "cohort_checkins": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohort_checkins (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id          INTEGER NOT NULL,
                member_telegram_id INTEGER NOT NULL,
                score              INTEGER,
                question_text      TEXT DEFAULT '',
                answered_at        TEXT
            )
        """,
        "columns": [
            ("cohort_id",          "INTEGER"),
            ("member_telegram_id", "INTEGER"),
            ("score",              "INTEGER"),
            ("question_text",      "TEXT DEFAULT ''"),
            ("answered_at",        "TEXT"),
        ],
    },

    "cohort_session_notes": {
        "create": """
            CREATE TABLE IF NOT EXISTS cohort_session_notes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      INTEGER NOT NULL,
                psychologist_id INTEGER NOT NULL,
                note_type       TEXT DEFAULT 'general',
                text            TEXT DEFAULT '',
                created_at      TEXT
            )
        """,
        "columns": [
            ("session_id",      "INTEGER"),
            ("psychologist_id", "INTEGER"),
            ("note_type",       "TEXT DEFAULT 'general'"),
            ("text",            "TEXT DEFAULT ''"),
            ("created_at",      "TEXT"),
        ],
    },

    "supervision_cases": {
        "create": """
            CREATE TABLE IF NOT EXISTS supervision_cases (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id  INTEGER NOT NULL,
                client_alias     TEXT NOT NULL,
                presenting_issue TEXT DEFAULT '',
                hypothesis       TEXT DEFAULT '',
                intervention     TEXT DEFAULT '',
                outcome          TEXT DEFAULT '',
                status           TEXT DEFAULT 'open',
                created_at       TEXT,
                updated_at       TEXT
            )
        """,
        "columns": [
            ("psychologist_id",  "INTEGER"),
            ("client_alias",     "TEXT"),
            ("presenting_issue", "TEXT DEFAULT ''"),
            ("hypothesis",       "TEXT DEFAULT ''"),
            ("intervention",     "TEXT DEFAULT ''"),
            ("outcome",          "TEXT DEFAULT ''"),
            ("status",           "TEXT DEFAULT 'open'"),
            ("created_at",       "TEXT"),
            ("updated_at",       "TEXT"),
        ],
    },

    "user_consents": {
        "create": """
            CREATE TABLE IF NOT EXISTS user_consents (
                user_id     INTEGER PRIMARY KEY,
                accepted_at TEXT NOT NULL,
                version     TEXT NOT NULL DEFAULT '1.0'
            )
        """,
        "columns": [
            ("accepted_at", "TEXT"),
            ("version",     "TEXT DEFAULT '1.0'"),
        ],
    },

    "user_plans": {
        "create": """
            CREATE TABLE IF NOT EXISTS user_plans (
                user_id    INTEGER PRIMARY KEY,
                plan       TEXT NOT NULL DEFAULT 'start',
                expires_at TEXT,
                updated_at TEXT NOT NULL
            )
        """,
        "columns": [
            ("plan",       "TEXT DEFAULT 'start'"),
            ("expires_at", "TEXT"),
            ("updated_at", "TEXT"),
        ],
    },

    "promo_codes": {
        "create": """
            CREATE TABLE IF NOT EXISTS promo_codes (
                code          TEXT PRIMARY KEY,
                plan          TEXT NOT NULL,
                duration_days INTEGER,
                max_uses      INTEGER,
                used_count    INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL
            )
        """,
        "columns": [
            ("plan",          "TEXT"),
            ("duration_days", "INTEGER"),
            ("max_uses",      "INTEGER"),
            ("used_count",    "INTEGER DEFAULT 0"),
            ("created_at",    "TEXT"),
        ],
    },

    "admin_actions_log": {
        "create": """
            CREATE TABLE IF NOT EXISTS admin_actions_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type    TEXT NOT NULL,
                details        TEXT,
                created_at_utc TEXT NOT NULL
            )
        """,
        "columns": [
            ("action_type",    "TEXT"),
            ("details",        "TEXT"),
            ("created_at_utc", "TEXT"),
        ],
    },

    "booking_profile": {
        "create": """
            CREATE TABLE IF NOT EXISTS booking_profile (
                psych_id        INTEGER PRIMARY KEY,
                slug            TEXT UNIQUE NOT NULL,
                display_name    TEXT,
                bio             TEXT,
                timezone        TEXT NOT NULL DEFAULT 'UTC',
                booking_enabled INTEGER DEFAULT 0,
                created_at      TEXT
            )
        """,
        "columns": [
            ("slug",            "TEXT"),
            ("display_name",    "TEXT"),
            ("bio",             "TEXT"),
            ("timezone",        "TEXT DEFAULT 'UTC'"),
            ("booking_enabled", "INTEGER DEFAULT 0"),
            ("created_at",      "TEXT"),
        ],
    },

    "availability_rules": {
        "create": """
            CREATE TABLE IF NOT EXISTS availability_rules (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                psych_id             INTEGER NOT NULL,
                weekday              INTEGER NOT NULL,
                start_time           TEXT NOT NULL,
                end_time             TEXT NOT NULL,
                session_duration_min INTEGER NOT NULL,
                buffer_min           INTEGER DEFAULT 0
            )
        """,
        "columns": [
            ("psych_id",             "INTEGER"),
            ("weekday",              "INTEGER"),
            ("start_time",           "TEXT"),
            ("end_time",             "TEXT"),
            ("session_duration_min", "INTEGER"),
            ("buffer_min",           "INTEGER DEFAULT 0"),
        ],
    },

    "availability_exceptions": {
        "create": """
            CREATE TABLE IF NOT EXISTS availability_exceptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                psych_id   INTEGER NOT NULL,
                date       TEXT NOT NULL,
                start_time TEXT,
                end_time   TEXT,
                type       TEXT NOT NULL DEFAULT 'blocked'
            )
        """,
        "columns": [
            ("psych_id",   "INTEGER"),
            ("date",       "TEXT"),
            ("start_time", "TEXT"),
            ("end_time",   "TEXT"),
            ("type",       "TEXT DEFAULT 'blocked'"),
        ],
    },

    "booking_requests_log": {
        "create": """
            CREATE TABLE IF NOT EXISTS booking_requests_log (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                client_telegram_id INTEGER NOT NULL,
                psych_id           INTEGER NOT NULL,
                requested_at_utc   TEXT NOT NULL
            )
        """,
        "columns": [
            ("client_telegram_id", "INTEGER"),
            ("psych_id",           "INTEGER"),
            ("requested_at_utc",   "TEXT"),
        ],
    },
}


# ── Core function ────────────────────────────────────────────────────────────

def ensure_db_schema(conn: sqlite3.Connection) -> None:
    """Bring the database schema up to date without touching existing data.

    - Creates any table that does not exist yet.
    - Adds any column that is missing from an existing table.
    - Never drops tables, drops columns, or modifies existing rows.
    - Protected by an in-memory flag so it runs at most once per process.

    Call this synchronously before asyncio.run(main()).
    """
    global _schema_applied
    if _schema_applied:
        log.debug("db_guard: schema already applied this session — skipping")
        return

    cur = conn.cursor()
    any_change = False

    # Fetch all existing table names once
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cur.fetchall()}

    for table, spec in DB_SCHEMA.items():
        if table not in existing_tables:
            # Table is completely missing — create it
            conn.execute(spec["create"])
            conn.commit()
            log.info("db_guard: Created table: %s", table)
            any_change = True
        else:
            # Table exists — check for missing columns
            cur.execute(f"PRAGMA table_info({table})")
            existing_cols = {row[1] for row in cur.fetchall()}

            for col_name, col_def in spec["columns"]:
                if col_name not in existing_cols:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"
                    )
                    conn.commit()
                    log.info("db_guard: Added column: %s to table %s", col_name, table)
                    any_change = True

    if any_change:
        log.info("db_guard: DB OK — schema updated")
    else:
        log.info("db_guard: DB OK — schema already up to date")

    _schema_applied = True


# ── Retry helper ─────────────────────────────────────────────────────────────

def db_execute(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple = (),
) -> sqlite3.Cursor:
    """Execute a SQL statement with one automatic retry on OperationalError.

    Scope: synchronous sqlite3 connections only — i.e. the startup guard
    path in main.py, or any future sync utility scripts. The bot's runtime
    uses aiosqlite (async), so those paths cannot call this helper directly.

    If sqlite3.OperationalError is raised (e.g. "no such column"), the
    function calls ensure_db_schema() to heal the schema, then retries
    the original statement once. This protects against schema drift on
    UserLAnd where the process may be killed between upgrades.

    Example (sync startup utility or one-off script):
        conn = sqlite3.connect(DB_PATH)
        cur = db_execute(conn, "SELECT foo FROM bar WHERE id = ?", (42,))
        rows = cur.fetchall()
        conn.close()
    """
    try:
        return conn.execute(sql, params)
    except sqlite3.OperationalError as exc:
        log.warning(
            "db_guard: OperationalError ('%s') — running ensure_db_schema and retrying",
            exc,
        )
        # Reset the lock so ensure_db_schema will run again
        global _schema_applied
        _schema_applied = False
        ensure_db_schema(conn)
        # Retry exactly once — let any second error propagate naturally
        return conn.execute(sql, params)
