"""Session management: schedule, list, card, cancel, reschedule."""

import logging
from datetime import datetime

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import (
    DB_PATH, format_offset,
    local_to_utc, now_utc, to_user_tz, utc_to_local,
)
from core.db.users_repository import get_user_lang, get_user_timezone
from core.db.clients_repository import get_client_lang, get_client_timezone
from core.services.sessions import (
    confirm_reschedule,
    delete_session,
    get_session_card,
    get_session_client_and_time,
    get_session_for_reschedule_confirm,
    get_session_psych_and_client,
    get_upcoming_sessions,
    insert_session,
    propose_reschedule,
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
    await insert_session(psych_id, client_name, utc_dt_str)
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
    psych_tz, _ = await get_user_timezone(callback.from_user.id)
    await callback.answer()
    sessions_raw = await get_upcoming_sessions(callback.from_user.id, now)
    sessions = [(sid, name, to_user_tz(dt, psych_tz, "%Y-%m-%d %H:%M")) for sid, name, dt in sessions_raw]
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
    row = await get_session_card(session_id, callback.from_user.id)
    if not row:
        await callback.message.answer(t(lang, "session_not_found"))
        return
    client_name, scheduled_at_utc, booking_status, proposed_utc = row
    psych_tz, _ = await get_user_timezone(callback.from_user.id)
    scheduled_local = to_user_tz(scheduled_at_utc, psych_tz, "%Y-%m-%d %H:%M")
    text = t(lang, "session_row", id=session_id, client=client_name, date=scheduled_local)
    # Show status badge for non-confirmed sessions
    if booking_status == "pending_client" and proposed_utc:
        proposed_local = to_user_tz(proposed_utc, psych_tz, "%Y-%m-%d %H:%M")
        text = f"{text}\n\n{t(lang, 'session_pending_client_badge')}\n📅 → {proposed_local}"
    elif booking_status == "pending_psych":
        text = f"{text}\n\n{t(lang, 'session_pending_psych_badge')}"
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
    row = await get_session_client_and_time(session_id, callback.from_user.id)
    if not row:
        await callback.message.answer(t(lang, "session_not_found"))
        return
    client_name, scheduled_at_utc = row
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (callback.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
    await delete_session(session_id)
    if client_row and client_row[0]:
        c_lang = await get_client_lang(client_row[0])
        c_tz, _ = await get_client_timezone(client_row[0])
        client_local = to_user_tz(scheduled_at_utc, c_tz, "%Y-%m-%d %H:%M")
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

    row = await get_session_client_and_time(session_id, message.from_user.id)
    if not row:
        await message.answer(t(lang, "session_not_found"))
        return
    client_name, old_utc_str = row
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id, timezone FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
    # Propose reschedule: write new time without moving scheduled_at yet
    await propose_reschedule(session_id, utc_dt_str)

    await message.answer(
        t(lang, "session_reschedule_proposed", client=client_name))

    if client_row and client_row[0]:
        client_tg, client_tz = client_row
        c_lang = await get_client_lang(client_tg)
        old_display = to_user_tz(old_utc_str, client_tz, "%d.%m.%Y %H:%M")
        new_display = to_user_tz(utc_dt_str, client_tz, "%d.%m.%Y %H:%M")
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(c_lang, "btn_rsc_confirm"),
                callback_data=f"bkc_rsc_confirm_{session_id}"),
            InlineKeyboardButton(
                text=t(c_lang, "btn_rsc_contact"),
                callback_data=f"bkc_rsc_contact_{session_id}"),
        ]])
        try:
            await bot.send_message(
                client_tg,
                t(c_lang, "booking_reschedule_propose_client",
                  old_datetime=old_display, new_datetime=new_display),
                parse_mode="Markdown",
                reply_markup=kb)
        except Exception as e:
            log.warning("RSC: notify client failed session_id=%d: %s", session_id, e)


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
    psych_tz, _ = await get_user_timezone(message.from_user.id)
    rows_raw = await get_upcoming_sessions(message.from_user.id, now)
    rows = [(sid, name, to_user_tz(dt, psych_tz, "%Y-%m-%d %H:%M")) for sid, name, dt in rows_raw]
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
    row = await get_session_client_and_time(session_id, message.from_user.id)
    if not row:
        await message.answer(t(lang, "session_not_found"))
        return
    client_name, scheduled_at_utc = row
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
    await delete_session(session_id)
    if client_row and client_row[0]:
        c_lang = await get_client_lang(client_row[0])
        c_tz, _ = await get_client_timezone(client_row[0])
        client_local = to_user_tz(scheduled_at_utc, c_tz, "%Y-%m-%d %H:%M")
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
    row = await get_session_client_and_time(session_id, message.from_user.id)
    if not row:
        await message.answer(t(lang, "session_not_found"))
        return
    client_name, old_utc_str = row
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id, timezone FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, client_name)
        )
        client_row = await cur.fetchone()
    await propose_reschedule(session_id, utc_dt_str)
    await message.answer(
        t(lang, "session_reschedule_proposed", client=client_name))
    if client_row and client_row[0]:
        client_tg, client_tz = client_row
        c_lang = await get_client_lang(client_tg)
        old_display = to_user_tz(old_utc_str, client_tz, "%d.%m.%Y %H:%M")
        new_display = to_user_tz(utc_dt_str, client_tz, "%d.%m.%Y %H:%M")
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(c_lang, "btn_rsc_confirm"),
                callback_data=f"bkc_rsc_confirm_{session_id}"),
            InlineKeyboardButton(
                text=t(c_lang, "btn_rsc_contact"),
                callback_data=f"bkc_rsc_contact_{session_id}"),
        ]])
        try:
            await bot.send_message(
                client_tg,
                t(c_lang, "booking_reschedule_propose_client",
                  old_datetime=old_display, new_datetime=new_display),
                parse_mode="Markdown",
                reply_markup=kb)
        except Exception as e:
            log.warning("RSC_CMD: notify client failed session_id=%d: %s", session_id, e)


# ── bkc_rsc_confirm_{id} — client confirms psychologist's reschedule ────────

@router.callback_query(F.data.regexp(r"^bkc_rsc_confirm_\d+$"))
async def bkc_rsc_confirm_cb(callback: CallbackQuery, bot: Bot):
    """Client accepts the psychologist's proposed new session time."""
    session_id = int(callback.data.split("_")[3])
    uid = callback.from_user.id
    c_lang = await get_client_lang(uid)
    await callback.answer()

    row = await get_session_for_reschedule_confirm(session_id)
    if not row:
        return
    psych_id, client_name, old_utc, proposed_utc, status = row
    if status != "pending_client" or not proposed_utc:
        # Already confirmed (double tap) — silent ignore
        return
    # Commit the new time: move proposed → scheduled_at, reset reminders
    await confirm_reschedule(session_id, proposed_utc)

    # Confirm to client
    c_tz, _ = await get_client_timezone(uid)
    new_display = to_user_tz(proposed_utc, c_tz, "%d.%m.%Y %H:%M")
    try:
        await callback.message.edit_text(
            t(c_lang, "booking_rsc_confirmed_client", datetime=new_display),
            reply_markup=None)
    except Exception:
        await callback.message.answer(
            t(c_lang, "booking_rsc_confirmed_client", datetime=new_display))

    # Notify psychologist
    p_lang = await get_user_lang(psych_id)
    p_tz, _ = await get_user_timezone(psych_id)
    p_display = to_user_tz(proposed_utc, p_tz, "%d.%m.%Y %H:%M")
    try:
        await bot.send_message(
            psych_id,
            t(p_lang, "booking_rsc_confirmed_psych",
              client=client_name, datetime=p_display))
    except Exception as e:
        log.warning("bkc_rsc_confirm: psych notify failed: %s", e)

    log.info("RSC: client confirmed reschedule session_id=%d new_utc=%s", session_id, proposed_utc)


# ── bkc_rsc_contact_{id} — client signals they can't make the new time ──────

@router.callback_query(F.data.regexp(r"^bkc_rsc_contact_\d+$"))
async def bkc_rsc_contact_cb(callback: CallbackQuery, bot: Bot):
    """Client cannot make the proposed time — notify psychologist to get in touch."""
    session_id = int(callback.data.split("_")[3])
    uid = callback.from_user.id
    await callback.answer()

    row = await get_session_psych_and_client(session_id)
    if not row:
        return
    psych_id, client_name = row

    # Remove buttons so client can't tap again
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    p_lang = await get_user_lang(psych_id)
    try:
        await bot.send_message(
            psych_id,
            t(p_lang, "booking_rsc_contact_psych", client=client_name))
    except Exception as e:
        log.warning("bkc_rsc_contact: psych notify failed: %s", e)

    log.info("RSC: client requested contact session_id=%d", session_id)
