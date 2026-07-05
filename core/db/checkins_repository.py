import aiosqlite

from core.db.base import DB_PATH


async def insert_manual_checkin(client_id: int, score: int, timestamp: str):
    """Save a manually-recorded (non-auto) check-in score."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checkins (client_id, score, auto, timestamp) VALUES (?, ?, 0, ?)",
            (client_id, score, timestamp)
        )
        await db.commit()


async def insert_auto_checkin(client_id: int, timestamp: str):
    """Save an auto-triggered check-in placeholder (score=0, auto=1)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checkins (client_id, score, auto, timestamp) VALUES (?, 0, 1, ?)",
            (client_id, timestamp)
        )
        await db.commit()


async def get_positive_scores(client_id: int):
    """Return raw list of (score,) rows where score > 0, no ordering."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT score FROM checkins WHERE client_id = ? AND score > 0", (client_id,))
        return await cur.fetchall()


async def get_all_scores(client_id: int):
    """Return raw list of (score,) rows including auto placeholders, no filter/order."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT score FROM checkins WHERE client_id = ?", (client_id,))
        return await cur.fetchall()


async def get_all_scores_ordered(client_id: int):
    """Return (score,) rows including auto placeholders, ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT score FROM checkins WHERE client_id = ? ORDER BY id", (client_id,))
        return await cur.fetchall()


async def get_positive_checkins_timestamped(client_id: int):
    """Return (timestamp, score) rows where score > 0, no explicit ORDER BY."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timestamp, score FROM checkins WHERE client_id = ? AND score > 0", (client_id,))
        return await cur.fetchall()


async def get_positive_checkins_timestamped_ordered(client_id: int):
    """Return (timestamp, score) rows where score > 0, ordered by id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timestamp, score FROM checkins WHERE client_id = ? AND score > 0 ORDER BY id",
            (client_id,))
        return await cur.fetchall()


async def get_max_checkin_timestamp(client_id: int):
    """Return the latest check-in timestamp for a client, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT MAX(timestamp) FROM checkins WHERE client_id = ?", (client_id,))
        return (await cur.fetchone())[0]


async def get_last_n_checkins(client_id: int, limit: int = 5):
    """Return the most recent N (score, timestamp) rows, newest first (by id)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT score, timestamp FROM checkins WHERE client_id = ? ORDER BY id DESC LIMIT ?",
            (client_id, limit)
        )
        return await cur.fetchall()


async def get_last_n_positive_checkins(client_id: int, limit: int = 10):
    """Return the most recent N (score, timestamp) rows with score > 0, newest first (by id)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT score, timestamp FROM checkins "
            "WHERE client_id = ? AND score > 0 ORDER BY id DESC LIMIT ?",
            (client_id, limit)
        )
        return await cur.fetchall()


async def get_recent_checkins_for_psych(psych_id: int, limit: int = 10):
    """Return (client_name, score, timestamp) for the most recent check-ins across
    all clients of a psychologist, newest first by timestamp."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, ci.score, ci.timestamp FROM checkins ci "
            "JOIN clients c ON c.id = ci.client_id "
            "WHERE c.psychologist_id = ? AND ci.score > 0 "
            "ORDER BY ci.timestamp DESC LIMIT ?",
            (psych_id, limit)
        )
        return await cur.fetchall()


async def get_auto_checkins_for_psych(psych_id: int):
    """Return (client_name, interval_min) for all auto check-in configs of a psychologist."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, interval_min FROM auto_checkins WHERE psychologist_id = ?",
            (psych_id,)
        )
        return await cur.fetchall()


async def get_auto_checkin_client_names(psych_id: int):
    """Return client_name for all auto check-in configs of a psychologist."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name FROM auto_checkins WHERE psychologist_id = ?",
            (psych_id,)
        )
        return await cur.fetchall()


async def upsert_auto_checkin_config(psych_id: int, client_name: str, interval_min: int):
    """Create or update an auto check-in config for a client, resetting last_sent."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO auto_checkins (psychologist_id, client_name, interval_min, last_sent) "
            "VALUES (?, ?, ?, NULL) "
            "ON CONFLICT(psychologist_id, client_name) "
            "DO UPDATE SET interval_min = excluded.interval_min, last_sent = NULL",
            (psych_id, client_name, interval_min)
        )
        await db.commit()


async def update_auto_checkin_last_sent(psych_id: int, client_name: str, timestamp: str):
    """Update the last_sent timestamp for an auto check-in config."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE auto_checkins SET last_sent = ? WHERE psychologist_id = ? AND client_name = ?",
            (timestamp, psych_id, client_name)
        )
        await db.commit()
