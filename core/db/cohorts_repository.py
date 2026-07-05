"""Cohorts repository — base cohort domain CRUD.

Covers: cohort creation/read/edit/archive, member add/list, attendance,
recurring-pause flag.

Out of scope (future domain): cohort_sessions scheduling, recurring rule
generation, cohort check-ins/broadcasts, supervision.
"""

import secrets

import aiosqlite

from core.db.base import DB_PATH
from core.utils.time import now_str


# ── Token helper ──────────────────────────────────────────────────────────

def _make_cohort_token() -> str:
    return secrets.token_hex(6)


# ── Cohort CRUD ───────────────────────────────────────────────────────────

async def create_cohort(
    psychologist_id: int,
    name: str,
    description: str,
    type_: str,
    max_participants: int,
) -> tuple[int, str]:
    """Insert a new cohort row. Returns (cohort_id, invite_token)."""
    token = _make_cohort_token()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cohorts "
            "(psychologist_id, name, description, type, max_participants, status, created_at, invite_token) "
            "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
            (psychologist_id, name, description, type_, max_participants, now_str(), token),
        )
        cohort_id = cur.lastrowid
        await db.commit()
    return cohort_id, token


async def get_cohort_by_token(token: str):
    """Return (id, psychologist_id, name, max_participants) for invite token, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, psychologist_id, name, max_participants FROM cohorts WHERE invite_token = ?",
            (token,),
        )
        return await cur.fetchone()


async def get_cohorts_for_psych(psychologist_id: int) -> list:
    """Return list of (id, name, max_participants) ordered by created_at DESC."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name, max_participants FROM cohorts WHERE psychologist_id = ? ORDER BY created_at DESC",
            (psychologist_id,),
        )
        return await cur.fetchall()


async def get_cohort_name(cohort_id: int) -> str:
    """Return cohort name, or str(cohort_id) if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cohorts WHERE id = ?", (cohort_id,))
        row = await cur.fetchone()
    return row[0] if row else str(cohort_id)


async def get_cohort_invite_token(cohort_id: int) -> tuple[str | None, str]:
    """Return (invite_token, name) for cohort_id, or (None, '') if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT invite_token, name FROM cohorts WHERE id = ?", (cohort_id,))
        row = await cur.fetchone()
    return (row[0], row[1]) if row else (None, "")


async def get_cohort_status(cohort_id: int) -> tuple[str, str] | None:
    """Return (name, status) for cohort_id, or None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name, status FROM cohorts WHERE id = ?", (cohort_id,))
        return await cur.fetchone()


async def get_cohort_for_owner(cohort_id: int, uid: int) -> tuple[str, str] | None:
    """Return (name, status) only if uid is the owning psychologist, else None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name, status FROM cohorts WHERE id = ? AND psychologist_id = ?",
            (cohort_id, uid),
        )
        return await cur.fetchone()


async def verify_cohort_owner(cohort_id: int, uid: int) -> str | None:
    """Return cohort name if uid is the owning psychologist, else None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name FROM cohorts WHERE id = ? AND psychologist_id = ?", (cohort_id, uid),
        )
        row = await cur.fetchone()
    return row[0] if row else None


async def archive_cohort(cohort_id: int) -> None:
    """Set cohort status to 'archived'."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE cohorts SET status = 'archived' WHERE id = ?", (cohort_id,))
        await db.commit()


async def is_recurring_paused(cohort_id: int) -> bool:
    """Return True if the cohort's recurring schedule is paused."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT recurring_paused FROM cohorts WHERE id = ?", (cohort_id,))
        row = await cur.fetchone()
    return bool(row and row[0])


async def set_recurring_paused(cohort_id: int, paused: bool) -> None:
    """Set or clear the recurring_paused flag on a cohort."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE cohorts SET recurring_paused = ? WHERE id = ?", (1 if paused else 0, cohort_id),
        )
        await db.commit()


# ── Member CRUD ───────────────────────────────────────────────────────────

async def get_member_count(cohort_id: int) -> int:
    """Return count of active members in a cohort."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM cohort_members WHERE cohort_id = ? AND status = 'active'",
            (cohort_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def is_member(cohort_id: int, telegram_id: int) -> bool:
    """Return True if telegram_id is an active member of cohort_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM cohort_members WHERE cohort_id = ? AND telegram_id = ? AND status = 'active'",
            (cohort_id, telegram_id),
        )
        return bool(await cur.fetchone())


async def add_member(cohort_id: int, telegram_id: int, name: str) -> None:
    """Add a member to a cohort (INSERT OR IGNORE)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO cohort_members (cohort_id, telegram_id, name, joined_at, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (cohort_id, telegram_id, name, now_str()),
        )
        await db.commit()


async def get_active_members(cohort_id: int) -> list:
    """Return list of (id, telegram_id, name) for active members, ordered by name."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, telegram_id, name FROM cohort_members "
            "WHERE cohort_id = ? AND status = 'active' ORDER BY name",
            (cohort_id,),
        )
        return await cur.fetchall()


async def get_next_manual_id(cohort_id: int) -> int:
    """Return a unique negative telegram_id for a manually-added (offline) member."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT MIN(telegram_id) FROM cohort_members WHERE cohort_id = ?", (cohort_id,))
        row = await cur.fetchone()
        min_id = row[0] if (row and row[0] is not None) else 0
    return min(min_id, 0) - 1


# ── Attendance ────────────────────────────────────────────────────────────

async def upsert_attendance(session_id: int, member_id: int, status: str) -> None:
    """Insert or update attendance status for a member in a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_attendance (session_id, member_id, status) VALUES (?, ?, ?) "
            "ON CONFLICT(session_id, member_id) DO UPDATE SET status = excluded.status",
            (session_id, member_id, status),
        )
        await db.commit()


async def get_attendance_for_session(session_id: int) -> dict:
    """Return {member_id: status} mapping for all attendance rows of a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT member_id, status FROM cohort_attendance WHERE session_id = ?",
            (session_id,),
        )
        rows = await cur.fetchall()
    return {row[0]: row[1] for row in rows}


async def seed_attendance_for_session(cohort_id: int, session_id: int) -> None:
    """Create pending attendance rows for all active cohort members for a session."""
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


# ── Admin helpers ─────────────────────────────────────────────────────────

async def list_all_cohorts_with_member_count() -> list:
    """Return (id, name, status, active_member_count) for all cohorts, newest first.

    Used by the admin panel.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT c.id, c.name, c.status, COUNT(cm.telegram_id) AS cnt
               FROM cohorts c
               LEFT JOIN cohort_members cm ON cm.cohort_id = c.id AND cm.status = 'active'
               GROUP BY c.id ORDER BY c.created_at DESC"""
        )
        return await cur.fetchall()
