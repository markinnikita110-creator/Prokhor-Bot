"""Cohort checkins repository — CRUD for cohort_checkin_configs and cohort_checkins.

All owner-checks live in the callers (handlers or service layer).
Score bounds validation (1–10) lives in the caller before save_checkin_response.
"""

import logging

import aiosqlite

from core.db.base import DB_PATH

log = logging.getLogger(__name__)


# ── Check-in config ───────────────────────────────────────────────────────────

async def upsert_checkin_config(cohort_id: int, question: str, interval_h: int) -> None:
    """Insert or update the check-in config for a cohort."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_checkin_configs (cohort_id, question, interval_h) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(cohort_id) DO UPDATE SET "
            "question=excluded.question, interval_h=excluded.interval_h, enabled=1",
            (cohort_id, question, interval_h),
        )
        await db.commit()
    log.info("COHORT_CHECKIN: config saved cohort_id=%d interval_h=%d", cohort_id, interval_h)


async def get_checkin_config(cohort_id: int) -> str | None:
    """Return the check-in question for cohort_id, or None if not configured."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT question FROM cohort_checkin_configs WHERE cohort_id = ?",
            (cohort_id,),
        )
        row = await cur.fetchone()
    return row[0] if row and row[0] else None


# ── Check-in responses ────────────────────────────────────────────────────────

async def save_checkin_response(
    cohort_id: int,
    member_tg_id: int,
    score: int,
    question: str,
    answered_at: str,
) -> None:
    """Persist a member's check-in response.

    Caller is responsible for validating 1 <= score <= 10 before calling this.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_checkins "
            "(cohort_id, member_telegram_id, score, question_text, answered_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (cohort_id, member_tg_id, score, question, answered_at),
        )
        await db.commit()
    log.info(
        "COHORT_CHECKIN: response saved cohort_id=%d member_tg_id=%d score=%d",
        cohort_id, member_tg_id, score,
    )


async def get_checkin_summary(cohort_id: int) -> list:
    """Return per-member check-in stats: (tg_id, name, response_count, avg_score)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT cm.telegram_id, cm.name, COUNT(cc.id), "
            "COALESCE(ROUND(AVG(cc.score), 1), 0.0) "
            "FROM cohort_members cm "
            "LEFT JOIN cohort_checkins cc "
            "  ON cc.cohort_id = cm.cohort_id AND cc.member_telegram_id = cm.telegram_id "
            "WHERE cm.cohort_id = ? AND cm.status = 'active' "
            "GROUP BY cm.telegram_id, cm.name ORDER BY cm.name",
            (cohort_id,),
        )
        return await cur.fetchall()
