"""Core repository for the tariff / plans domain.

All raw SQL for user_plans and promo_codes tables lives here.
Business logic (expiry handling, limit checks, promo validation) lives in
core/services/plans.py.
"""

import aiosqlite

from core.db.base import DB_PATH


# ── user_plans ─────────────────────────────────────────────────────────────

async def fetch_user_plan_row(user_id: int) -> tuple | None:
    """Return (plan, expires_at) for the user, or None if no row exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT plan, expires_at FROM user_plans WHERE user_id = ?",
            (user_id,),
        )
        return await cur.fetchone()


async def upsert_user_plan(
    user_id: int,
    plan_name: str,
    expires_at: str | None,
    updated_at: str,
) -> None:
    """Insert or update the user's plan row."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO user_plans (user_id, plan, expires_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 plan       = excluded.plan,
                 expires_at = excluded.expires_at,
                 updated_at = excluded.updated_at""",
            (user_id, plan_name, expires_at, updated_at),
        )
        await db.commit()


async def downgrade_user_plan(user_id: int) -> None:
    """Downgrade an expired Pro user to Start, clearing expires_at."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_plans SET plan = 'start', expires_at = NULL WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def fetch_expiring_plans(window_start: str, window_end: str) -> list:
    """Return (user_id, plan, expires_at) rows expiring within [window_start, window_end)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, plan, expires_at FROM user_plans "
            "WHERE plan != 'start' AND expires_at IS NOT NULL "
            "AND expires_at >= ? AND expires_at < ?",
            (window_start, window_end),
        )
        return await cur.fetchall()


# ── promo_codes ────────────────────────────────────────────────────────────

async def fetch_promo_code(code: str) -> tuple | None:
    """Return (plan, duration_days, max_uses, used_count) or None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT plan, duration_days, max_uses, used_count FROM promo_codes WHERE code = ?",
            (code,),
        )
        return await cur.fetchone()


async def increment_promo_used_count(code: str) -> None:
    """Increment used_count for a promo code by 1."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
            (code,),
        )
        await db.commit()


async def insert_or_replace_promo(
    code: str,
    plan_name: str,
    duration_days: int,
    max_uses: int | None,
    created_at: str,
) -> None:
    """Insert or replace a promo code record (admin operation)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO promo_codes
               (code, plan, duration_days, max_uses, used_count, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (code, plan_name, duration_days, max_uses, created_at),
        )
        await db.commit()


async def fetch_all_promos() -> list:
    """Return all promo codes ordered newest-first.

    Columns: (code, plan, duration_days, max_uses, used_count)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT code, plan, duration_days, max_uses, used_count "
            "FROM promo_codes ORDER BY created_at DESC"
        )
        return await cur.fetchall()


# ── helper queries used by limit checks ────────────────────────────────────

async def fetch_psychologist_lang(user_id: int) -> str:
    """Return the language code for a psychologist, defaulting to 'ru'."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT language FROM psychologists WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
    return row[0] if row else "ru"


async def count_active_clients(psychologist_id: int) -> int:
    """Count non-archived clients for a psychologist."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM clients WHERE psychologist_id = ? AND is_archived = 0",
            (psychologist_id,),
        )
        return (await cur.fetchone())[0]


async def count_cohorts(psychologist_id: int) -> int:
    """Count cohorts for a psychologist."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM cohorts WHERE psychologist_id = ?",
            (psychologist_id,),
        )
        return (await cur.fetchone())[0]


async def count_cohort_members(cohort_id: int) -> int:
    """Count active members in a cohort."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM cohort_members WHERE cohort_id = ?",
            (cohort_id,),
        )
        return (await cur.fetchone())[0]
