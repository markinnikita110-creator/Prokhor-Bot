"""Check-ins: send, auto, history — for psychologists and clients."""

import logging

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    DB_PATH,
    find_connected_client,
    get_client_lang,
    get_user_lang,
    get_user_timezone,
    now_str,
    resolve_client,
    to_user_tz,
)
from keyboards import (
    cancel_keyboard,
    checkin_score_keyboard,
    checkins_section_keyboard,
)
from states.note_states import AddCheckinForm
from translations import t

router = Router()
log = logging.getLogger(__name__)


# ── Section callback ───────────────────────────────────────────────────────
@router.callback_query(F.data == "m_checkins")
async def checkins_section(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "section_checkins"),
                                         reply_markup=checkins_section_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "section_checkins"),
                                      reply_markup=checkins_section_keyboard(lang))


# ── ci_send → ask which client to send check-in to ────────────────────────
@router.callback_query(F.data == "ci_send")
async def ci_send_start(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(lang=lang, mode="send")
    await state.set_state(AddCheckinForm.client_name)
    await callback.message.answer(t(lang, "ask_checkin_client"), reply_markup=cancel_keyboard(lang))


@router.message(AddCheckinForm.client_name)
async def ci_got_client(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "en")
    mode = data.get("mode", "send")
    client_name = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        row = await cur.fetchone()

    if not row:
        await state.clear()
        await message.answer(t(lang, "client_not_found", name=client_name))
        return

    client_id, client_tg = row

    if mode == "send":
        await state.clear()
        if not client_tg:
            await message.answer(t(lang, "client_not_connected_tg"))
            return
        c_lang = await get_client_lang(client_tg)
        await bot.send_message(client_tg, t(c_lang, "checkin_question"),
                               reply_markup=checkin_score_keyboard(client_id))
        await message.answer(t(lang, "checkin_request_sent", client=client_name))
    else:
        # Manual score entry (for psychologist recording a check-in)
        await state.update_data(client_id=client_id, client_name=client_name)
        await state.set_state(AddCheckinForm.score)
        await message.answer("Score (1-10):", reply_markup=cancel_keyboard(lang))


@router.message(AddCheckinForm.score)
async def ci_got_score(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_id = data["client_id"]
    client_name = data["client_name"]
    await state.clear()
    try:
        score = int(message.text.strip())
        if not (1 <= score <= 10):
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "score_invalid"))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checkins (client_id, score, auto, timestamp) VALUES (?, ?, 0, ?)",
            (client_id, score, now_str())
        )
        await db.commit()
    await message.answer(t(lang, "checkin_saved", client=client_name, score=score))


# ── ci_auto → quick info about auto check-ins ─────────────────────────────
@router.callback_query(F.data == "ci_auto")
async def ci_auto_info(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, interval_min FROM auto_checkins WHERE psychologist_id = ?",
            (callback.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        text = t(lang, "no_auto_checkins")
    else:
        lines = [f"• {name}: every {mins} min" for name, mins in rows]
        text = "Auto check-ins:\n" + "\n".join(lines)
    try:
        await callback.message.edit_text(text, reply_markup=checkins_section_keyboard(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=checkins_section_keyboard(lang))


# ── ci_recent → last 10 check-ins across all clients ──────────────────────
@router.callback_query(F.data == "ci_recent")
async def ci_recent(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, ci.score, ci.timestamp FROM checkins ci "
            "JOIN clients c ON c.id = ci.client_id "
            "WHERE c.psychologist_id = ? AND ci.score > 0 "
            "ORDER BY ci.timestamp DESC LIMIT 10",
            (callback.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        text = t(lang, "no_recent_checkins")
    else:
        tz_name, _ = await get_user_timezone(callback.from_user.id)
        lines = [
            f"• {name}: {score}/10  ({to_user_tz(ts, tz_name)})"
            for name, score, ts in rows
        ]
        text = t(lang, "recent_checkins_title") + "\n" + "\n".join(lines)
    try:
        await callback.message.edit_text(text, reply_markup=checkins_section_keyboard(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=checkins_section_keyboard(lang))


# ── checkin_{client_id}_{score} → client presses score button ─────────────
@router.callback_query(F.data.regexp(r"^checkin_\d+_\d+$"))
async def checkin_score_callback(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    client_id, score = int(parts[1]), int(parts[2])
    c_lang = await get_client_lang(callback.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checkins (client_id, score, auto, timestamp) VALUES (?, ?, 0, ?)",
            (client_id, score, now_str())
        )
        cur = await db.execute(
            "SELECT name, psychologist_id FROM clients WHERE id = ?", (client_id,)
        )
        row = await cur.fetchone()
        await db.commit()
    await callback.answer(t(c_lang, "checkin_thanks"))
    if row:
        client_name, psych_id = row
        p_lang = await get_user_lang(psych_id)
        await bot.send_message(psych_id,
            t(p_lang, "checkin_submitted", client=client_name, score=score))
    log.info("Client check-in: client_id=%d score=%d", client_id, score)


# ── Legacy slash commands ──────────────────────────────────────────────────

@router.message(Command("checkin"))
async def checkin_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /checkin <client> <score 1-10>")
        return
    client_name = args[1].strip()
    try:
        score = int(args[2].strip())
        if not (1 <= score <= 10):
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "score_invalid"))
        return
    client_id = await resolve_client(message.from_user.id, client_name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO checkins (client_id, score, auto, timestamp) VALUES (?, ?, 0, ?)",
            (client_id, score, now_str())
        )
        await db.commit()
    await message.answer(t(lang, "checkin_saved", client=client_name, score=score))


@router.message(Command("checkins"))
async def checkins_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /checkins <client>")
        return
    name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT score, timestamp FROM checkins WHERE client_id = ? ORDER BY id DESC LIMIT 5",
            (client_id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_checkins", client=name))
        return
    tz_name, _ = await get_user_timezone(message.from_user.id)
    lines = [f"- {sc}/10  ({to_user_tz(ts, tz_name)})" for sc, ts in rows]
    await message.answer(t(lang, "checkins_title", client=name) + "\n" + "\n".join(lines))


@router.message(Command("send_checkin"))
async def send_checkin_cmd(message: Message, bot: Bot):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /send_checkin <client>")
        return
    name = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name)
        )
        row = await cur.fetchone()
    if not row:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    client_id, client_tg = row
    if not client_tg:
        await message.answer(t(lang, "client_not_connected_tg"))
        return
    c_lang = await get_client_lang(client_tg)
    await bot.send_message(client_tg, t(c_lang, "checkin_question"),
                           reply_markup=checkin_score_keyboard(client_id))
    await message.answer(t(lang, "checkin_request_sent", client=name))


@router.message(Command("auto_checkin"))
async def auto_checkin_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /auto_checkin <client> <interval_minutes>")
        return
    client_name = args[1].strip()
    try:
        interval = int(args[2].strip())
        if interval <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "interval_invalid"))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO auto_checkins (psychologist_id, client_name, interval_min, last_sent) "
            "VALUES (?, ?, ?, NULL) "
            "ON CONFLICT(psychologist_id, client_name) "
            "DO UPDATE SET interval_min = excluded.interval_min, last_sent = NULL",
            (message.from_user.id, client_name, interval)
        )
        await db.commit()
    await message.answer(t(lang, "auto_checkin_enabled", client=client_name, interval=interval))


@router.message(Command("run_auto_checkins"))
async def run_auto_checkins_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name FROM auto_checkins WHERE psychologist_id = ?",
            (message.from_user.id,)
        )
        configs = await cur.fetchall()
    if not configs:
        await message.answer(t(lang, "no_auto_checkins"))
        return
    timestamp = now_str()
    count = 0
    for (client_name,) in configs:
        client_id = await resolve_client(message.from_user.id, client_name)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO checkins (client_id, score, auto, timestamp) VALUES (?, 0, 1, ?)",
                (client_id, timestamp)
            )
            await db.execute(
                "UPDATE auto_checkins SET last_sent = ? WHERE psychologist_id = ? AND client_name = ?",
                (timestamp, message.from_user.id, client_name)
            )
            await db.commit()
        count += 1
    await message.answer(t(lang, "auto_checkins_done", count=count))


@router.message(Command("remind"))
async def remind_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /remind <client> <minutes>")
        return
    client_name = args[1].strip()
    try:
        minutes = int(args[2].strip())
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "minutes_invalid"))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reminders (psychologist_id, client_name, time_minutes) VALUES (?, ?, ?)",
            (message.from_user.id, client_name, minutes)
        )
        await db.commit()
    await message.answer(t(lang, "reminder_set", client=client_name, minutes=minutes))


@router.message(Command("reminders"))
async def reminders_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, time_minutes FROM reminders WHERE psychologist_id = ?",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_reminders"))
        return
    lines = [f"- {c} in {m} min" for c, m in rows]
    await message.answer(t(lang, "reminders_title") + "\n" + "\n".join(lines))


@router.message(Command("checkin_history"))
async def checkin_history_cmd(message: Message):
    client_row = await find_connected_client(message.from_user.id)
    if not client_row:
        await message.answer(t("en", "not_a_client"))
        return
    client_id, _, _ = client_row
    lang = await get_client_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT score, timestamp FROM checkins "
            "WHERE client_id = ? AND score > 0 ORDER BY id DESC LIMIT 10",
            (client_id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_my_checkins"))
        return
    lines = [f"- {sc}/10  ({ts})" for sc, ts in rows]
    await message.answer(t(lang, "my_checkins_title") + "\n" + "\n".join(lines))
