import logging
import re as _re
import secrets
from datetime import datetime, timedelta, timezone as _tz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiosqlite

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


def now_str() -> str:
    """Current LOCAL time string — used only for display-only created_at fields."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def now_utc() -> str:
    """Current UTC time string — used for all scheduling and reminder comparisons."""
    return datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M")


# ── Timezone helpers ───────────────────────────────────────────────────────

def local_to_utc(dt_str: str, utc_offset_minutes: int) -> str:
    """Convert 'YYYY-MM-DD HH:MM' in user's local time to UTC for storage."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(minutes=utc_offset_minutes)
    return utc_dt.strftime("%Y-%m-%d %H:%M")


def utc_to_local(dt_str: str, utc_offset_minutes: int) -> str:
    """Convert 'YYYY-MM-DD HH:MM' UTC stored value to user's local time for display."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    local_dt = dt + timedelta(minutes=utc_offset_minutes)
    return local_dt.strftime("%Y-%m-%d %H:%M")


def format_offset(utc_offset_minutes: int) -> str:
    """Format offset integer as 'UTC+3' or 'UTC-5:30'."""
    sign = "+" if utc_offset_minutes >= 0 else "-"
    total = abs(utc_offset_minutes)
    hours, mins = divmod(total, 60)
    if mins:
        return f"UTC{sign}{hours}:{mins:02d}"
    return f"UTC{sign}{hours}"


def to_user_tz(
    utc_dt_str: str,
    tz_name: str | None,
    fmt: str = "%d.%m.%Y %H:%M",
    *,
    user_id: int | None = None,
) -> str:
    """Convert a UTC datetime string (as stored in DB) to the user's local time.

    utc_dt_str — "YYYY-MM-DD HH:MM" in UTC, as stored everywhere in the DB.
    tz_name    — IANA name ("Europe/Moscow") from psychologists.timezone or
                 clients.timezone.  Legacy "UTC+3" offset strings are handled
                 via a regex fallback so existing records keep working without
                 a forced data migration.
    fmt        — strftime format; default matches app-wide display standard.
    user_id    — optional; included in the warning log when conversion fails.

    Never raises: on any parse failure returns utc_dt_str unchanged.
    When timezone cannot be resolved the returned string is suffixed with
    \" ⚠️ (UTC)\" so the user sees an explicit indication rather than silently
    wrong local time, and a WARNING is emitted to the log.
    """
    try:
        dt_utc = datetime.strptime(utc_dt_str, "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("UTC")
        )
    except (ValueError, Exception):
        return utc_dt_str  # unparseable — return as-is

    # Defensive guard: caller accidentally passed an integer offset instead of a
    # string (e.g. old utc_offset column value). Convert on the fly so the
    # function never raises TypeError.
    if isinstance(tz_name, int):
        return (dt_utc + timedelta(minutes=tz_name)).strftime(fmt)

    tz = tz_name or ""

    # 1. Proper IANA name ("UTC", "Europe/Moscow", "Asia/Kolkata", …)
    if tz:
        try:
            return dt_utc.astimezone(ZoneInfo(tz)).strftime(fmt)
        except (ZoneInfoNotFoundError, KeyError):
            pass

        # 2. Legacy "UTC+3" / "UTC+5:30" strings saved by old preset buttons
        m = _re.match(r"^UTC([+-])(\d{1,2})(?::(\d{2}))?$", tz)
        if m:
            sign = 1 if m.group(1) == "+" else -1
            hours = int(m.group(2))
            mins = int(m.group(3) or 0)
            offset_min = sign * (hours * 60 + mins)
            return (dt_utc + timedelta(minutes=offset_min)).strftime(fmt)

    # 3. Timezone missing or unrecognised — show UTC with an explicit warning.
    #    Do NOT silently guess Moscow time: the user sees the wrong time with no
    #    indication, which is worse than an honest "this is UTC, please fix it".
    _log.warning(
        "to_user_tz: cannot resolve timezone %r (user_id=%s) — displaying UTC. "
        "User should update their timezone setting.",
        tz_name, user_id if user_id is not None else "unknown",
    )
    return dt_utc.strftime(fmt) + " ⚠️ (UTC)"


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


async def ensure_user(user_id: int, username: str = "") -> bool:
    """Register psychologist if not already known.

    Returns True if the user was newly created, False if they already existed.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM psychologists WHERE user_id = ?", (user_id,)
        )
        already_exists = await cur.fetchone()
        if not already_exists:
            await db.execute(
                "INSERT INTO psychologists (user_id, username, created_at) VALUES (?, ?, ?)",
                (user_id, username, now_str())
            )
            await db.commit()
            return True   # freshly registered
        return False      # already known


async def resolve_client(psychologist_id: int, name: str, create: bool = True):
    """Return client_id. Optionally auto-create the client."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM clients WHERE psychologist_id = ? AND name = ?",
            (psychologist_id, name)
        )
        row = await cur.fetchone()
        if row:
            return row[0]
        if create:
            cur = await db.execute(
                "INSERT INTO clients (psychologist_id, name, created_at, invite_token) VALUES (?, ?, ?, ?)",
                (psychologist_id, name, now_str(), _make_token())
            )
            await db.commit()
            return cur.lastrowid
        return None


async def find_connected_client(telegram_id: int):
    """Return (client_id, name, psychologist_id) if this Telegram user is a connected client."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name, psychologist_id FROM clients WHERE telegram_id = ?",
            (telegram_id,)
        )
        return await cur.fetchone()


async def get_user_roles(user_id: int) -> tuple:
    """Return (is_psychologist, client_row) — both can be truthy at the same time.

    is_psychologist : truthy row if user is registered in psychologists table.
    client_row      : (id, name, psychologist_id) if user has a connected client record,
                      None otherwise.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM psychologists WHERE user_id = ?", (user_id,)
        )
        is_psych = await cur.fetchone()
        cur = await db.execute(
            "SELECT id, name, psychologist_id FROM clients WHERE telegram_id = ?",
            (user_id,)
        )
        client = await cur.fetchone()
    return is_psych, client


async def reset_client_role(telegram_id: int) -> bool:
    """Disconnect this Telegram user from their client record.

    Sets telegram_id = NULL on the client row so the psychologist's
    client data (notes, sessions, homework) is preserved.
    Returns True if a row was affected, False if the user had no client role.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        if not row:
            return False
        await db.execute(
            "UPDATE clients SET telegram_id = NULL WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()
    return True


async def get_user_timezone(user_id: int) -> tuple[str, int]:
    """Return (timezone_name, utc_offset_minutes) for a psychologist."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, utc_offset FROM psychologists WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    if row:
        return (row[0] or "UTC", row[1] or 0)
    return ("UTC", 0)


async def get_client_timezone(telegram_id: int) -> tuple[str, int]:
    """Return (timezone_name, utc_offset_minutes) for a connected client."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, utc_offset FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
    if row:
        return (row[0] or "UTC", row[1] or 0)
    return ("UTC", 0)


async def set_user_timezone(user_id: int, tz_name: str, utc_offset_minutes: int):
    """Persist psychologist's timezone and mark it as explicitly confirmed."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE psychologists SET timezone = ?, utc_offset = ?, tz_confirmed = 1"
            " WHERE user_id = ?",
            (tz_name, utc_offset_minutes, user_id)
        )
        await db.commit()


async def set_client_timezone(telegram_id: int, tz_name: str, utc_offset_minutes: int):
    """Persist connected client's timezone and mark it as explicitly confirmed."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET timezone = ?, utc_offset = ?, tz_confirmed = 1"
            " WHERE telegram_id = ?",
            (tz_name, utc_offset_minutes, telegram_id)
        )
        await db.commit()


async def needs_tz_confirm(user_id: int) -> bool:
    """Return True if the psychologist still uses the default UTC and hasn't confirmed it.

    Triggers the one-time 'please set your timezone' prompt in the main menu.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, tz_confirmed FROM psychologists WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    if not row:
        return False
    tz, confirmed = row
    return (not tz or tz == "UTC") and not confirmed


async def needs_tz_confirm_client(telegram_id: int) -> bool:
    """Return True if the client still uses the default UTC and hasn't confirmed it."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, tz_confirmed FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
    if not row:
        return False
    tz, confirmed = row
    return (not tz or tz == "UTC") and not confirmed


async def get_user_lang(user_id: int) -> str:
    """Return the psychologist's language preference ('en' or 'ru')."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM psychologists WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return (row[0] or "en") if row else "en"


async def get_client_lang(telegram_id: int) -> str:
    """Return the connected client's language preference."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
    return (row[0] or "en") if row else "en"


async def set_user_lang(user_id: int, lang: str):
    """Persist psychologist's language choice."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE psychologists SET language = ? WHERE user_id = ?", (lang, user_id)
        )
        await db.commit()


async def set_client_lang(telegram_id: int, lang: str):
    """Persist connected client's language choice."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET language = ? WHERE telegram_id = ?", (lang, telegram_id)
        )
        await db.commit()


def make_token() -> str:
    return _make_token()


async def get_cohort_member_lang(telegram_id: int) -> str:
    """COHORT_SESSION: Language for a cohort member — checks clients then psychologists."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        if row and row[0]:
            return row[0]
        cur = await db.execute(
            "SELECT language FROM psychologists WHERE user_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        if row and row[0]:
            return row[0]
    return "en"


async def get_cohort_member_timezone(telegram_id: int) -> tuple[str, int]:
    """COHORT_SESSION: Timezone for any user — checks clients then psychologists, falls back to UTC."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, utc_offset FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        if row and row[1] is not None:
            return (row[0] or "UTC", row[1])
        cur = await db.execute(
            "SELECT timezone, utc_offset FROM psychologists WHERE user_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
        if row and row[1] is not None:
            return (row[0] or "UTC", row[1])
    return ("UTC", 0)
