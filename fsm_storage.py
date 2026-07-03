"""Persistent FSM storage backed by the project's SQLite database.

Replaces MemoryStorage so that FSM state and data survive process restarts —
critical on mobile/UserLAnd where the process can be killed at any time.
State and per-user form data are kept in the `fsm_storage` table and restored
transparently on the next /start or any message.
"""

import json
import logging
from typing import Any, Mapping

import aiosqlite
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from database import DB_PATH

log = logging.getLogger(__name__)


def _make_key(storage_key: StorageKey) -> str:
    """Serialise StorageKey to a stable string primary key.

    Uses all discriminating fields so different bots / threads / destinies
    never collide.
    """
    return ":".join(str(v) for v in (
        storage_key.bot_id,
        storage_key.chat_id,
        storage_key.user_id,
        storage_key.thread_id or 0,
        storage_key.business_connection_id or "",
        storage_key.destiny,
    ))


class SQLiteFSMStorage(BaseStorage):
    """aiogram 3 BaseStorage implementation backed by the project's SQLite DB.

    The `fsm_storage` table is created by init_db() at startup — no per-call
    DDL needed here, which avoids unnecessary lock contention under concurrent
    handler execution.  All reads/writes open a fresh aiosqlite connection so
    the storage is safe to use from any coroutine without extra locking.
    """

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        k = _make_key(key)
        # Resolve State object → its string representation, or None to clear
        state_str = state.state if hasattr(state, "state") else state
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO fsm_storage (key, state, data) VALUES (?, ?, '{}')
                   ON CONFLICT(key) DO UPDATE SET state = excluded.state""",
                (k, state_str),
            )
            await db.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        k = _make_key(key)
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT state FROM fsm_storage WHERE key = ?", (k,)
            )
            row = await cur.fetchone()
        return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        k = _make_key(key)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO fsm_storage (key, state, data) VALUES (?, NULL, ?)
                   ON CONFLICT(key) DO UPDATE SET data = excluded.data""",
                (k, json.dumps(data)),
            )
            await db.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        k = _make_key(key)
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT data FROM fsm_storage WHERE key = ?", (k,)
            )
            row = await cur.fetchone()
        if not row or not row[0]:
            return {}
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            log.warning("SQLiteFSMStorage: corrupt data for key %s, returning empty", k)
            return {}

    async def close(self) -> None:
        # aiosqlite connections are opened and closed per-call; nothing to clean up
        pass
