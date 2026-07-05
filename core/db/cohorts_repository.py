"""Cohorts repository — ownership verification for the cohort entity."""

import aiosqlite

from core.db.base import DB_PATH


async def verify_cohort_owner(cohort_id: int, uid: int) -> str | None:
    """Returns the cohort name if `uid` is its owning psychologist, else None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name FROM cohorts WHERE id = ? AND psychologist_id = ?",
            (cohort_id, uid),
        )
        row = await cur.fetchone()
    return row[0] if row else None
