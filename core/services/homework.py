"""Homework service layer.

No plan-limit or length-validation business rules exist for homework (see
Этап 0 audit). The one real business rule found — notifying a connected
client via Telegram when a new homework item is assigned — is implemented
here, wrapping the repository. All other access is a thin pass-through
re-export so handlers have a single stable import point.
"""

from core.db.clients_repository import get_client_lang
from core.db.homework_repository import (
    get_active_homework_for_psych,
    get_client_homeworks,
    get_client_homeworks_created_text,
    get_client_homeworks_full,
    insert_homework,
)
from translations import t

__all__ = [
    "assign_homework",
    "get_active_homework_for_psych",
    "get_client_homeworks",
    "get_client_homeworks_created_text",
    "get_client_homeworks_full",
    "insert_homework",
]


async def assign_homework(client_id: int, client_tg, hw_text: str, created_at: str, bot) -> bool:
    """Save the homework item and, if the client is connected via Telegram,
    notify them immediately. Returns True if a notification was sent."""
    await insert_homework(client_id, hw_text, created_at)
    if client_tg and bot:
        c_lang = await get_client_lang(client_tg)
        await bot.send_message(client_tg, t(c_lang, "new_homework_client", text=hw_text))
        return True
    return False
