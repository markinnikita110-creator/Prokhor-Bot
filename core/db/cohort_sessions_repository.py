"""Cohort sessions repository — CRUD for cohort_sessions and cohort_attendance.

All owner-checks live in the callers (handlers or service layer).
The one exception is generate_recurring_cohort_sessions, which is a
system-level background job and has no caller-supplied uid.
"""

import logging
from datetime import datetime, timedelta

import aiosqlite

from core.db.base import DB_PATH

log = logging.getLogger(__name__)


# ── Cohort Sessions ───────────────────────────────────────────────────────────

async def create_cohort_session(
    cohort_id: int,
    session_number: int,
    scheduled_at_utc: str,
    topic: str,
    link: str,
    recurring: int = 0,
    days_of_week: str = "",
) -> int:
    """Insert a cohort session row; returns the new session id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cohort_sessions "
            "(cohort_id, session_number, scheduled_at, topic, link, status, recurring, days_of_week) "
            "VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?)",
            (cohort_id, session_number, scheduled_at_utc, topic, link, recurring, days_of_week),
        )
        session_id = cur.lastrowid
        await db.commit()
    return session_id


async def get_cohort_sessions(cohort_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic, link, status "
            "FROM cohort_sessions WHERE cohort_id = ? ORDER BY scheduled_at ASC",
            (cohort_id,),
        )
        return await cur.fetchall()


async def get_scheduled_sessions(cohort_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic "
            "FROM cohort_sessions "
            "WHERE cohort_id = ? AND status IN ('scheduled', 'completed') "
            "ORDER BY scheduled_at ASC",
            (cohort_id,),
        )
        return await cur.fetchall()


async def get_upcoming_sessions(cohort_id: int, days_ahead: int = 45) -> list:
    """Scheduled sessions for a cohort within the next `days_ahead` days."""
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    horizon_utc = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic, link, recurring, days_of_week "
            "FROM cohort_sessions "
            "WHERE cohort_id = ? AND status = 'scheduled' "
            "AND scheduled_at >= ? AND scheduled_at <= ? "
            "ORDER BY scheduled_at ASC",
            (cohort_id, now_utc, horizon_utc),
        )
        return await cur.fetchall()


async def get_session(session_id: int):
    """Full row for one session, or None if it no longer exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, cohort_id, session_number, scheduled_at, topic, link, status, "
            "recurring, days_of_week FROM cohort_sessions WHERE id = ?",
            (session_id,),
        )
        return await cur.fetchone()


async def get_cohort_for_session(session_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT cs.cohort_id, c.name, cs.session_number "
            "FROM cohort_sessions cs JOIN cohorts c ON c.id = cs.cohort_id "
            "WHERE cs.id = ?",
            (session_id,),
        )
        return await cur.fetchone()


async def update_session_field(session_id: int, field: str, value: str) -> None:
    """Update one editable column (scheduled_at/topic/link) of a session."""
    if field not in ("scheduled_at", "topic", "link"):
        raise ValueError(f"field not editable: {field}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE cohort_sessions SET {field} = ? WHERE id = ?", (value, session_id))
        await db.commit()


async def delete_cohort_session(session_id: int) -> None:
    """Remove a session and its attendance rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cohort_attendance WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM cohort_sessions WHERE id = ?", (session_id,))
        await db.commit()


async def delete_recurring_rule(cohort_id: int) -> None:
    """Forget the schedule for a cohort. Already-created sessions are kept as-is
    (just no longer flagged as part of a live rule), and the generator will find
    no more `recurring=1` template to work from."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE cohort_sessions SET recurring = 0, days_of_week = '' "
            "WHERE cohort_id = ? AND recurring = 1",
            (cohort_id,),
        )
        await db.execute("UPDATE cohorts SET recurring_paused = 0 WHERE id = ?", (cohort_id,))
        await db.commit()


# ── Cohort helpers (needed by service layer) ──────────────────────────────────

async def get_cohort_name(cohort_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cohorts WHERE id = ?", (cohort_id,))
        row = await cur.fetchone()
    return row[0] if row else str(cohort_id)


async def get_active_members(cohort_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, telegram_id, name FROM cohort_members "
            "WHERE cohort_id = ? AND status = 'active' ORDER BY name",
            (cohort_id,),
        )
        return await cur.fetchall()


# ── Attendance ────────────────────────────────────────────────────────────────

async def seed_attendance_for_session(cohort_id: int, session_id: int) -> None:
    """Create pending attendance rows for all active members of a cohort right
    when a session (one-off or auto-generated) is created."""
    members = await get_active_members(cohort_id)
    if not members:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO cohort_attendance (session_id, member_id, status) "
            "VALUES (?, ?, 'pending')",
            [(session_id, member_id) for member_id, _tg, _name in members],
        )
        await db.commit()


# ── Recurring generator ───────────────────────────────────────────────────────

async def generate_recurring_cohort_sessions(cohort_id: int = None) -> int:
    """RECURRING: for every cohort with a recurring session schedule, create
    missing occurrences on the matching weekdays for the next 30 days.

    Called once/day from `reminder_loop()` in main.py, and once immediately
    after a psychologist sets up a new recurring schedule (via `cohort_id=`)
    so the horizon is filled in right away instead of waiting for the next
    daily tick.

    For each cohort the most recently created recurring session (highest id)
    acts as the template: its time-of-day, topic, link and days_of_week are
    reused for every generated occurrence. Dates that already have a session
    are skipped, so this is safe to call repeatedly (idempotent).
    """
    today = datetime.utcnow().date()
    horizon = today + timedelta(days=30)

    query = (
        "SELECT cs.cohort_id, MAX(cs.id) "
        "FROM cohort_sessions cs JOIN cohorts c ON c.id = cs.cohort_id "
        "WHERE cs.recurring = 1 AND c.status != 'archived' "
        "AND COALESCE(c.recurring_paused, 0) = 0 "
    )
    params: tuple = ()
    if cohort_id is not None:
        query += "AND cs.cohort_id = ? "
        params = (cohort_id,)
    query += "GROUP BY cs.cohort_id"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        rule_rows = await cur.fetchall()

    total_created = 0
    for c_id, last_id in rule_rows:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT session_number, scheduled_at, topic, link, days_of_week "
                "FROM cohort_sessions WHERE id = ?",
                (last_id,),
            )
            row = await cur.fetchone()
        if not row:
            continue
        last_num, sched_str, topic, link, days_csv = row
        if not days_csv:
            continue
        try:
            days = {int(d) for d in days_csv.split(",") if d.strip() != ""}
        except ValueError:
            continue
        if not days:
            continue
        try:
            time_part = datetime.strptime(sched_str, "%Y-%m-%d %H:%M").strftime("%H:%M")
        except ValueError:
            continue

        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT scheduled_at FROM cohort_sessions WHERE cohort_id = ?",
                (c_id,),
            )
            existing_dates = {r[0].split(" ")[0] for r in await cur.fetchall()}

        next_num = last_num
        day_cursor = today
        while day_cursor <= horizon:
            if day_cursor.weekday() in days:
                date_str = day_cursor.strftime("%Y-%m-%d")
                if date_str not in existing_dates:
                    next_num += 1
                    scheduled_at = f"{date_str} {time_part}"
                    new_session_id = await create_cohort_session(
                        c_id, next_num, scheduled_at, topic, link,
                        recurring=1, days_of_week=days_csv,
                    )
                    await seed_attendance_for_session(c_id, new_session_id)
                    existing_dates.add(date_str)
                    total_created += 1
            day_cursor += timedelta(days=1)

    if total_created:
        log.info("RECURRING: generator created %d session(s)", total_created)
    return total_created
