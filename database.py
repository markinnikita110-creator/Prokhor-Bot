import secrets
from datetime import datetime, timedelta, timezone as _tz

import aiosqlite

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


async def init_db():
    """Create all tables on first run."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS psychologists (
                user_id        INTEGER PRIMARY KEY,
                username       TEXT,
                language       TEXT DEFAULT 'en',
                created_at     TEXT,
                timezone       TEXT DEFAULT 'UTC',
                utc_offset     INTEGER DEFAULT 0
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
                invite_token     TEXT UNIQUE
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
    """Persist psychologist's timezone."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE psychologists SET timezone = ?, utc_offset = ? WHERE user_id = ?",
            (tz_name, utc_offset_minutes, user_id)
        )
        await db.commit()


async def set_client_timezone(telegram_id: int, tz_name: str, utc_offset_minutes: int):
    """Persist connected client's timezone."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET timezone = ?, utc_offset = ? WHERE telegram_id = ?",
            (tz_name, utc_offset_minutes, telegram_id)
        )
        await db.commit()


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
