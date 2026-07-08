"""Core repository for the psychologist profile / users domain.

All raw SQL for the ``psychologists`` table lives here.
Business logic (timezone confirmation prompt, registration events) stays in
``core/services/users.py``.
"""

from datetime import datetime

import aiosqlite

from core.db.base import DB_PATH


# ── Registration ─────────────────────────────────────────────────────────────

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
                (user_id, username, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            )
            await db.commit()
            return True
        return False


# ── Language ──────────────────────────────────────────────────────────────────

async def get_user_lang(user_id: int) -> str:
    """Return the psychologist's language preference (``'en'`` or ``'ru'``)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM psychologists WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return (row[0] or "en") if row else "en"


async def set_user_lang(user_id: int, lang: str) -> None:
    """Persist psychologist's language choice."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE psychologists SET language = ? WHERE user_id = ?",
            (lang, user_id),
        )
        await db.commit()


# ── Timezone ──────────────────────────────────────────────────────────────────

async def get_user_timezone(user_id: int) -> tuple[str, int]:
    """Return ``(timezone_name, utc_offset_minutes)`` for a psychologist.

    Falls back to ``("UTC", 0)`` when no row exists.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, utc_offset FROM psychologists WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
    if row:
        return (row[0] or "UTC", row[1] or 0)
    return ("UTC", 0)


async def set_user_timezone(
    user_id: int, tz_name: str, utc_offset_minutes: int
) -> None:
    """Persist psychologist's timezone and mark it as explicitly confirmed."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE psychologists SET timezone = ?, utc_offset = ?, tz_confirmed = 1"
            " WHERE user_id = ?",
            (tz_name, utc_offset_minutes, user_id),
        )
        await db.commit()


async def needs_tz_confirm(user_id: int) -> bool:
    """Return True if the psychologist still uses the default UTC without confirmation.

    Triggers the one-time 'please set your timezone' prompt in the main menu.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, tz_confirmed FROM psychologists WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
    if not row:
        return False
    tz, confirmed = row
    return (not tz or tz == "UTC") and not confirmed
