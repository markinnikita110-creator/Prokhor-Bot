"""Session management: schedule, list, card, cancel, reschedule."""

import logging
from datetime import datetime

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    DB_PATH, format_offset, get_client_lang, get_client_timezone,
    get_user_lang, get_user_timezone, local_to_utc, now_utc, utc_to_local,
)
from keyboards import (
    cancel_keyboard,
    session_card_keyboard,
    session_list_keyboard,
    sessions_section_keyboard,
)
from states.session_states import (
    RescheduleForm,
    ScheduleSessionForm,
    ScheduleSessionFromCardForm,
)
from translations import t

router = Router()
log = logging.getLogger(__name__)


# ── s_add → start ScheduleSessionForm (from menu, asks client name first) ──
@router.callback_query(F.data == "s_add")
async def s_add_start(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(lang=lang)
    await state.set_state(ScheduleSessionForm.client_name)
    await callback.message.answer(t(lang, "ask_client_name"), reply_markup=cancel_keyboard(lang))


@router.message(ScheduleSessionForm.client_name)
async def sched_got_client(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(client_name=message.text.strip())
    await state.set_state(ScheduleSessionForm.datetime_str)
    await message.answer(t(lang, "ask_session_datetime"), reply_markup=cancel_keyboard(lang))


@router.message(ScheduleSessionForm.datetime_str)
async def sched_got_dt(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_name = data["client_name"]
    dt_str = message.text.strip()
    try:
        session_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    await state.clear()
    await _save_session(message.from_user.id, client_name, dt_str, lang, message)


# ── From client card: datetime only (client pre-set in FSM data) ───────────
@router.message(ScheduleSessionFromCardForm.datetime_str)
async def sched_card_got_dt(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_name = data.get("client_name", "")
    dt_str = message.text.strip()
    try:
        datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    await state.clear()
    await _save_session(message.from_user.id, client_name, dt_str, lang, message)


async def _save_session(psych_id: int, client_name: str, local_dt_str: str, lang: str, message: Message):
    """local_dt_str is in the psychologist's local timezone; stored as UTC in the DB."""
    _, psych_offset = await get_user_timezone(psych_id)
    utc_dt_str = local_to_utc(local_dt_str, psych_offset)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (psychologist_id, client_name, scheduled_at) VALUES (?, ?, ?)",
            (psych_id, client_name, utc_dt_str)
        )
        await db.commit()
    offset_label = format_offset(psych_offset)
    tz_info = t(lang, "tz_info", offset=offset_label)
    await message.answer(t(lang, "session_scheduled", client=client_name,
                           date=local_dt_str, tz_info=tz_info))
    log.info("Session scheduled: psych=%d client=%s local=%s utc=%s",
             psych_id, client_name, local_dt_str, utc_dt_str)


# ── sl_{page} → upcoming session list ─────────────────────────────────────
@router.callback_query(F.data.regexp(r"^sl_\d+$"))
async def session_list_cb(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    page = int(callback.data.split("_")[1])
    now = now_utc()
    _, psych_offset = await get_user_timezone(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, client_name, scheduled_at FROM sessions "
            "WHERE psychologist_id = ? AND scheduled_at >= ? ORDER BY scheduled_at",
            (callback.from_user.id, now)
        )
        sessions_raw = await cur.fetchall()
    sessions = [(sid, name, utc_to_local(dt, psych_offset)) for sid, name, dt in sessions_raw]
    if not sessions:
        try:
            await callback.message.edit_text(t(lang, "no_sessions"),
                                             reply_markup=sessions_section_keyboard(lang))
        except Exception:
            await callback.message.answer(t(lang, "no_sessions"),
                                          reply_markup=sessions_section_keyboard(lang))
        return
    try:
        await callback.message.edit_text(
            t(lang, "sessions_title"),
            reply_markup=session_list_keyboard(sessions, page, lang))
    except Exception:
        await callback.message.answer(
            t(lang, "sessions_title"),
            reply_markup=session_list_keyboard(sessions, page, lang))


# ── sc_{id} → session card ─────────────────────────────────────────────────
@router.callback_query(F.data.regexp(r"^sc_\d+$"))
async def session_card_cb(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    session_id = int(callback.data.split("_")[1])
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, callback.from_user.id)
        )
        row = await cur.fetchone()
    if not row:
        await callback.message.answer(t(lang, "session_not_found"))
        return
    client_name, scheduled_at_utc = row
    _, psych_offset = await get_user_timezone(callback.from_user.id)
    scheduled_local = utc_to_local(scheduled_at_utc, psych_offset)
    text = t(lang, "session_row", id=session_id, client=client_name, date=scheduled_local)
    try:
        await callback.message.edit_text(text,
            reply_markup=session_card_keyboard(session_id, lang))
    except Exception:
        await callback.message.answer(text,
            reply_markup=session_card_keyboard(session_id, lang))


# ── sa_{id}_can → cancel session ──────────────────────────────────────────
@router.callback_query(F.data.regexp(r"^sa_\d+_can$"))
async def session_cancel_cb(callback: CallbackQuery, bot: Bot):
    lang = await get_user_lang(callback.from_user.id)
    session_id = int(callback.data.split("_")[1])
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, callback.from_user.id)
        )
        row = await cur.fetchone()
        if not row:
            await callback.message.answer(t(lang, "session_not_found"))
            return
        client_name, scheduled_at_utc = row
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (callback.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    if client_row and client_row[0]:
        c_lang = await get_client_lang(client_row[0])
        _, c_offset = await get_client_timezone(client_row[0])
        client_local = utc_to_local(scheduled_at_utc, c_offset)
        await bot.send_message(client_row[0],
            t(c_lang, "session_cancelled_notify", date=client_local))
    try:
        await callback.message.edit_text(t(lang, "session_cancelled", id=session_id),
                                         reply_markup=sessions_section_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "session_cancelled", id=session_id))


# ── sa_{id}_rsc → reschedule: start RescheduleForm ────────────────────────
@router.callback_query(F.data.regexp(r"^sa_\d+_rsc$"))
async def session_reschedule_start(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    session_id = int(callback.data.split("_")[1])
    await callback.answer()
    await state.update_data(session_id=session_id, lang=lang)
    await state.set_state(RescheduleForm.datetime_str)
    await callback.message.answer(t(lang, "ask_reschedule_datetime"),
                                   reply_markup=cancel_keyboard(lang))


@router.message(RescheduleForm.datetime_str)
async def reschedule_got_dt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "en")
    session_id = data["session_id"]
    local_dt_str = message.text.strip()
    try:
        datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    await state.clear()
    _, psych_offset = await get_user_timezone(message.from_user.id)
    utc_dt_str = local_to_utc(local_dt_str, psych_offset)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, message.from_user.id)
        )
        row = await cur.fetchone()
        if not row:
            await message.answer(t(lang, "session_not_found"))
            return
        client_name = row[0]
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
        await db.execute(
            "UPDATE sessions SET scheduled_at = ?, reminded_24h = 0, reminded_1h = 0 WHERE id = ?",
            (utc_dt_str, session_id)
        )
        await db.commit()

    if client_row and client_row[0]:
        c_lang = await get_client_lang(client_row[0])
        _, c_offset = await get_client_timezone(client_row[0])
        client_local = utc_to_local(utc_dt_str, c_offset)
        await bot.send_message(client_row[0],
            t(c_lang, "session_rescheduled_notify", date=client_local))
    await message.answer(t(lang, "session_rescheduled", id=session_id, date=local_dt_str))


# ── Legacy slash commands ──────────────────────────────────────────────────

@router.message(Command("schedule"))
async def schedule_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /schedule <client> <YYYY-MM-DD HH:MM>")
        return
    client_name, dt_str = args[1].strip(), args[2].strip()
    try:
        datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    await _save_session(message.from_user.id, client_name, dt_str, lang, message)


@router.message(Command("sessions"))
async def sessions_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    now = now_utc()
    _, psych_offset = await get_user_timezone(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, client_name, scheduled_at FROM sessions "
            "WHERE psychologist_id = ? AND scheduled_at >= ? ORDER BY scheduled_at",
            (message.from_user.id, now)
        )
        rows_raw = await cur.fetchall()
    rows = [(sid, name, utc_to_local(dt, psych_offset)) for sid, name, dt in rows_raw]
    if not rows:
        await message.answer(t(lang, "no_sessions"))
        return
    lines = [t(lang, "session_row", id=sid, client=c, date=d) for sid, c, d in rows]
    await message.answer(t(lang, "sessions_title") + "\n" + "\n".join(lines))


@router.message(Command("cancel_session"))
async def cancel_session_cmd(message: Message, bot: Bot):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /cancel_session <id>")
        return
    try:
        session_id = int(args[1].strip())
    except ValueError:
        await message.answer(t(lang, "id_invalid"))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, message.from_user.id)
        )
        row = await cur.fetchone()
        if not row:
            await message.answer(t(lang, "session_not_found"))
            return
        client_name, scheduled_at_utc = row
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    if client_row and client_row[0]:
        c_lang = await get_client_lang(client_row[0])
        _, c_offset = await get_client_timezone(client_row[0])
        client_local = utc_to_local(scheduled_at_utc, c_offset)
        await bot.send_message(client_row[0],
            t(c_lang, "session_cancelled_notify", date=client_local))
    await message.answer(t(lang, "session_cancelled", id=session_id))


@router.message(Command("reschedule_session"))
async def reschedule_session_cmd(message: Message, bot: Bot):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /reschedule_session <id> <YYYY-MM-DD HH:MM>")
        return
    try:
        session_id = int(args[1].strip())
    except ValueError:
        await message.answer(t(lang, "id_invalid"))
        return
    local_dt_str = args[2].strip()
    try:
        datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    _, psych_offset = await get_user_timezone(message.from_user.id)
    utc_dt_str = local_to_utc(local_dt_str, psych_offset)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name FROM sessions WHERE id = ? AND psychologist_id = ?",
            (session_id, message.from_user.id)
        )
        row = await cur.fetchone()
        if not row:
            await message.answer(t(lang, "session_not_found"))
            return
        client_name = row[0]
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
        await db.execute(
            "UPDATE sessions SET scheduled_at = ?, reminded_24h = 0, reminded_1h = 0 WHERE id = ?",
            (utc_dt_str, session_id)
        )
        await db.commit()
    if client_row and client_row[0]:
        c_lang = await get_client_lang(client_row[0])
        _, c_offset = await get_client_timezone(client_row[0])
        client_local = utc_to_local(utc_dt_str, c_offset)
        await bot.send_message(client_row[0],
            t(c_lang, "session_rescheduled_notify", date=client_local))
    await message.answer(t(lang, "session_rescheduled", id=session_id, date=local_dt_str))
