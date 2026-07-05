import aiosqlite

from core.db.base import DB_PATH


# ── Insert ───────────────────────────────────────────────────────────────

async def insert_session(psych_id: int, client_name: str, utc_dt_str: str):
    """Insert a plain one-off session (no topic/link/recurring)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (psychologist_id, client_name, scheduled_at) VALUES (?, ?, ?)",
            (psych_id, client_name, utc_dt_str)
        )
        await db.commit()


async def insert_oneoff_session(psych_id: int, client_name: str, scheduled_at: str,
                                 topic: str, link: str):
    """Insert a one-off session with topic/link (client-card flow, recurring-template
    occurrence generation)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions "
            "(psychologist_id, client_name, scheduled_at, topic, link) "
            "VALUES (?, ?, ?, ?, ?)",
            (psych_id, client_name, scheduled_at, topic, link))
        await db.commit()


async def insert_recurring_session(psych_id: int, client_name: str, utc_template: str,
                                    topic: str, link: str, days_csv: str):
    """Insert the recurring rule row itself (recurring=1, days_of_week=days_csv)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions "
            "(psychologist_id, client_name, scheduled_at, topic, link, recurring, days_of_week) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (psych_id, client_name, utc_template, topic, link, days_csv))
        await db.commit()


async def insert_pending_booking_session(psych_id: int, client_name: str, utc_str: str,
                                          topic: str) -> int:
    """Insert a client self-booking request (booking_status='pending_psych').
    Returns the new session id. May raise on UNIQUE constraint violation
    (slot already taken) — caller handles that."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO sessions "
            "(psychologist_id, client_name, scheduled_at, topic, booking_status) "
            "VALUES (?, ?, ?, ?, 'pending_psych')",
            (psych_id, client_name, utc_str, topic))
        session_id = cur.lastrowid
        await db.commit()
        return session_id


# ── Read ─────────────────────────────────────────────────────────────────

async def get_upcoming_sessions(psych_id: int, now: str):
    """Return (id, client_name, scheduled_at) for sessions at/after `now`, ordered by time."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, client_name, scheduled_at FROM sessions "
            "WHERE psychologist_id = ? AND scheduled_at >= ? ORDER BY scheduled_at",
            (psych_id, now)
        )
        return await cur.fetchall()


async def get_session_card(session_id: int, psych_id: int):
    """Return (client_name, scheduled_at, booking_status, proposed_start_datetime_utc)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at, booking_status, proposed_start_datetime_utc "
            "FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, psych_id)
        )
        return await cur.fetchone()


async def get_session_client_and_time(session_id: int, psych_id: int):
    """Return (client_name, scheduled_at) for a session owned by psych_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, psych_id)
        )
        return await cur.fetchone()


async def get_session_for_reschedule_confirm(session_id: int):
    """Return (psychologist_id, client_name, scheduled_at, proposed_start_datetime_utc,
    booking_status) — no psych_id filter (client-side callback)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT psychologist_id, client_name, scheduled_at, "
            "proposed_start_datetime_utc, booking_status FROM sessions WHERE id = ?",
            (session_id,))
        return await cur.fetchone()


async def get_session_psych_and_client(session_id: int):
    """Return (psychologist_id, client_name) — no psych_id filter (client-side callback)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT psychologist_id, client_name FROM sessions WHERE id = ?",
            (session_id,))
        return await cur.fetchone()


async def get_sessions_for_client(psych_id: int, client_name: str, now_str: str):
    """Return (id, scheduled_at, topic, link, recurring, days_of_week) rows: all recurring
    rules plus upcoming one-off sessions, ordered recurring-first then by time."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, scheduled_at, topic, link, recurring, days_of_week "
            "FROM sessions "
            "WHERE psychologist_id = ? AND client_name = ? "
            "AND (recurring = 1 OR scheduled_at >= ?) "
            "ORDER BY recurring DESC, scheduled_at ASC",
            (psych_id, client_name, now_str))
        return await cur.fetchall()


async def get_session_full(session_id: int):
    """Return (id, psychologist_id, client_name, scheduled_at, topic, link, recurring,
    days_of_week) — no psych_id filter."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, psychologist_id, client_name, scheduled_at, "
            "topic, link, recurring, days_of_week "
            "FROM sessions WHERE id = ?",
            (session_id,))
        return await cur.fetchone()


async def session_exists_at(psych_id: int, client_name: str, utc_str: str) -> bool:
    """Check whether a non-recurring session already exists at this exact UTC slot."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM sessions WHERE psychologist_id = ? "
            "AND client_name = ? AND scheduled_at = ? AND recurring = 0",
            (psych_id, client_name, utc_str))
        return (await cur.fetchone()) is not None


async def get_booked_slots_raw(psych_id: int) -> set[str]:
    """Return UTC slot strings that are taken (confirmed or pending psych approval,
    or NULL booking_status). Declined/deleted sessions are excluded."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT scheduled_at FROM sessions WHERE psychologist_id = ? "
            "AND (booking_status IN ('confirmed', 'pending_psych') OR booking_status IS NULL)",
            (psych_id,))
        return {row[0] for row in await cur.fetchall()}


async def get_session_for_booking_decision(session_id: int, psych_id: int):
    """Return (client_name, scheduled_at, booking_status) for a psych's approve/reject flow."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at, booking_status FROM sessions "
            "WHERE id = ? AND psychologist_id = ?",
            (session_id, psych_id))
        return await cur.fetchone()


async def get_next_session(psych_id: int, client_name: str, now_dt: str):
    """Return (scheduled_at,) for the next upcoming session, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT scheduled_at FROM sessions "
            "WHERE psychologist_id = ? AND client_name = ? AND scheduled_at >= ? "
            "ORDER BY scheduled_at LIMIT 1",
            (psych_id, client_name, now_dt)
        )
        return await cur.fetchone()


async def get_all_session_times(psych_id: int, client_name: str):
    """Return (scheduled_at,) rows for all sessions of a client, no ordering."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT scheduled_at FROM sessions WHERE psychologist_id = ? AND client_name = ?",
            (psych_id, client_name))
        return await cur.fetchall()


async def get_sessions_for_export(psych_id: int, client_name: str):
    """Return (scheduled_at, link) rows ordered by time, for CSV/TXT export."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT scheduled_at, link FROM sessions "
            "WHERE psychologist_id = ? AND client_name = ? ORDER BY scheduled_at",
            (psych_id, client_name))
        return await cur.fetchall()


async def get_last_session_time(psych_id: int, client_name: str):
    """Return MAX(scheduled_at) for a client, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT MAX(scheduled_at) FROM sessions WHERE psychologist_id = ? AND client_name = ?",
            (psych_id, client_name))
        return (await cur.fetchone())[0]


async def count_sessions_for_psych(psych_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM sessions WHERE psychologist_id = ?", (psych_id,))
        return (await cur.fetchone())[0]


async def count_sessions_in_range(start: str, end: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM sessions WHERE scheduled_at >= ? AND scheduled_at < ?",
            (start, end))
        return (await cur.fetchone())[0]


async def count_sessions_since(since: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM sessions WHERE scheduled_at >= ?", (since,))
        return (await cur.fetchone())[0]


async def count_all_sessions() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM sessions")
        return (await cur.fetchone())[0]


# ── Update ───────────────────────────────────────────────────────────────

async def update_session_datetime(session_id: int, utc_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET scheduled_at = ? WHERE id = ?",
                         (utc_str, session_id))
        await db.commit()


async def update_session_topic(session_id: int, topic: str):
    """Pass topic='' to clear."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET topic = ? WHERE id = ?", (topic, session_id))
        await db.commit()


async def update_session_link(session_id: int, link: str):
    """Pass link='' to clear."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET link = ? WHERE id = ?", (link, session_id))
        await db.commit()


async def propose_reschedule(session_id: int, utc_dt_str: str):
    """Write a proposed new time without moving scheduled_at yet; awaits client confirm."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET proposed_start_datetime_utc = ?, "
            "booking_status = 'pending_client' WHERE id = ?",
            (utc_dt_str, session_id)
        )
        await db.commit()


async def confirm_reschedule(session_id: int, proposed_utc: str):
    """Commit the proposed time: move proposed -> scheduled_at, reset reminder flags."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET scheduled_at = ?, proposed_start_datetime_utc = NULL, "
            "booking_status = 'confirmed', reminded_24h = 0, reminded_1h = 0 WHERE id = ?",
            (proposed_utc, session_id))
        await db.commit()


async def confirm_booking(session_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET booking_status = 'confirmed' WHERE id = ?",
            (session_id,))
        await db.commit()


# ── Delete ───────────────────────────────────────────────────────────────

async def delete_session(session_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()


async def delete_recurring_sessions_for_client(psych_id: int, client_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM sessions WHERE psychologist_id = ? AND client_name = ? AND recurring = 1",
            (psych_id, client_name))
        await db.commit()


# ── Reminder helpers ─────────────────────────────────────────────────────

async def get_sessions_pending_reminders() -> list:
    """Return sessions still needing a reminder (reminded_1h = 0, booking confirmed or legacy NULL).

    Columns: (id, psychologist_id, client_name, scheduled_at,
               link, reminded_24h, reminded_1h, client_telegram_id).
    client_telegram_id is NULL when the client has not connected via Telegram.
    Only non-recurring one-off sessions and upcoming instances are returned;
    recurring template rows (recurring=1) have reminded_1h=0 forever and are
    excluded implicitly because they never fall inside the reminder windows.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT s.id, s.psychologist_id, s.client_name, s.scheduled_at, "
            "s.link, s.reminded_24h, s.reminded_1h, c.telegram_id "
            "FROM sessions s "
            "LEFT JOIN clients c ON c.psychologist_id = s.psychologist_id "
            "  AND c.name = s.client_name "
            "WHERE s.reminded_1h = 0 "
            "AND (s.booking_status = 'confirmed' OR s.booking_status IS NULL)"
        )
        return await cur.fetchall()


async def mark_reminded_24h(session_id: int) -> None:
    """Set reminded_24h = 1.  Called after both psych and client send attempts."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET reminded_24h = 1 WHERE id = ?", (session_id,))
        await db.commit()


async def mark_reminded_1h(session_id: int) -> None:
    """Set reminded_1h = 1.  Called after both psych and client send attempts."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET reminded_1h = 1 WHERE id = ?", (session_id,))
        await db.commit()
