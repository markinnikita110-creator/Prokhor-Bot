"""Individual client sessions: list, create (one-off + recurring), edit, delete."""
import logging
from datetime import datetime, timedelta

import aiosqlite
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from database import DB_PATH
from keyboards import (
    client_session_list_keyboard,
    client_session_detail_keyboard,
    client_ind_recurring_days_keyboard,
)
from states.session_states import (
    IndividualSessionRecurringForm,
    IndividualSessionEditForm,
    IndividualOneOffForm,
)
from translations import t

log = logging.getLogger(__name__)
router = Router(name="client_sessions")

_DOW_KEYS = ["dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"]


# ── DB helpers ─────────────────────────────────────────────────────────────

async def _get_user_lang(psych_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT lang FROM psychologists WHERE telegram_id = ?", (psych_id,))
        row = await cur.fetchone()
    return (row[0] if row else None) or "en"


async def _get_user_tz_offset(psych_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT tz_offset FROM psychologists WHERE telegram_id = ?", (psych_id,))
        row = await cur.fetchone()
    return (row[0] if row else None) or 0


def _utc_to_local(dt_utc_str: str, offset_min: int) -> str:
    dt = datetime.strptime(dt_utc_str, "%Y-%m-%d %H:%M") + timedelta(minutes=offset_min)
    return dt.strftime("%Y-%m-%d %H:%M")


def _local_to_utc(dt_local_str: str, offset_min: int) -> str:
    dt = datetime.strptime(dt_local_str, "%Y-%m-%d %H:%M") - timedelta(minutes=offset_min)
    return dt.strftime("%Y-%m-%d %H:%M")


async def _get_client_by_id(client_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, psychologist_id, name, recurring_paused FROM clients WHERE id = ?",
            (client_id,))
        return await cur.fetchone()


async def _get_client_by_name(psych_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, psychologist_id, name, recurring_paused FROM clients "
            "WHERE psychologist_id = ? AND name = ?",
            (psych_id, name))
        return await cur.fetchone()


async def _get_sessions_for_client(psych_id: int, client_name: str) -> list:
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, scheduled_at, topic, link, recurring, days_of_week "
            "FROM sessions "
            "WHERE psychologist_id = ? AND client_name = ? "
            "AND (recurring = 1 OR scheduled_at >= ?) "
            "ORDER BY recurring DESC, scheduled_at ASC",
            (psych_id, client_name, now_str))
        return await cur.fetchall()


async def _get_session(session_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, psychologist_id, client_name, scheduled_at, "
            "topic, link, recurring, days_of_week "
            "FROM sessions WHERE id = ?",
            (session_id,))
        return await cur.fetchone()


def _format_session_label(sess, offset_min: int, lang: str) -> str:
    sid, sched_utc, topic, link, recurring, dow = sess
    if recurring:
        dow_labels = [t(lang, _DOW_KEYS[int(d)])
                      for d in (dow or "").split(",") if d.strip()]
        label = "🔁 " + "/".join(dow_labels) if dow_labels else "🔁 ?"
        if topic:
            label += f" · {topic[:20]}"
        return label
    local = _utc_to_local(sched_utc, offset_min)
    try:
        dt = datetime.strptime(local, "%Y-%m-%d %H:%M")
        label = dt.strftime("%d %b %H:%M")
    except ValueError:
        label = local
    if topic:
        label += f" · {topic[:20]}"
    return label


# ── Generate upcoming sessions inline (used after recurring setup) ─────────

async def _generate_upcoming(psych_id: int, client_name: str,
                              selected_days: list, time_local: str,
                              offset_min: int, topic: str, link: str):
    now = datetime.utcnow()
    horizon = now + timedelta(days=30)
    check_date = now.date()
    async with aiosqlite.connect(DB_PATH) as db:
        while check_date <= horizon.date():
            if check_date.weekday() in selected_days:
                local_dt_str = f"{check_date.strftime('%Y-%m-%d')} {time_local}"
                utc_str = _local_to_utc(local_dt_str, offset_min)
                dt_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M")
                if dt_utc > now:
                    cur = await db.execute(
                        "SELECT 1 FROM sessions WHERE psychologist_id = ? "
                        "AND client_name = ? AND scheduled_at = ? AND recurring = 0",
                        (psych_id, client_name, utc_str))
                    if not await cur.fetchone():
                        await db.execute(
                            "INSERT INTO sessions "
                            "(psychologist_id, client_name, scheduled_at, topic, link) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (psych_id, client_name, utc_str, topic, link))
            check_date += timedelta(days=1)
        await db.commit()


# ── Sessions list ──────────────────────────────────────────────────────────

async def _show_sessions_list(msg_or_cb, psych_id: int, client_id: int,
                               lang: str, offset: int, edit: bool = True):
    client = await _get_client_by_id(client_id)
    if not client:
        if isinstance(msg_or_cb, CallbackQuery):
            await msg_or_cb.answer("Client not found.")
        return
    _, _, client_name, _ = client
    sessions = await _get_sessions_for_client(psych_id, client_name)
    session_rows = [(_format_session_label(s, offset, lang), s[0]) for s in sessions]
    has_recurring = any(s[4] == 1 for s in sessions)
    kb = client_session_list_keyboard(session_rows, client_id, has_recurring, lang)
    text = (t(lang, "is_sessions_title", client=client_name) if sessions
            else t(lang, "is_sessions_empty", client=client_name))
    if isinstance(msg_or_cb, CallbackQuery):
        if edit:
            await msg_or_cb.message.edit_text(text, reply_markup=kb)
        else:
            await msg_or_cb.message.answer(text, reply_markup=kb)
    else:
        await msg_or_cb.answer(text, reply_markup=kb)


async def _show_session_detail_msg(cb: CallbackQuery, session_id: int,
                                    psych_id: int, lang: str, offset: int):
    sess = await _get_session(session_id)
    if not sess:
        await cb.answer(t(lang, "is_not_found"))
        return
    sid, s_psych_id, client_name, sched_utc, topic, link, recurring, dow = sess
    client = await _get_client_by_name(s_psych_id, client_name)
    client_id = client[0] if client else 0
    paused_flag = bool(client[3]) if client else False

    local_dt = _utc_to_local(sched_utc, offset)
    try:
        dt = datetime.strptime(local_dt, "%Y-%m-%d %H:%M")
        date_display = dt.strftime("%A, %d %b %Y · %H:%M")
    except ValueError:
        date_display = local_dt

    lines = [t(lang, "is_detail_header", client=client_name),
             t(lang, "is_detail_date", date=date_display)]
    if topic:
        lines.append(t(lang, "is_detail_topic", topic=topic))
    if link:
        lines.append(t(lang, "is_detail_link", link=link))
    if recurring:
        dow_labels = [t(lang, _DOW_KEYS[int(d)])
                      for d in (dow or "").split(",") if d.strip()]
        lines.append(t(lang, "is_detail_recurring", days="/".join(dow_labels)))
        if paused_flag:
            lines.append(t(lang, "is_detail_paused"))

    kb = client_session_detail_keyboard(session_id, client_id, bool(recurring), paused_flag, lang)
    await cb.message.edit_text("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data.regexp(r"^ics_(\d+)$"))
async def show_client_sessions(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    psych_id = cb.from_user.id
    client_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    await _show_sessions_list(cb, psych_id, client_id, lang, offset, edit=True)
    await cb.answer()


# ── Session detail ─────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^isd_(\d+)$"))
async def show_session_detail(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    await _show_session_detail_msg(cb, session_id, psych_id, lang, offset)
    await cb.answer()


# ── Edit date/time ─────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^isdt_(\d+)$"))
async def edit_dt_start(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    await state.set_state(IndividualSessionEditForm.datetime_)
    await state.update_data(session_id=session_id)
    await cb.message.edit_text(t(lang, "is_ask_datetime_new"))
    await cb.answer()


@router.message(StateFilter(IndividualSessionEditForm.datetime_))
async def edit_dt_save(msg: Message, state: FSMContext):
    psych_id = msg.from_user.id
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    try:
        datetime.strptime(msg.text.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        await msg.answer(t(lang, "err_invalid_datetime"))
        return
    data = await state.get_data()
    session_id = data["session_id"]
    utc_str = _local_to_utc(msg.text.strip(), offset)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET scheduled_at = ? WHERE id = ?",
                         (utc_str, session_id))
        await db.commit()
    await state.clear()
    await msg.answer(t(lang, "is_updated_dt"))


# ── Edit topic ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^istp_(\d+)$"))
async def edit_topic_start(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    await state.set_state(IndividualSessionEditForm.topic)
    await state.update_data(session_id=session_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_btn_clear"), callback_data="istpclear")
    ]])
    await cb.message.edit_text(t(lang, "is_ask_topic_new"), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "istpclear", StateFilter(IndividualSessionEditForm.topic))
async def edit_topic_clear(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    lang = await _get_user_lang(psych_id)
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET topic = '' WHERE id = ?", (data["session_id"],))
        await db.commit()
    await state.clear()
    await cb.message.edit_text(t(lang, "is_updated_topic"))
    await cb.answer()


@router.message(StateFilter(IndividualSessionEditForm.topic))
async def edit_topic_save(msg: Message, state: FSMContext):
    psych_id = msg.from_user.id
    lang = await _get_user_lang(psych_id)
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET topic = ? WHERE id = ?",
                         (msg.text.strip(), data["session_id"]))
        await db.commit()
    await state.clear()
    await msg.answer(t(lang, "is_updated_topic"))


# ── Edit link ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^islk_(\d+)$"))
async def edit_link_start(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    await state.set_state(IndividualSessionEditForm.link)
    await state.update_data(session_id=session_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_btn_clear"), callback_data="islkclear")
    ]])
    await cb.message.edit_text(t(lang, "is_ask_link_new"), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "islkclear", StateFilter(IndividualSessionEditForm.link))
async def edit_link_clear(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    lang = await _get_user_lang(psych_id)
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET link = '' WHERE id = ?", (data["session_id"],))
        await db.commit()
    await state.clear()
    await cb.message.edit_text(t(lang, "is_updated_link"))
    await cb.answer()


@router.message(StateFilter(IndividualSessionEditForm.link))
async def edit_link_save(msg: Message, state: FSMContext):
    psych_id = msg.from_user.id
    lang = await _get_user_lang(psych_id)
    data = await state.get_data()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET link = ? WHERE id = ?",
                         (msg.text.strip(), data["session_id"]))
        await db.commit()
    await state.clear()
    await msg.answer(t(lang, "is_updated_link"))


# ── Delete session ─────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^isdl_(\d+)$"))
async def delete_session_ask(cb: CallbackQuery):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    sess = await _get_session(session_id)
    if not sess:
        await cb.answer(t(lang, "is_not_found"))
        return
    local_dt = _utc_to_local(sess[3], offset)
    try:
        dt = datetime.strptime(local_dt, "%Y-%m-%d %H:%M")
        date_display = dt.strftime("%d %b %Y %H:%M")
    except ValueError:
        date_display = local_dt
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_delete_yes"),
                             callback_data=f"isdy_{session_id}"),
        InlineKeyboardButton(text=t(lang, "is_delete_no"),
                             callback_data=f"isd_{session_id}"),
    ]])
    await cb.message.edit_text(t(lang, "is_delete_confirm", date=date_display), reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.regexp(r"^isdy_(\d+)$"))
async def delete_session_confirm(cb: CallbackQuery):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    sess = await _get_session(session_id)
    client_id = 0
    if sess:
        client = await _get_client_by_name(sess[1], sess[2])
        client_id = client[0] if client else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_btn_back_list"),
                             callback_data=f"ics_{client_id}" if client_id else "menu_individual")
    ]])
    await cb.message.edit_text(t(lang, "is_deleted_ok"), reply_markup=kb)
    await cb.answer()


# ── Pause / Resume recurrence ──────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^ispz_(\d+)$"))
async def toggle_pause(cb: CallbackQuery):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    sess = await _get_session(session_id)
    if not sess:
        await cb.answer(t(lang, "is_not_found"))
        return
    _, s_psych_id, client_name, _, _, _, _, _ = sess
    client = await _get_client_by_name(s_psych_id, client_name)
    if not client:
        await cb.answer()
        return
    client_id, _, _, paused = client
    new_paused = 0 if paused else 1
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE clients SET recurring_paused = ? WHERE id = ?",
                         (new_paused, client_id))
        await db.commit()
    alert = (t(lang, "is_paused_ok", client=client_name) if new_paused
             else t(lang, "is_resumed_ok", client=client_name))
    await cb.answer(alert, show_alert=True)
    await _show_session_detail_msg(cb, session_id, psych_id, lang, offset)


# ── Delete recurrence rule ─────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^isrl_(\d+)$"))
async def delete_rule_ask(cb: CallbackQuery):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    sess = await _get_session(session_id)
    if not sess:
        await cb.answer(t(lang, "is_not_found"))
        return
    client_name = sess[2]
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_delrule_yes"),
                             callback_data=f"isry_{session_id}"),
        InlineKeyboardButton(text=t(lang, "is_delrule_no"),
                             callback_data=f"isd_{session_id}"),
    ]])
    await cb.message.edit_text(t(lang, "is_delrule_confirm", client=client_name),
                                reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.regexp(r"^isry_(\d+)$"))
async def delete_rule_confirm(cb: CallbackQuery):
    psych_id = cb.from_user.id
    session_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    sess = await _get_session(session_id)
    client_id = 0
    if sess:
        client = await _get_client_by_name(sess[1], sess[2])
        client_id = client[0] if client else 0
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            if client_id:
                await db.execute("UPDATE clients SET recurring_paused = 0 WHERE id = ?",
                                 (client_id,))
            await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_btn_back_list"),
                             callback_data=f"ics_{client_id}" if client_id else "menu_individual")
    ]])
    await cb.message.edit_text(t(lang, "is_delrule_ok"), reply_markup=kb)
    await cb.answer()


# ── One-off session ────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^isoa_(\d+)$"))
async def add_oneoff_start(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    client_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    client = await _get_client_by_id(client_id)
    if not client:
        await cb.answer()
        return
    await state.set_state(IndividualOneOffForm.datetime_)
    await state.update_data(client_id=client_id, client_name=client[2])
    await cb.message.edit_text(t(lang, "is_ask_datetime"))
    await cb.answer()


@router.message(StateFilter(IndividualOneOffForm.datetime_))
async def add_oneoff_datetime(msg: Message, state: FSMContext):
    psych_id = msg.from_user.id
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    try:
        datetime.strptime(msg.text.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        await msg.answer(t(lang, "err_invalid_datetime"))
        return
    utc_str = _local_to_utc(msg.text.strip(), offset)
    await state.update_data(scheduled_at=utc_str)
    await state.set_state(IndividualOneOffForm.topic)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="isoatopskip")
    ]])
    await msg.answer(t(lang, "is_ask_topic_new"), reply_markup=kb)


@router.callback_query(F.data == "isoatopskip", StateFilter(IndividualOneOffForm.topic))
async def add_oneoff_topic_skip(cb: CallbackQuery, state: FSMContext):
    await state.update_data(topic="")
    await state.set_state(IndividualOneOffForm.link)
    lang = await _get_user_lang(cb.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="isoalnkskip")
    ]])
    await cb.message.edit_text(t(lang, "is_ask_link_new"), reply_markup=kb)
    await cb.answer()


@router.message(StateFilter(IndividualOneOffForm.topic))
async def add_oneoff_topic(msg: Message, state: FSMContext):
    await state.update_data(topic=msg.text.strip())
    await state.set_state(IndividualOneOffForm.link)
    lang = await _get_user_lang(msg.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="isoalnkskip")
    ]])
    await msg.answer(t(lang, "is_ask_link_new"), reply_markup=kb)


@router.callback_query(F.data == "isoalnkskip", StateFilter(IndividualOneOffForm.link))
async def add_oneoff_link_skip(cb: CallbackQuery, state: FSMContext):
    await state.update_data(link="")
    await _save_oneoff(cb, state)


@router.message(StateFilter(IndividualOneOffForm.link))
async def add_oneoff_link(msg: Message, state: FSMContext):
    await state.update_data(link=msg.text.strip())
    await _save_oneoff(msg, state)


async def _save_oneoff(trigger, state: FSMContext):
    is_cb = isinstance(trigger, CallbackQuery)
    psych_id = trigger.from_user.id
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    data = await state.get_data()
    await state.clear()
    client_id = data["client_id"]
    client_name = data["client_name"]
    scheduled_at = data["scheduled_at"]
    topic = data.get("topic", "")
    link = data.get("link", "")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions "
            "(psychologist_id, client_name, scheduled_at, topic, link) "
            "VALUES (?, ?, ?, ?, ?)",
            (psych_id, client_name, scheduled_at, topic, link))
        await db.commit()
    local_dt = _utc_to_local(scheduled_at, offset)
    try:
        dt = datetime.strptime(local_dt, "%Y-%m-%d %H:%M")
        date_display = dt.strftime("%d %b %Y · %H:%M")
    except ValueError:
        date_display = local_dt
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_btn_back_list"),
                             callback_data=f"ics_{client_id}")
    ]])
    text = t(lang, "is_session_created", client=client_name, date=date_display)
    if is_cb:
        await trigger.message.edit_text(text, reply_markup=kb)
        await trigger.answer()
    else:
        await trigger.answer(text, reply_markup=kb)


# ── Recurring session setup ────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^isra_(\d+)$"))
async def add_recurring_start(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    client_id = int(cb.data.split("_")[1])
    lang = await _get_user_lang(psych_id)
    client = await _get_client_by_id(client_id)
    if not client:
        await cb.answer()
        return
    await state.set_state(IndividualSessionRecurringForm.days)
    await state.update_data(client_id=client_id, client_name=client[2], selected_days=[])
    await cb.message.edit_text(
        t(lang, "is_recurring_ask_days"),
        reply_markup=client_ind_recurring_days_keyboard([], lang))
    await cb.answer()


@router.callback_query(F.data.regexp(r"^isrd_(\d+)$"),
                        StateFilter(IndividualSessionRecurringForm.days))
async def toggle_recurring_day(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    lang = await _get_user_lang(psych_id)
    day_idx = int(cb.data.split("_")[1])
    data = await state.get_data()
    selected = list(data.get("selected_days", []))
    if day_idx in selected:
        selected.remove(day_idx)
    else:
        selected.append(day_idx)
    await state.update_data(selected_days=selected)
    await cb.message.edit_reply_markup(
        reply_markup=client_ind_recurring_days_keyboard(selected, lang))
    await cb.answer()


@router.callback_query(F.data == "isrd_done",
                        StateFilter(IndividualSessionRecurringForm.days))
async def recurring_days_done(cb: CallbackQuery, state: FSMContext):
    psych_id = cb.from_user.id
    lang = await _get_user_lang(psych_id)
    data = await state.get_data()
    selected = data.get("selected_days", [])
    if not selected:
        await cb.answer(t(lang, "is_recurring_days_empty"), show_alert=True)
        return
    await state.set_state(IndividualSessionRecurringForm.time_)
    await cb.message.edit_text(t(lang, "is_recurring_ask_time"))
    await cb.answer()


@router.message(StateFilter(IndividualSessionRecurringForm.time_))
async def recurring_time(msg: Message, state: FSMContext):
    psych_id = msg.from_user.id
    lang = await _get_user_lang(psych_id)
    try:
        datetime.strptime(msg.text.strip(), "%H:%M")
    except ValueError:
        await msg.answer(t(lang, "err_invalid_time"))
        return
    await state.update_data(time_local=msg.text.strip())
    await state.set_state(IndividualSessionRecurringForm.topic)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="isrtopskip")
    ]])
    await msg.answer(t(lang, "is_ask_topic_new"), reply_markup=kb)


@router.callback_query(F.data == "isrtopskip",
                        StateFilter(IndividualSessionRecurringForm.topic))
async def recurring_topic_skip(cb: CallbackQuery, state: FSMContext):
    await state.update_data(topic="")
    await state.set_state(IndividualSessionRecurringForm.link)
    lang = await _get_user_lang(cb.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="isrlnkskip")
    ]])
    await cb.message.edit_text(t(lang, "is_ask_link_new"), reply_markup=kb)
    await cb.answer()


@router.message(StateFilter(IndividualSessionRecurringForm.topic))
async def recurring_topic(msg: Message, state: FSMContext):
    await state.update_data(topic=msg.text.strip())
    await state.set_state(IndividualSessionRecurringForm.link)
    lang = await _get_user_lang(msg.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_skip"), callback_data="isrlnkskip")
    ]])
    await msg.answer(t(lang, "is_ask_link_new"), reply_markup=kb)


@router.callback_query(F.data == "isrlnkskip",
                        StateFilter(IndividualSessionRecurringForm.link))
async def recurring_link_skip(cb: CallbackQuery, state: FSMContext):
    await state.update_data(link="")
    await _save_recurring(cb, state)


@router.message(StateFilter(IndividualSessionRecurringForm.link))
async def recurring_link(msg: Message, state: FSMContext):
    await state.update_data(link=msg.text.strip())
    await _save_recurring(msg, state)


async def _save_recurring(trigger, state: FSMContext):
    is_cb = isinstance(trigger, CallbackQuery)
    psych_id = trigger.from_user.id
    lang = await _get_user_lang(psych_id)
    offset = await _get_user_tz_offset(psych_id)
    data = await state.get_data()
    await state.clear()
    client_id = data["client_id"]
    client_name = data["client_name"]
    selected_days = sorted(data.get("selected_days", []))
    time_local = data["time_local"]
    topic = data.get("topic", "")
    link = data.get("link", "")

    today = datetime.utcnow().date()
    utc_template = _local_to_utc(f"{today.strftime('%Y-%m-%d')} {time_local}", offset)
    days_csv = ",".join(str(d) for d in selected_days)
    dow_labels = [t(lang, _DOW_KEYS[d]) for d in selected_days]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM sessions WHERE psychologist_id = ? AND client_name = ? AND recurring = 1",
            (psych_id, client_name))
        await db.execute(
            "INSERT INTO sessions "
            "(psychologist_id, client_name, scheduled_at, topic, link, recurring, days_of_week) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (psych_id, client_name, utc_template, topic, link, days_csv))
        await db.execute("UPDATE clients SET recurring_paused = 0 WHERE id = ?", (client_id,))
        await db.commit()

    await _generate_upcoming(psych_id, client_name, selected_days,
                              time_local, offset, topic, link)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "is_btn_back_list"),
                             callback_data=f"ics_{client_id}")
    ]])
    text = t(lang, "is_recurring_created",
             client=client_name, days="/".join(dow_labels), time=time_local)
    if is_cb:
        await trigger.message.edit_text(text, reply_markup=kb)
        await trigger.answer()
    else:
        await trigger.answer(text, reply_markup=kb)
