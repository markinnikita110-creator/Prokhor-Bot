import aiosqlite

from core.db.base import DB_PATH


async def insert_homework(client_id: int, text: str, created_at: str):
    """Save a new homework assignment for a client."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO homeworks (client_id, text, created_at) VALUES (?, ?, ?)",
            (client_id, text, created_at)
        )
        await db.commit()


async def get_active_homework_for_psych(psych_id: int):
    """Return up to 30 most recent active (not completed) homework items across
    all non-archived clients of a psychologist, as (client_name, text) rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, h.text FROM homeworks h "
            "JOIN clients c ON c.id = h.client_id "
            "WHERE c.psychologist_id = ? AND h.completed = 0 AND c.is_archived = 0 "
            "ORDER BY h.id DESC LIMIT 30",
            (psych_id,)
        )
        return await cur.fetchall()


async def get_client_homeworks(client_id: int):
    """Return (text, completed) rows for a client, ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT text, completed FROM homeworks WHERE client_id = ? ORDER BY id", (client_id,)
        )
        return await cur.fetchall()


async def get_client_homeworks_full(client_id: int):
    """Return (created_at, text, completed) rows for a client, ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT created_at, text, completed FROM homeworks WHERE client_id = ? ORDER BY id",
            (client_id,))
        return await cur.fetchall()


async def get_client_homeworks_created_text(client_id: int):
    """Return (created_at, text) rows for a client, in table order (no explicit ORDER BY)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT created_at, text FROM homeworks WHERE client_id = ?", (client_id,))
        return await cur.fetchall()
