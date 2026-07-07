"""Core repository for supervision cases domain.

Four SQL operations extracted from handlers/supervision.py:
  - insert_supervision_case   : INSERT new case
  - get_supervision_logbook   : SELECT all cases for a psychologist
  - get_supervision_open_cases: SELECT open cases with full detail
  - close_supervision_case    : owner-check SELECT + UPDATE close (atomic)
"""

import aiosqlite

from core.db.base import DB_PATH


async def insert_supervision_case(
    psychologist_id: int,
    client_alias: str,
    presenting_issue: str,
    hypothesis: str,
    intervention: str,
    outcome: str,
    created_at: str,
) -> int:
    """Insert a new supervision case. Returns the new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO supervision_cases "
            "(psychologist_id, client_alias, presenting_issue, hypothesis, intervention, outcome, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)",
            (psychologist_id, client_alias, presenting_issue, hypothesis, intervention, outcome, created_at, created_at),
        )
        case_id = cur.lastrowid
        await db.commit()
    return case_id


async def get_supervision_logbook(psychologist_id: int) -> list:
    """Return all supervision cases for a psychologist ordered newest-first.

    Columns: (id, client_alias, status, created_at)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, client_alias, status, created_at "
            "FROM supervision_cases WHERE psychologist_id = ? "
            "ORDER BY created_at DESC",
            (psychologist_id,),
        )
        return await cur.fetchall()


async def get_supervision_open_cases(psychologist_id: int) -> list:
    """Return open supervision cases with full detail for a psychologist.

    Columns: (id, client_alias, presenting_issue, hypothesis, intervention, outcome)
    Owner-check is implicit via WHERE psychologist_id = ?.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, client_alias, presenting_issue, hypothesis, intervention, outcome "
            "FROM supervision_cases WHERE psychologist_id = ? AND status = 'open' "
            "ORDER BY created_at DESC",
            (psychologist_id,),
        )
        return await cur.fetchall()


async def close_supervision_case(case_id: int, psychologist_id: int, updated_at: str) -> bool:
    """Owner-check then close a supervision case atomically.

    Returns True if the case was found and closed, False if not found
    (owner-check fails — case belongs to another psychologist or doesn't exist).
    Owner-check is at the mutation point, matching the original handler position.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM supervision_cases WHERE id = ? AND psychologist_id = ?",
            (case_id, psychologist_id),
        )
        row = await cur.fetchone()
        if not row:
            return False
        await db.execute(
            "UPDATE supervision_cases SET status = 'closed', updated_at = ? WHERE id = ?",
            (updated_at, case_id),
        )
        await db.commit()
    return True
