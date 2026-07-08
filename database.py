import logging
import secrets

import aiosqlite

from core.utils.time import (  # noqa: F401 — re-exported for backward compatibility
    format_offset,
    local_to_utc,
    now_str,
    now_utc,
    to_user_tz,
    utc_to_local,
)
from core.db.clients_repository import (  # noqa: F401 — re-exported for backward compatibility
    find_connected_client,
    get_client_lang,
    get_client_timezone,
    get_cohort_member_lang,
    get_cohort_member_timezone,
    get_user_roles,
    needs_tz_confirm_client,
    reset_client_role,
    resolve_client,
    set_client_lang,
    set_client_timezone,
)

_log = logging.getLogger(__name__)

# ── Timezone: integer offset (minutes) → canonical IANA zone name ─────────
# Used when a user selects a preset button so we store a proper IANA
# identifier rather than a synthetic "UTC+3" string.
OFFSET_TO_IANA: dict[int, str] = {
    -600: "Pacific/Honolulu",
    -540: "America/Anchorage",
    -480: "America/Los_Angeles",
    -420: "America/Denver",
    -360: "America/Chicago",
    -300: "America/New_York",
    -240: "America/Halifax",
    -180: "America/Sao_Paulo",
    -120: "Atlantic/South_Georgia",
     -60: "Atlantic/Azores",
       0: "UTC",
      60: "Europe/London",
     120: "Europe/Kaliningrad",
     180: "Europe/Moscow",
     240: "Europe/Samara",
     300: "Asia/Yekaterinburg",
     330: "Asia/Kolkata",
     360: "Asia/Omsk",
     420: "Asia/Krasnoyarsk",
     480: "Asia/Irkutsk",
     540: "Asia/Yakutsk",
     600: "Asia/Vladivostok",
     660: "Asia/Magadan",
     720: "Asia/Kamchatka",
}

_FALLBACK_TZ = "Europe/Moscow"

DB_PATH = "prokhor.db"


def _make_token() -> str:
    return "client_" + secrets.token_hex(4)


async def init_db():
    """Create all tables on first run."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for crash-safety on mobile/UserLAnd where the process
        # can be killed by the OS at any moment without a clean shutdown.
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.executescript("""
            -- FSM storage: persists aiogram FSM state/data across process restarts
            CREATE TABLE IF NOT EXISTS fsm_storage (
                key   TEXT PRIMARY KEY,
                state TEXT,
                data  TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS psychologists (
                user_id        INTEGER PRIMARY KEY,
                username       TEXT,
                language       TEXT DEFAULT 'en',
                created_at     TEXT,
                timezone       TEXT DEFAULT 'UTC',
                utc_offset     INTEGER DEFAULT 0,
                tz_confirmed   INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS clients (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                name            TEXT,
                created_at      TEXT,
                telegram_id     INTEGER,
                invite_token    TEXT,
                language        TEXT DEFAULT 'en',
                is_archived     INTEGER DEFAULT 0,
                timezone        TEXT DEFAULT 'UTC',
                utc_offset      INTEGER DEFAULT 0,
                tz_confirmed    INTEGER NOT NULL DEFAULT 0,
                UNIQUE(psychologist_id, name)
            );
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id  INTEGER,
                text       TEXT,
                note_type  TEXT DEFAULT 'plain',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS checkins (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                score     INTEGER,
                auto      INTEGER DEFAULT 0,
                timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                client_name     TEXT,
                time_minutes    INTEGER
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                client_name     TEXT,
                scheduled_at    TEXT,
                link            TEXT,
                reminded_24h    INTEGER DEFAULT 0,
                reminded_1h     INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS auto_checkins (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                client_name     TEXT,
                interval_min    INTEGER,
                last_sent       TEXT,
                UNIQUE(psychologist_id, client_name)
            );
            CREATE TABLE IF NOT EXISTS homeworks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id  INTEGER NOT NULL,
                text       TEXT NOT NULL,
                created_at TEXT,
                completed  INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS client_tags (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                tag       TEXT NOT NULL
            );

            -- COHORT: cohort groups created by psychologists
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
            );

            -- COHORT: participants who joined a cohort via invite link
            CREATE TABLE IF NOT EXISTS cohort_members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id   INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                name        TEXT,
                joined_at   TEXT,
                status      TEXT DEFAULT 'active',
                UNIQUE(cohort_id, telegram_id)
            );

            -- COHORT_SESSION: group sessions scheduled by psychologist
            -- recurring/days_of_week (RECURRING) power the weekly repeat generator
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
            );

            -- COHORT_SESSION: per-member attendance for each cohort session
            CREATE TABLE IF NOT EXISTS cohort_attendance (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                member_id  INTEGER NOT NULL,
                status     TEXT DEFAULT 'pending',
                notes      TEXT DEFAULT '',
                UNIQUE(session_id, member_id)
            );

            -- COHORT_V2: auto check-in configuration per cohort (one row per cohort)
            CREATE TABLE IF NOT EXISTS cohort_checkin_configs (
                cohort_id    INTEGER PRIMARY KEY,
                question     TEXT DEFAULT '',
                interval_h   INTEGER DEFAULT 24,
                enabled      INTEGER DEFAULT 1,
                last_sent_at TEXT
            );

            -- COHORT_V2: individual check-in responses from cohort members
            CREATE TABLE IF NOT EXISTS cohort_checkins (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id          INTEGER NOT NULL,
                member_telegram_id INTEGER NOT NULL,
                score              INTEGER,
                question_text      TEXT DEFAULT '',
                answered_at        TEXT
            );

            -- COHORT_V2: psychologist notes attached to a specific cohort session
            CREATE TABLE IF NOT EXISTS cohort_session_notes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      INTEGER NOT NULL,
                psychologist_id INTEGER NOT NULL,
                note_type       TEXT DEFAULT 'general',
                text            TEXT DEFAULT '',
                created_at      TEXT
            );

            -- COHORT_V2: supervision case logbook
            CREATE TABLE IF NOT EXISTS supervision_cases (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER NOT NULL,
                client_alias    TEXT NOT NULL,
                presenting_issue TEXT DEFAULT '',
                hypothesis      TEXT DEFAULT '',
                intervention    TEXT DEFAULT '',
                outcome         TEXT DEFAULT '',
                status          TEXT DEFAULT 'open',
                created_at      TEXT,
                updated_at      TEXT
            );

            -- LEGAL: consent records
            CREATE TABLE IF NOT EXISTS user_consents (
                user_id     INTEGER PRIMARY KEY,
                accepted_at TEXT NOT NULL,
                version     TEXT NOT NULL DEFAULT '1.0'
            );

            -- PLANS: user tariff plans
            CREATE TABLE IF NOT EXISTS user_plans (
                user_id     INTEGER PRIMARY KEY,
                plan        TEXT NOT NULL DEFAULT 'start',
                expires_at  TEXT,
                updated_at  TEXT NOT NULL
            );

            -- PLANS: promo codes
            CREATE TABLE IF NOT EXISTS promo_codes (
                code          TEXT PRIMARY KEY,
                plan          TEXT NOT NULL,
                duration_days INTEGER,
                max_uses      INTEGER,
                used_count    INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL
            );

            -- ADMIN: audit log for admin actions
            CREATE TABLE IF NOT EXISTS admin_actions_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type    TEXT NOT NULL,
                details        TEXT,
                created_at_utc TEXT NOT NULL
            );

            -- BOOKING: psychologist public booking profile
            CREATE TABLE IF NOT EXISTS booking_profile (
                psych_id        INTEGER PRIMARY KEY,
                slug            TEXT UNIQUE NOT NULL,
                display_name    TEXT,
                bio             TEXT,
                timezone        TEXT NOT NULL DEFAULT 'UTC',
                booking_enabled INTEGER DEFAULT 0,
                created_at      TEXT
            );

            -- BOOKING: weekly availability rules (one row per weekday per psych)
            CREATE TABLE IF NOT EXISTS availability_rules (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                psych_id             INTEGER NOT NULL,
                weekday              INTEGER NOT NULL,
                start_time           TEXT NOT NULL,
                end_time             TEXT NOT NULL,
                session_duration_min INTEGER NOT NULL,
                buffer_min           INTEGER DEFAULT 0
            );

            -- BOOKING: blocked date/time exceptions
            CREATE TABLE IF NOT EXISTS availability_exceptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                psych_id   INTEGER NOT NULL,
                date       TEXT NOT NULL,
                start_time TEXT,
                end_time   TEXT,
                type       TEXT NOT NULL DEFAULT 'blocked'
            );
        """)
        await db.commit()


async def migrate_db():
    """Safely add columns to existing databases without data loss."""
    async with aiosqlite.connect(DB_PATH) as db:
        # clients
        cur = await db.execute("PRAGMA table_info(clients)")
        client_cols = {row[1] for row in await cur.fetchall()}
        for col, definition in [
            ("telegram_id",  "INTEGER"),
            ("invite_token", "TEXT"),
            ("language",     "TEXT DEFAULT 'en'"),
            ("is_archived",  "INTEGER DEFAULT 0"),
            ("timezone",     "TEXT DEFAULT 'UTC'"),
            ("utc_offset",   "INTEGER DEFAULT 0"),
        ]:
            if col not in client_cols:
                await db.execute(f"ALTER TABLE clients ADD COLUMN {col} {definition}")

        # psychologists
        cur = await db.execute("PRAGMA table_info(psychologists)")
        psych_cols = {row[1] for row in await cur.fetchall()}
        for col, definition in [
            ("language",   "TEXT DEFAULT 'en'"),
            ("timezone",   "TEXT DEFAULT 'UTC'"),
            ("utc_offset", "INTEGER DEFAULT 0"),
        ]:
            if col not in psych_cols:
                await db.execute(f"ALTER TABLE psychologists ADD COLUMN {col} {definition}")

        # sessions
        cur = await db.execute("PRAGMA table_info(sessions)")
        session_cols = {row[1] for row in await cur.fetchall()}
        if "link" not in session_cols:
            await db.execute("ALTER TABLE sessions ADD COLUMN link TEXT")
        if "topic" not in session_cols:
            await db.execute("ALTER TABLE sessions ADD COLUMN topic TEXT DEFAULT ''")
        if "recurring" not in session_cols:
            await db.execute("ALTER TABLE sessions ADD COLUMN recurring INTEGER DEFAULT 0")
        if "days_of_week" not in session_cols:
            await db.execute("ALTER TABLE sessions ADD COLUMN days_of_week TEXT DEFAULT ''")
        if "booking_status" not in session_cols:
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN booking_status TEXT DEFAULT 'confirmed'"
            )
        if "proposed_start_datetime_utc" not in session_cols:
            await db.execute(
                "ALTER TABLE sessions ADD COLUMN proposed_start_datetime_utc TEXT"
            )

        # clients — recurring_paused for individual recurring sessions
        cur = await db.execute("PRAGMA table_info(clients)")
        client_cols2 = {row[1] for row in await cur.fetchall()}
        if "recurring_paused" not in client_cols2:
            await db.execute("ALTER TABLE clients ADD COLUMN recurring_paused INTEGER DEFAULT 0")

        # RECURRING: cohort_sessions — recurring weekly sessions
        cur = await db.execute("PRAGMA table_info(cohort_sessions)")
        cohort_session_cols = {row[1] for row in await cur.fetchall()}
        for col, definition in [
            ("recurring",    "INTEGER DEFAULT 0"),
            ("days_of_week", "TEXT DEFAULT ''"),
        ]:
            if col not in cohort_session_cols:
                await db.execute(f"ALTER TABLE cohort_sessions ADD COLUMN {col} {definition}")

        # RECURRING: cohorts — per-cohort pause switch for the recurrence rule
        cur = await db.execute("PRAGMA table_info(cohorts)")
        cohort_cols = {row[1] for row in await cur.fetchall()}
        if "recurring_paused" not in cohort_cols:
            await db.execute("ALTER TABLE cohorts ADD COLUMN recurring_paused INTEGER DEFAULT 0")

        # PLANS: user_plans table
        cur = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_plans'"
        )
        if not await cur.fetchone():
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_plans (
                    user_id     INTEGER PRIMARY KEY,
                    plan        TEXT NOT NULL DEFAULT 'start',
                    expires_at  TEXT,
                    updated_at  TEXT NOT NULL
                )
            """)

        # PLANS: promo_codes table
        cur = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='promo_codes'"
        )
        if not await cur.fetchone():
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    code          TEXT PRIMARY KEY,
                    plan          TEXT NOT NULL,
                    duration_days INTEGER,
                    max_uses      INTEGER,
                    used_count    INTEGER NOT NULL DEFAULT 0,
                    created_at    TEXT NOT NULL
                )
            """)

        # PROMO_CODES: remove spurious 'type' column added on some installs
        # (column was never part of the committed schema but exists on some
        # real devices; its NOT NULL constraint causes every INSERT to fail)
        cur = await db.execute("PRAGMA table_info(promo_codes)")
        promo_cols = {row[1] for row in await cur.fetchall()}
        if "type" in promo_cols:
            # 1. Snapshot existing rows to logs BEFORE touching anything
            cur = await db.execute("SELECT * FROM promo_codes")
            existing_promos = await cur.fetchall()
            log.info(
                "migrate_db: promo_codes snapshot before type-column removal "
                "(%d rows): %s", len(existing_promos), existing_promos
            )
            # 2. Remove any leftover temp table from a prior interrupted run
            await db.execute("DROP TABLE IF EXISTS promo_codes_new")
            await db.commit()  # flush before opening the explicit transaction
            # 3. Atomic recreation — BEGIN / COMMIT / ROLLBACK explicitly so
            #    SQLite guarantees the swap is all-or-nothing even on power loss
            try:
                await db.execute("BEGIN")
                await db.execute("""
                    CREATE TABLE promo_codes_new (
                        code          TEXT PRIMARY KEY,
                        plan          TEXT NOT NULL,
                        duration_days INTEGER,
                        max_uses      INTEGER,
                        used_count    INTEGER NOT NULL DEFAULT 0,
                        created_at    TEXT NOT NULL
                    )
                """)
                await db.execute("""
                    INSERT INTO promo_codes_new
                        (code, plan, duration_days, max_uses,
                         used_count, created_at)
                    SELECT code, plan, duration_days, max_uses,
                           used_count, created_at
                    FROM   promo_codes
                """)
                await db.execute("DROP TABLE promo_codes")
                await db.execute(
                    "ALTER TABLE promo_codes_new RENAME TO promo_codes"
                )
                await db.commit()
                log.info(
                    "migrate_db: promo_codes.type column removed successfully"
                )
            except Exception as exc:
                try:
                    await db.execute("ROLLBACK")
                except Exception:
                    pass
                log.error(
                    "migrate_db: promo_codes type-column removal FAILED — "
                    "rolled back, original table untouched: %s", exc
                )
                raise

        # ADMIN: audit log
        await db.execute(
            """CREATE TABLE IF NOT EXISTS admin_actions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                details TEXT,
                created_at_utc TEXT NOT NULL)"""
        )

        # BOOKING: new tables (safe for existing DBs)
        for tbl_sql in [
            """CREATE TABLE IF NOT EXISTS booking_profile (
                psych_id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL,
                display_name TEXT, bio TEXT, timezone TEXT NOT NULL DEFAULT 'UTC',
                booking_enabled INTEGER DEFAULT 0, created_at TEXT)""",
            """CREATE TABLE IF NOT EXISTS availability_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT, psych_id INTEGER NOT NULL,
                weekday INTEGER NOT NULL, start_time TEXT NOT NULL,
                end_time TEXT NOT NULL, session_duration_min INTEGER NOT NULL,
                buffer_min INTEGER DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS availability_exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, psych_id INTEGER NOT NULL,
                date TEXT NOT NULL, start_time TEXT, end_time TEXT,
                type TEXT NOT NULL DEFAULT 'blocked')""",
        ]:
            await db.execute(tbl_sql)

        # BOOKING: unique index on sessions to prevent double-booking
        try:
            await db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_psych_slot "
                "ON sessions(psychologist_id, scheduled_at)"
            )
        except Exception:
            pass  # skip if existing data has duplicates

        # BOOKING: rate-limit log (5 requests per client per 24h across all psychs)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS booking_requests_log (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                client_telegram_id INTEGER NOT NULL,
                psych_id           INTEGER NOT NULL,
                requested_at_utc   TEXT NOT NULL
            )
        """)

        await db.commit()


# ensure_user / get_user_lang / set_user_lang / get_user_timezone /
# set_user_timezone / needs_tz_confirm have moved to core.db.users_repository.


def make_token() -> str:
    return _make_token()
