import aiosqlite

from core.db.base import DB_PATH


async def insert_plain_note(client_id: int, text: str, created_at: str):
    """Save a plain-text note for a client. Used by FSM flow and legacy /note command."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO notes (client_id, text, note_type, created_at) VALUES (?, ?, 'plain', ?)",
            (client_id, text, created_at)
        )
        await db.commit()


async def insert_soap_note(client_id: int, text: str, created_at: str):
    """Save a SOAP note (S/O/A/P fields already merged into `text`) for a client."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO notes (client_id, text, note_type, created_at) VALUES (?, ?, 'soap', ?)",
            (client_id, text, created_at)
        )
        await db.commit()


async def count_notes(client_id: int) -> int:
    """Return the number of notes for a client."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM notes WHERE client_id = ?", (client_id,))
        return (await cur.fetchone())[0]


async def get_notes_created_text(client_id: int):
    """Return list of (created_at, text) rows, in table order (no explicit ORDER BY)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT created_at, text FROM notes WHERE client_id = ?", (client_id,))
        return await cur.fetchall()


async def get_notes_full(client_id: int):
    """Return list of (created_at, note_type, text) rows ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT created_at, note_type, text FROM notes WHERE client_id = ? ORDER BY id",
            (client_id,))
        return await cur.fetchall()


async def get_notes_text_only(client_id: int):
    """Return list of (text,) rows ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT text FROM notes WHERE client_id = ? ORDER BY id", (client_id,))
        return await cur.fetchall()
