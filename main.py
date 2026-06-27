"""Prokhor — Telegram assistant for psychologists.
Entry point: sets up bot, registers all routers, runs reminder loop, starts polling.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from database import (
    DB_PATH, get_client_lang, get_client_timezone, get_user_lang,
    get_user_timezone, init_db, migrate_db, utc_to_local,
)
from handlers import routers
from handlers.clients import set_bot_username
from translations import t

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

bot = Bot(token=os.environ["BOT_TOKEN"])
dp  = Dispatcher(storage=MemoryStorage())


# ── Background: 24h / 1h session reminders ────────────────────────────────
async def reminder_loop():
    while True:
        await asyncio.sleep(60)
        try:
            now = datetime.utcnow()  # scheduled_at is stored in UTC — compare UTC vs UTC
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT s.id, s.psychologist_id, s.client_name, s.scheduled_at, "
                    "s.link, s.reminded_24h, s.reminded_1h, c.telegram_id "
                    "FROM sessions s "
                    "LEFT JOIN clients c ON c.psychologist_id = s.psychologist_id "
                    "  AND c.name = s.client_name "
                    "WHERE s.reminded_1h = 0"
                )
                sessions = await cur.fetchall()

            for sid, psych_id, client_name, scheduled_at_str, link, r24, r1h, client_tg in sessions:
                try:
                    session_dt = datetime.strptime(scheduled_at_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                delta = session_dt - now
                p_lang = await get_user_lang(psych_id)
                # Convert UTC session time to psychologist's local time for display
                _, p_offset = await get_user_timezone(psych_id)
                p_local = utc_to_local(scheduled_at_str, p_offset)
                p_display = datetime.strptime(p_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                link_line = t(p_lang, "session_link_line", link=link) if link else ""

                async with aiosqlite.connect(DB_PATH) as db:
                    if not r24 and timedelta(hours=23) < delta <= timedelta(hours=25):
                        await bot.send_message(
                            psych_id,
                            t(p_lang, "reminder_psych_24h",
                              client=client_name, time=p_display) + link_line
                        )
                        if client_tg:
                            c_lang = await get_client_lang(client_tg)
                            _, c_offset = await get_client_timezone(client_tg)
                            c_local = utc_to_local(scheduled_at_str, c_offset)
                            c_display = datetime.strptime(c_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                            c_link = t(c_lang, "session_link_line", link=link) if link else ""
                            await bot.send_message(
                                client_tg,
                                t(c_lang, "reminder_client_24h", time=c_display) + c_link
                            )
                        await db.execute(
                            "UPDATE sessions SET reminded_24h = 1 WHERE id = ?", (sid,))
                        await db.commit()

                    elif not r1h and timedelta(minutes=50) < delta <= timedelta(minutes=70):
                        await bot.send_message(
                            psych_id,
                            t(p_lang, "reminder_psych_1h",
                              client=client_name, time=p_display) + link_line
                        )
                        if client_tg:
                            c_lang = await get_client_lang(client_tg)
                            _, c_offset = await get_client_timezone(client_tg)
                            c_local = utc_to_local(scheduled_at_str, c_offset)
                            c_display = datetime.strptime(c_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                            c_link = t(c_lang, "session_link_line", link=link) if link else ""
                            await bot.send_message(
                                client_tg,
                                t(c_lang, "reminder_client_1h", time=c_display) + c_link
                            )
                        await db.execute(
                            "UPDATE sessions SET reminded_1h = 1 WHERE id = ?", (sid,))
                        await db.commit()

        except Exception as e:
            log.error("Reminder loop error: %s", e)


# ── Startup ────────────────────────────────────────────────────────────────
async def main():
    await init_db()
    await migrate_db()

    me = await bot.get_me()
    set_bot_username(me.username or "")
    log.info("Bot started: @%s", me.username)

    # Register all routers
    for r in routers:
        dp.include_router(r)

    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
