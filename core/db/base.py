import aiosqlite

DB_PATH = "prokhor.db"


def get_connection() -> aiosqlite.Connection:
    """Return a new aiosqlite connection context manager to the app database.

    Usage mirrors the existing pattern used throughout database.py/handlers:

        async with get_connection() as db:
            cur = await db.execute(...)
    """
    return aiosqlite.connect(DB_PATH)
