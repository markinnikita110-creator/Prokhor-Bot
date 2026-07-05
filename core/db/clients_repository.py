import aiosqlite

from core.db.base import DB_PATH
from core.utils.time import now_str


def _make_token() -> str:
    import secrets
    return "client_" + secrets.token_hex(4)


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


async def set_client_timezone(telegram_id: int, tz_name: str, utc_offset_minutes: int):
    """Persist connected client's timezone and mark it as explicitly confirmed."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET timezone = ?, utc_offset = ?, tz_confirmed = 1"
            " WHERE telegram_id = ?",
            (tz_name, utc_offset_minutes, telegram_id)
        )
        await db.commit()


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


async def get_client_lang(telegram_id: int) -> str:
    """Return the connected client's language preference."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
    return (row[0] or "en") if row else "en"


async def set_client_lang(telegram_id: int, lang: str):
    """Persist connected client's language choice."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET language = ? WHERE telegram_id = ?", (lang, telegram_id)
        )
        await db.commit()


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
