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
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    DB_PATH, get_client_lang, get_client_timezone, get_user_lang,
    get_user_timezone, get_cohort_member_lang, get_cohort_member_timezone,
    init_db, migrate_db, now_str, utc_to_local,
)
from handlers import routers
from handlers.clients import set_bot_username
from handlers.cohorts import generate_recurring_cohort_sessions  # RECURRING
from handlers.legal import ConsentMiddleware
from translations import t

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

bot = Bot(token=os.environ["BOT_TOKEN"])
dp  = Dispatcher(storage=MemoryStorage())


# ── Helper: build cohort check-in score keyboard ───────────────────────────
def _cohort_checkin_kb(cohort_id: int, member_tg: int) -> InlineKeyboardMarkup:
    """COHORT_V2: 1-10 score keyboard — mirrors the one in cohorts.py."""
    row1 = [
        InlineKeyboardButton(text=str(i),
                             callback_data=f"cci_{cohort_id}_{member_tg}_{i}")
        for i in range(1, 6)
    ]
    row2 = [
        InlineKeyboardButton(text=str(i),
                             callback_data=f"cci_{cohort_id}_{member_tg}_{i}")
        for i in range(6, 11)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


# ── RECURRING_IND: daily generator for individual recurring sessions ────────

async def generate_recurring_individual_sessions():
    """Generate one-off session rows for all active individual recurring templates (next 30 days)."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=30)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT s.id, s.psychologist_id, s.client_name, s.days_of_week, "
            "s.scheduled_at, s.topic, s.link, p.tz_offset "
            "FROM sessions s "
            "JOIN psychologists p ON p.telegram_id = s.psychologist_id "
            "JOIN clients c ON c.psychologist_id = s.psychologist_id "
            "  AND c.name = s.client_name "
            "WHERE s.recurring = 1 AND c.is_archived = 0 AND c.recurring_paused = 0"
        )
        templates = await cur.fetchall()
        for sid, psych_id, client_name, days_csv, tpl_utc, topic, link, tz_offset in templates:
            try:
                day_idxs = [int(d) for d in (days_csv or "").split(",") if d.strip()]
            except ValueError:
                continue
            if not day_idxs:
                continue
            try:
                tpl_dt = datetime.strptime(tpl_utc, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            tpl_local = tpl_dt + timedelta(minutes=(tz_offset or 0))
            time_hh_mm = tpl_local.strftime("%H:%M")
            check_date = now.date()
            while check_date <= horizon.date():
                if check_date.weekday() in day_idxs:
                    local_dt_str = f"{check_date.strftime('%Y-%m-%d')} {time_hh_mm}"
                    local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M")
                    utc_dt = local_dt - timedelta(minutes=(tz_offset or 0))
                    if utc_dt > now:
                        utc_str = utc_dt.strftime("%Y-%m-%d %H:%M")
                        cur2 = await db.execute(
                            "SELECT 1 FROM sessions WHERE psychologist_id = ? "
                            "AND client_name = ? AND scheduled_at = ? AND recurring = 0",
                            (psych_id, client_name, utc_str))
                        if not await cur2.fetchone():
                            await db.execute(
                                "INSERT INTO sessions "
                                "(psychologist_id, client_name, scheduled_at, topic, link) "
                                "VALUES (?, ?, ?, ?, ?)",
                                (psych_id, client_name, utc_str, topic or "", link or ""))
                check_date += timedelta(days=1)
        await db.commit()
    log.info("RECURRING_IND: individual recurring sessions generated")


# ── Background: reminder loop ──────────────────────────────────────────────
_last_recurring_gen_date = None  # RECURRING: tracks last date the daily generator ran


async def reminder_loop():
    global _last_recurring_gen_date
    while True:
        await asyncio.sleep(60)
        try:
            now = datetime.utcnow()

            # ── RECURRING: run the recurring-session generator once/day ────
            today = now.date()
            if _last_recurring_gen_date != today:
                try:
                    await generate_recurring_cohort_sessions()
                    await generate_recurring_individual_sessions()  # RECURRING_IND
                finally:
                    _last_recurring_gen_date = today

            # ── Individual session reminders ───────────────────────────────
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

            # ── COHORT_SESSION: cohort session reminders ───────────────────
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT cs.id, cs.cohort_id, cs.session_number, cs.scheduled_at, "
                    "cs.link, cs.reminded_24h, cs.reminded_1h, "
                    "c.psychologist_id, c.name AS cohort_name "
                    "FROM cohort_sessions cs "
                    "JOIN cohorts c ON c.id = cs.cohort_id "
                    "WHERE cs.reminded_1h = 0 AND cs.status = 'scheduled' "
                    "AND c.status != 'archived'"
                )
                cohort_sessions = await cur.fetchall()

            for cs_id, cohort_id, sess_num, sched_str, link, r24, r1h, psych_id, cohort_name in cohort_sessions:
                try:
                    session_dt = datetime.strptime(sched_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
                delta = session_dt - now

                async with aiosqlite.connect(DB_PATH) as db:
                    cur = await db.execute(
                        "SELECT telegram_id FROM cohort_members "
                        "WHERE cohort_id = ? AND status = 'active'",
                        (cohort_id,),
                    )
                    members = [row[0] for row in await cur.fetchall()]

                if not r24 and timedelta(hours=23) < delta <= timedelta(hours=25):
                    p_lang = await get_user_lang(psych_id)
                    _, p_offset = await get_user_timezone(psych_id)
                    p_local = utc_to_local(sched_str, p_offset)
                    p_time = datetime.strptime(p_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                    p_link = t(p_lang, "cs_link_line", link=link) if link else ""
                    await bot.send_message(
                        psych_id,
                        t(p_lang, "cs_reminder_psych_24h",
                          num=sess_num, cohort=cohort_name, time=p_time) + p_link,
                    )
                    for member_tg in members:
                        try:
                            m_lang = await get_cohort_member_lang(member_tg)
                            _, m_offset = await get_cohort_member_timezone(member_tg)
                            m_local = utc_to_local(sched_str, m_offset)
                            m_time = datetime.strptime(m_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                            m_link = t(m_lang, "cs_link_line", link=link) if link else ""
                            await bot.send_message(
                                member_tg,
                                t(m_lang, "cs_reminder_24h",
                                  num=sess_num, cohort=cohort_name, time=m_time) + m_link,
                            )
                        except Exception as e:
                            log.warning("COHORT_SESSION: 24h remind fail member_tg=%d: %s", member_tg, e)
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "UPDATE cohort_sessions SET reminded_24h = 1 WHERE id = ?", (cs_id,)
                        )
                        await db.commit()

                elif not r1h and timedelta(minutes=50) < delta <= timedelta(minutes=70):
                    p_lang = await get_user_lang(psych_id)
                    _, p_offset = await get_user_timezone(psych_id)
                    p_local = utc_to_local(sched_str, p_offset)
                    p_time = datetime.strptime(p_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                    p_link = t(p_lang, "cs_link_line", link=link) if link else ""
                    await bot.send_message(
                        psych_id,
                        t(p_lang, "cs_reminder_psych_1h",
                          num=sess_num, cohort=cohort_name, time=p_time) + p_link,
                    )
                    for member_tg in members:
                        try:
                            m_lang = await get_cohort_member_lang(member_tg)
                            _, m_offset = await get_cohort_member_timezone(member_tg)
                            m_local = utc_to_local(sched_str, m_offset)
                            m_time = datetime.strptime(m_local, "%Y-%m-%d %H:%M").strftime("%H:%M")
                            m_link = t(m_lang, "cs_link_line", link=link) if link else ""
                            await bot.send_message(
                                member_tg,
                                t(m_lang, "cs_reminder_1h",
                                  num=sess_num, cohort=cohort_name, time=m_time) + m_link,
                            )
                        except Exception as e:
                            log.warning("COHORT_SESSION: 1h remind fail member_tg=%d: %s", member_tg, e)
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "UPDATE cohort_sessions SET reminded_1h = 1 WHERE id = ?", (cs_id,)
                        )
                        await db.commit()

            # ── COHORT_V2: auto check-ins ──────────────────────────────────
            async with aiosqlite.connect(DB_PATH) as db:
                cur = await db.execute(
                    "SELECT cc.cohort_id, cc.question, cc.interval_h, cc.last_sent_at, "
                    "c.psychologist_id, c.name "
                    "FROM cohort_checkin_configs cc "
                    "JOIN cohorts c ON c.id = cc.cohort_id "
                    "WHERE cc.enabled = 1 AND c.status != 'archived'"
                )
                checkin_cfgs = await cur.fetchall()

            for cohort_id, question, interval_h, last_sent_at, psych_id, cohort_name in checkin_cfgs:
                if not question:
                    continue
                should_send = False
                if last_sent_at is None:
                    should_send = True
                else:
                    try:
                        last_sent_dt = datetime.strptime(last_sent_at, "%Y-%m-%d %H:%M")
                        if (now - last_sent_dt) >= timedelta(hours=interval_h):
                            should_send = True
                    except ValueError:
                        should_send = True

                if not should_send:
                    continue

                async with aiosqlite.connect(DB_PATH) as db:
                    cur = await db.execute(
                        "SELECT telegram_id FROM cohort_members "
                        "WHERE cohort_id = ? AND status = 'active'",
                        (cohort_id,),
                    )
                    members = [row[0] for row in await cur.fetchall()]

                sent = 0
                for member_tg in members:
                    try:
                        kb = _cohort_checkin_kb(cohort_id, member_tg)
                        await bot.send_message(member_tg, question, reply_markup=kb)
                        sent += 1
                    except Exception as e:
                        log.warning("COHORT_V2: auto-checkin fail member_tg=%d: %s", member_tg, e)

                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE cohort_checkin_configs SET last_sent_at = ? WHERE cohort_id = ?",
                        (now_str(), cohort_id),
                    )
                    await db.commit()
                log.info("COHORT_V2: auto-checkin sent cohort_id=%d members=%d/%d",
                         cohort_id, sent, len(members))

        except Exception as e:
            log.error("Reminder loop error: %s", e)


# ── Startup ────────────────────────────────────────────────────────────────
async def main():
    await init_db()
    await migrate_db()

    me = await bot.get_me()
    set_bot_username(me.username or "")
    log.info("Bot started: @%s", me.username)

    await bot.set_my_commands([
        BotCommand(command="start",           description="Главное меню"),
        BotCommand(command="privacy",         description="Политика конфиденциальности"),
        BotCommand(command="terms",           description="Условия использования"),
        BotCommand(command="consent",         description="Согласие на обработку ПД"),
        BotCommand(command="delete_my_data",  description="Удалить все мои данные"),
        BotCommand(command="supervision_case",     description="Новый случай супервизии"),
        BotCommand(command="supervision_logbook",  description="Журнал супервизии"),
        BotCommand(command="supervision_progress", description="Открытые случаи"),
    ])

    # Register consent middleware globally — fires before every message/callback
    dp.message.middleware(ConsentMiddleware())
    dp.callback_query.middleware(ConsentMiddleware())

    for r in routers:
        dp.include_router(r)

    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
