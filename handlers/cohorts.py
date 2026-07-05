"""COHORT / COHORT_SESSION / COHORT_V2: Full cohort management handler.

Commands: /cohort_create, /cohorts, /cohort_schedule, /cohort_sessions,
          /cohort_attendance + all cv2_* inline callbacks.
"""

import logging
from datetime import datetime, timedelta

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import (
    DB_PATH,
    get_user_lang,
    get_user_timezone,
    local_to_utc,
    now_str,
    to_user_tz,
    utc_to_local,
)
from core.db.clients_repository import get_cohort_member_lang, get_cohort_member_timezone
from core.services.cohorts import (
    add_member,
    archive_cohort,
    check_add_cohort,
    check_add_cohort_member,
    create_cohort,
    get_active_members,
    get_attendance_for_session,
    get_cohort_by_token,
    get_cohort_for_owner,
    get_cohort_invite_token,
    get_cohort_name,
    get_cohort_status,
    get_cohorts_for_psych,
    get_member_count,
    get_next_manual_id,
    is_member,
    is_recurring_paused,
    seed_attendance_for_session,
    set_recurring_paused,
    upsert_attendance,
    verify_cohort_owner,
)
from keyboards import (
    cancel_keyboard,
    cohort_action_keyboard,
    cohort_clear_field_keyboard,
    cohort_confirm_keyboard,
    cohort_members_keyboard,
    cohort_recurring_days_keyboard,
    cohort_session_detail_keyboard,
    cohort_session_list_keyboard,
    cohort_type_keyboard,
)
from states.cohort_states import (
    CohortAddMemberManualForm,
    CohortAttendanceForm,
    CohortBroadcastForm,
    CohortCheckinSetupForm,
    CohortCreateForm,
    CohortRecurringScheduleForm,
    CohortScheduleForm,
    CohortSessionEditForm,
    CohortSessionNoteForm,
    CohortSOAPNoteForm,
)
from translations import t

from handlers.clients import BOT_USERNAME  # COHORT: bot username for invite links

# RECURRING: display names for weekday indices (0=Mon..6=Sun), keyed to translations.py
_DOW_KEYS = ["dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"]

router = Router()
log = logging.getLogger(__name__)



# ══════════════════════════════════════════════════════════════════════════
# COHORT_SESSION: DB helpers
# ══════════════════════════════════════════════════════════════════════════

async def _create_cohort_session(cohort_id, session_number, scheduled_at_utc, topic, link,
                                  recurring=0, days_of_week=""):
    """COHORT_SESSION / RECURRING: create a session. `recurring`/`days_of_week`
    default to off, so this stays fully backward compatible with one-off sessions."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cohort_sessions "
            "(cohort_id, session_number, scheduled_at, topic, link, status, recurring, days_of_week) "
            "VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?)",
            (cohort_id, session_number, scheduled_at_utc, topic, link, recurring, days_of_week),
        )
        session_id = cur.lastrowid
        await db.commit()
    return session_id



async def _get_cohort_sessions(cohort_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic, link, status "
            "FROM cohort_sessions WHERE cohort_id = ? ORDER BY scheduled_at ASC",
            (cohort_id,),
        )
        return await cur.fetchall()


async def _get_scheduled_sessions(cohort_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic "
            "FROM cohort_sessions "
            "WHERE cohort_id = ? AND status IN ('scheduled', 'completed') "
            "ORDER BY scheduled_at ASC",
            (cohort_id,),
        )
        return await cur.fetchall()



async def _get_cohort_for_session(session_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT cs.cohort_id, c.name, cs.session_number "
            "FROM cohort_sessions cs JOIN cohorts c ON c.id = cs.cohort_id "
            "WHERE cs.id = ?",
            (session_id,),
        )
        return await cur.fetchone()




async def _get_upcoming_sessions(cohort_id: int, days_ahead: int = 45) -> list:
    """SESSIONS: scheduled sessions for a cohort within the next `days_ahead` days."""
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    horizon_utc = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic, link, recurring, days_of_week "
            "FROM cohort_sessions "
            "WHERE cohort_id = ? AND status = 'scheduled' "
            "AND scheduled_at >= ? AND scheduled_at <= ? "
            "ORDER BY scheduled_at ASC",
            (cohort_id, now_utc, horizon_utc),
        )
        return await cur.fetchall()


async def _get_session(session_id: int):
    """SESSIONS: full row for one session, or None if it no longer exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, cohort_id, session_number, scheduled_at, topic, link, status, "
            "recurring, days_of_week FROM cohort_sessions WHERE id = ?",
            (session_id,),
        )
        return await cur.fetchone()


async def _update_session_field(session_id: int, field: str, value: str):
    """SESSIONS: update one editable column (scheduled_at/topic/link) of a session."""
    if field not in ("scheduled_at", "topic", "link"):
        raise ValueError(f"field not editable: {field}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE cohort_sessions SET {field} = ? WHERE id = ?", (value, session_id))
        await db.commit()


async def _delete_cohort_session(session_id: int):
    """SESSIONS: remove a session and its attendance rows."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cohort_attendance WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM cohort_sessions WHERE id = ?", (session_id,))
        await db.commit()



async def _delete_recurring_rule(cohort_id: int):
    """SESSIONS / RECURRING: forget the schedule for a cohort. Already-created
    sessions are kept as-is (just no longer flagged as part of a live rule),
    and the generator will find no more `recurring=1` template to work from."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE cohort_sessions SET recurring = 0, days_of_week = '' "
            "WHERE cohort_id = ? AND recurring = 1",
            (cohort_id,),
        )
        await db.execute("UPDATE cohorts SET recurring_paused = 0 WHERE id = ?", (cohort_id,))
        await db.commit()


# ══════════════════════════════════════════════════════════════════════════
# COHORT_SESSION: Attendance keyboard builder
# ══════════════════════════════════════════════════════════════════════════

async def _attendance_kb(session_id: int, cohort_id: int, lang: str):
    members = await get_active_members(cohort_id)
    if not members:
        return t(lang, "cs_att_no_members"), None
    attendance = await get_attendance_for_session(session_id)
    rows = []
    for member_id, _tg, name in members:
        cur_status = attendance.get(member_id, "pending")
        rows.append([
            InlineKeyboardButton(text=name[:22], callback_data="noop"),
            InlineKeyboardButton(
                text="✅◀" if cur_status == "present" else "✅",
                callback_data=f"catt_mk_{session_id}_{member_id}_present",
            ),
            InlineKeyboardButton(
                text="❌◀" if cur_status == "absent" else "❌",
                callback_data=f"catt_mk_{session_id}_{member_id}_absent",
            ),
            InlineKeyboardButton(
                text="⏳◀" if cur_status == "pending" else "⏳",
                callback_data=f"catt_mk_{session_id}_{member_id}_pending",
            ),
        ])
    return "", InlineKeyboardMarkup(inline_keyboard=rows)


def _cohort_picker_kb(cohorts: list, cb_prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"{cb_prefix}_{cid}")]
        for cid, name, _ in cohorts
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: Check-in score keyboard builder (used in cohorts.py and main.py)
# ══════════════════════════════════════════════════════════════════════════

def _cohort_checkin_kb(cohort_id: int, member_tg: int) -> InlineKeyboardMarkup:
    """COHORT_V2: 1-10 score keyboard for cohort member check-in response."""
    row1 = [
        InlineKeyboardButton(text=str(i), callback_data=f"cci_{cohort_id}_{member_tg}_{i}")
        for i in range(1, 6)
    ]
    row2 = [
        InlineKeyboardButton(text=str(i), callback_data=f"cci_{cohort_id}_{member_tg}_{i}")
        for i in range(6, 11)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


# ══════════════════════════════════════════════════════════════════════════
# COHORT: /cohort_create — FSM wizard
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("cohort_create"))
async def cohort_create_start(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(CohortCreateForm.name)
    await message.answer(t(lang, "cohort_ask_name"), reply_markup=cancel_keyboard(lang))
    log.info("COHORT: create started by user_id=%d", message.from_user.id)


@router.message(CohortCreateForm.name)
async def cohort_got_name(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(name=message.text.strip())
    await state.set_state(CohortCreateForm.description)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_cohort_skip_desc"), callback_data="cohort_skip_desc")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await message.answer(t(lang, "cohort_ask_description"), reply_markup=skip_kb)


@router.callback_query(CohortCreateForm.description, F.data == "cohort_skip_desc")
async def cohort_skip_description(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(description="")
    await state.set_state(CohortCreateForm.max_participants)
    await callback.answer()
    await callback.message.answer(t(lang, "cohort_ask_max"), reply_markup=cancel_keyboard(lang))


@router.message(CohortCreateForm.description)
async def cohort_got_description(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(description=message.text.strip())
    await state.set_state(CohortCreateForm.max_participants)
    await message.answer(t(lang, "cohort_ask_max"), reply_markup=cancel_keyboard(lang))


@router.message(CohortCreateForm.max_participants)
async def cohort_got_max(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    raw = message.text.strip()
    max_p = 12
    if raw:
        try:
            max_p = int(raw)
            if max_p < 1:
                raise ValueError
        except ValueError:
            await message.answer(t(lang, "minutes_invalid"))
            return
    await state.update_data(max_participants=max_p)
    await state.set_state(CohortCreateForm.type_)
    await message.answer(t(lang, "cohort_ask_type"), reply_markup=cohort_type_keyboard(lang))


@router.callback_query(CohortCreateForm.type_, F.data.startswith("cohort_type_"))
async def cohort_got_type(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    uid = callback.from_user.id
    allowed, err_msg = await check_add_cohort(uid, lang=lang)
    if not allowed:
        await state.clear()
        await callback.answer()
        await callback.message.answer(err_msg)
        return
    type_map = {
        "cohort_type_course":      ("course",      t(lang, "btn_cohort_type_course")),
        "cohort_type_group":       ("group",        t(lang, "btn_cohort_type_group")),
        "cohort_type_supervision": ("supervision",  t(lang, "btn_cohort_type_supervision")),
    }
    type_key, type_display = type_map.get(callback.data, ("group", "Group"))
    data = await state.get_data()
    cohort_id, token = await create_cohort(
        uid, data["name"], data.get("description", ""),
        type_key, data.get("max_participants", 12),
    )
    invite_link = f"https://t.me/{BOT_USERNAME}?start=cohort_{token}"
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_created", name=data["name"], type=type_display,
          max=data.get("max_participants", 12), link=invite_link),
        parse_mode="HTML",
    )
    log.info("COHORT: created cohort_id=%d by user_id=%d", cohort_id, uid)


# ══════════════════════════════════════════════════════════════════════════
# COHORT: /cohorts — text list
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("cohorts"))
async def cohorts_list(message: Message):
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    lines = [t(lang, "cohort_list_title")]
    for cid, name, max_p in cohorts:
        count = await get_member_count(cid)
        lines.append(t(lang, "cohort_list_row", name=name, count=count, max=max_p))
    await message.answer("\n".join(lines))


# ══════════════════════════════════════════════════════════════════════════
# COHORT: join confirmation callback
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cohort_join_"))
async def cohort_join_confirm(callback: CallbackQuery):
    uid = callback.from_user.id
    token = callback.data[len("cohort_join_"):]
    lang = await get_user_lang(uid)
    row = await get_cohort_by_token(token)
    if not row:
        await callback.answer(t(lang, "cohort_invalid_token"), show_alert=True)
        return
    cohort_id, psych_id, name, max_p = row
    if psych_id == uid:
        await callback.answer(t(lang, "cohort_is_leader"), show_alert=True)
        return
    if await is_member(cohort_id, uid):
        await callback.answer(t(lang, "cohort_already_member"), show_alert=True)
        return
    if await get_member_count(cohort_id) >= max_p:
        await callback.answer(t(lang, "cohort_full"), show_alert=True)
        return
    allowed, err_msg = await check_add_cohort_member(psych_id, cohort_id, lang=lang)
    if not allowed:
        await callback.answer(err_msg, show_alert=True)
        return
    first_name = callback.from_user.first_name or f"user_{uid}"
    await add_member(cohort_id, uid, first_name)
    await callback.answer()
    await callback.message.answer(t(lang, "cohort_join_confirm", name=name), parse_mode="HTML")
    log.info("COHORT: user_id=%d joined cohort_id=%d", uid, cohort_id)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_SESSION: /cohort_schedule — FSM
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("cohort_schedule"))
async def cohort_schedule_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await state.set_state(CohortScheduleForm.cohort)
    await message.answer(t(lang, "cs_pick_cohort_schedule"),
                         reply_markup=_cohort_picker_kb(cohorts, "csch_coh"))


@router.callback_query(CohortScheduleForm.cohort, F.data.startswith("csch_coh_"))
async def cs_got_cohort(callback: CallbackQuery, state: FSMContext):
    """SESSIONS: session number is auto-assigned (next in sequence) — no manual
    entry required, straight to picking the date/time."""
    lang = await get_user_lang(callback.from_user.id)
    cohort_id = int(callback.data[len("csch_coh_"):])
    existing = await _get_cohort_sessions(cohort_id)
    next_num = max((row[1] for row in existing), default=0) + 1
    await state.update_data(cohort_id=cohort_id, session_number=next_num)
    await state.set_state(CohortScheduleForm.datetime_)
    await callback.answer()
    await callback.message.answer(t(lang, "cs_ask_datetime"), reply_markup=cancel_keyboard(lang))


@router.message(CohortScheduleForm.datetime_)
async def cs_got_datetime(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    uid = message.from_user.id
    raw = message.text.strip()
    try:
        datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    _, p_offset = await get_user_timezone(uid)
    scheduled_at_utc = local_to_utc(raw, p_offset)
    await state.update_data(scheduled_at_utc=scheduled_at_utc, scheduled_at_local=raw)
    await state.set_state(CohortScheduleForm.topic)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="csch_skip_topic")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await message.answer(t(lang, "cs_ask_topic"), reply_markup=skip_kb)


@router.callback_query(CohortScheduleForm.topic, F.data == "csch_skip_topic")
async def cs_skip_topic(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(topic="")
    await state.set_state(CohortScheduleForm.link)
    await callback.answer()
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="csch_skip_link")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await callback.message.answer(t(lang, "cs_ask_link"), reply_markup=skip_kb)


@router.message(CohortScheduleForm.topic)
async def cs_got_topic(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(topic=message.text.strip())
    await state.set_state(CohortScheduleForm.link)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="csch_skip_link")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await message.answer(t(lang, "cs_ask_link"), reply_markup=skip_kb)


@router.callback_query(CohortScheduleForm.link, F.data == "csch_skip_link")
async def cs_skip_link(callback: CallbackQuery, state: FSMContext):
    await state.update_data(link="")
    await _finalize_schedule(callback, state)


@router.message(CohortScheduleForm.link)
async def cs_got_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await _finalize_schedule(message, state)


async def _finalize_schedule(source, state: FSMContext):
    uid = source.from_user.id
    lang = await get_user_lang(uid)
    data = await state.get_data()
    cohort_id = data["cohort_id"]
    session_number = data["session_number"]
    scheduled_at_utc = data["scheduled_at_utc"]
    scheduled_at_local = data["scheduled_at_local"]
    topic = data.get("topic", "")
    link = data.get("link", "")
    session_id = await _create_cohort_session(cohort_id, session_number, scheduled_at_utc, topic, link)
    cohort_name = await get_cohort_name(cohort_id)
    topic_display = topic if topic else t(lang, "cs_no_topic")
    date_display = datetime.strptime(scheduled_at_local, "%Y-%m-%d %H:%M").strftime("%d.%m %H:%M")
    await state.clear()
    reply = t(lang, "cs_created", num=session_number, cohort=cohort_name,
              date=date_display, topic=topic_display)
    if isinstance(source, CallbackQuery):
        await source.answer()
        await source.message.answer(reply)
    else:
        await source.answer(reply)
    log.info("COHORT_SESSION: created session_id=%d cohort_id=%d num=%d by user_id=%d",
             session_id, cohort_id, session_number, uid)


# ══════════════════════════════════════════════════════════════════════════
# RECURRING: generator — creates upcoming occurrences for the next 30 days
# ══════════════════════════════════════════════════════════════════════════

async def generate_recurring_cohort_sessions(cohort_id: int = None) -> int:
    """RECURRING: for every cohort with a recurring session schedule, create
    missing occurrences on the matching weekdays for the next 30 days.

    Called once/day from `reminder_loop()` in main.py, and once immediately
    after a psychologist sets up a new recurring schedule (via `cohort_id=`)
    so the horizon is filled in right away instead of waiting for the next
    daily tick.

    For each cohort the most recently created recurring session (highest id)
    acts as the template: its time-of-day, topic, link and days_of_week are
    reused for every generated occurrence. Dates that already have a session
    are skipped, so this is safe to call repeatedly (idempotent).
    """
    today = datetime.utcnow().date()
    horizon = today + timedelta(days=30)

    query = (
        "SELECT cs.cohort_id, MAX(cs.id) "
        "FROM cohort_sessions cs JOIN cohorts c ON c.id = cs.cohort_id "
        "WHERE cs.recurring = 1 AND c.status != 'archived' "
        "AND COALESCE(c.recurring_paused, 0) = 0 "
    )
    params: tuple = ()
    if cohort_id is not None:
        query += "AND cs.cohort_id = ? "
        params = (cohort_id,)
    query += "GROUP BY cs.cohort_id"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        rule_rows = await cur.fetchall()

    total_created = 0
    for c_id, last_id in rule_rows:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT session_number, scheduled_at, topic, link, days_of_week "
                "FROM cohort_sessions WHERE id = ?",
                (last_id,),
            )
            row = await cur.fetchone()
        if not row:
            continue
        last_num, sched_str, topic, link, days_csv = row
        if not days_csv:
            continue
        try:
            days = {int(d) for d in days_csv.split(",") if d.strip() != ""}
        except ValueError:
            continue
        if not days:
            continue
        try:
            time_part = datetime.strptime(sched_str, "%Y-%m-%d %H:%M").strftime("%H:%M")
        except ValueError:
            continue

        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT scheduled_at FROM cohort_sessions WHERE cohort_id = ?",
                (c_id,),
            )
            existing_dates = {r[0].split(" ")[0] for r in await cur.fetchall()}

        next_num = last_num
        day_cursor = today
        while day_cursor <= horizon:
            if day_cursor.weekday() in days:
                date_str = day_cursor.strftime("%Y-%m-%d")
                if date_str not in existing_dates:
                    next_num += 1
                    scheduled_at = f"{date_str} {time_part}"
                    new_session_id = await _create_cohort_session(
                        c_id, next_num, scheduled_at, topic, link,
                        recurring=1, days_of_week=days_csv,
                    )
                    await seed_attendance_for_session(c_id, new_session_id)
                    existing_dates.add(date_str)
                    total_created += 1
            day_cursor += timedelta(days=1)

    if total_created:
        log.info("RECURRING: generator created %d session(s)", total_created)
    return total_created


# ══════════════════════════════════════════════════════════════════════════
# RECURRING: /cohort_recurring_schedule — FSM for weekly-repeating sessions
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("cohort_recurring_schedule"))
async def cohort_recurring_schedule_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await state.set_state(CohortRecurringScheduleForm.cohort)
    await message.answer(t(lang, "cs_recurring_pick_cohort"),
                         reply_markup=_cohort_picker_kb(cohorts, "crsch_coh"))


@router.callback_query(F.data.startswith("cv2_rsched_"))
async def cv2_recurring_schedule(callback: CallbackQuery, state: FSMContext):
    """RECURRING: cv2_rsched shortcut — jump straight into day-of-week picking."""
    cid = int(callback.data[len("cv2_rsched_"):])
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(cohort_id=cid, days=set())
    await state.set_state(CohortRecurringScheduleForm.days)
    await callback.answer()
    await callback.message.answer(
        t(lang, "cs_recurring_ask_days"),
        reply_markup=cohort_recurring_days_keyboard(set(), lang),
    )


@router.callback_query(CohortRecurringScheduleForm.cohort, F.data.startswith("crsch_coh_"))
async def cr_got_cohort(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    cohort_id = int(callback.data[len("crsch_coh_"):])
    await state.update_data(cohort_id=cohort_id, days=set())
    await state.set_state(CohortRecurringScheduleForm.days)
    await callback.answer()
    await callback.message.answer(
        t(lang, "cs_recurring_ask_days"),
        reply_markup=cohort_recurring_days_keyboard(set(), lang),
    )


@router.callback_query(CohortRecurringScheduleForm.days, F.data.startswith("crday_"))
async def cr_toggle_day(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    payload = callback.data[len("crday_"):]

    if payload == "done":
        data = await state.get_data()
        days = data.get("days", set())
        if not days:
            await callback.answer(t(lang, "cs_recurring_days_empty"), show_alert=True)
            return
        await state.set_state(CohortRecurringScheduleForm.time_)
        await callback.answer()
        await callback.message.answer(t(lang, "cs_recurring_ask_time"), reply_markup=cancel_keyboard(lang))
        return

    try:
        day_idx = int(payload)
    except ValueError:
        await callback.answer()
        return
    data = await state.get_data()
    days = set(data.get("days", set()))
    if day_idx in days:
        days.discard(day_idx)
    else:
        days.add(day_idx)
    await state.update_data(days=days)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=cohort_recurring_days_keyboard(days, lang))


@router.message(CohortRecurringScheduleForm.time_)
async def cr_got_time(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    raw = message.text.strip()
    try:
        datetime.strptime(raw, "%H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    await state.update_data(time_local=raw)
    await state.set_state(CohortRecurringScheduleForm.topic)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="crsch_skip_topic")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await message.answer(t(lang, "cs_ask_topic"), reply_markup=skip_kb)


@router.callback_query(CohortRecurringScheduleForm.topic, F.data == "crsch_skip_topic")
async def cr_skip_topic(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(topic="")
    await state.set_state(CohortRecurringScheduleForm.link)
    await callback.answer()
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="crsch_skip_link")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await callback.message.answer(t(lang, "cs_ask_link"), reply_markup=skip_kb)


@router.message(CohortRecurringScheduleForm.topic)
async def cr_got_topic(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(topic=message.text.strip())
    await state.set_state(CohortRecurringScheduleForm.link)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="crsch_skip_link")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])
    await message.answer(t(lang, "cs_ask_link"), reply_markup=skip_kb)


@router.callback_query(CohortRecurringScheduleForm.link, F.data == "crsch_skip_link")
async def cr_skip_link(callback: CallbackQuery, state: FSMContext):
    await state.update_data(link="")
    await _finalize_recurring_schedule(callback, state)


@router.message(CohortRecurringScheduleForm.link)
async def cr_got_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await _finalize_recurring_schedule(message, state)


async def _finalize_recurring_schedule(source, state: FSMContext):
    """RECURRING: create the first occurrence as the recurring template, then
    immediately backfill the rest of the 30-day horizon for this cohort."""
    uid = source.from_user.id
    lang = await get_user_lang(uid)
    data = await state.get_data()
    cohort_id = data["cohort_id"]
    days = sorted(data["days"])
    days_csv = ",".join(str(d) for d in days)
    time_local = data["time_local"]
    topic = data.get("topic", "")
    link = data.get("link", "")

    existing = await _get_cohort_sessions(cohort_id)
    next_num = max((row[1] for row in existing), default=0) + 1

    # Find the soonest date (today or later) matching one of the picked weekdays.
    # NOTE: uses UTC "today" as the base day — close enough for scheduling purposes,
    # and consistent with how the daily generator advances through the horizon.
    today = datetime.utcnow().date()
    first_date = today
    for _ in range(7):
        if first_date.weekday() in days:
            break
        first_date += timedelta(days=1)

    _, p_offset = await get_user_timezone(uid)
    local_dt_str = f"{first_date.strftime('%Y-%m-%d')} {time_local}"
    scheduled_at_utc = local_to_utc(local_dt_str, p_offset)

    session_id = await _create_cohort_session(
        cohort_id, next_num, scheduled_at_utc, topic, link,
        recurring=1, days_of_week=days_csv,
    )
    await seed_attendance_for_session(cohort_id, session_id)

    # Backfill the remaining occurrences in the 30-day horizon right away.
    await generate_recurring_cohort_sessions(cohort_id=cohort_id)

    cohort_name = await get_cohort_name(cohort_id)
    days_display = ", ".join(t(lang, _DOW_KEYS[d]) for d in days)
    await state.clear()
    reply = t(lang, "cs_recurring_created", cohort=cohort_name, days=days_display, time=time_local)
    if isinstance(source, CallbackQuery):
        await source.answer()
        await source.message.answer(reply)
    else:
        await source.answer(reply)
    log.info("RECURRING: created template session_id=%d cohort_id=%d days=%s by user_id=%d",
             session_id, cohort_id, days_csv, uid)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_SESSION: /cohort_sessions — list sessions
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("cohort_sessions"))
async def cohort_sessions_start(message: Message):
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await message.answer(t(lang, "cs_pick_cohort_list"),
                         reply_markup=_cohort_picker_kb(cohorts, "csl_coh"))


@router.callback_query(F.data.startswith("csl_coh_"))
async def cohort_sessions_show(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_id = int(callback.data[len("csl_coh_"):])
    cohort_name = await verify_cohort_owner(cohort_id, uid)
    if not cohort_name:
        await callback.answer()
        return
    sessions = await _get_cohort_sessions(cohort_id)
    await callback.answer()
    if not sessions:
        await callback.message.answer(t(lang, "no_cs"))
        return
    p_tz, _ = await get_user_timezone(uid)
    status_key_map = {
        "scheduled": "cs_status_scheduled",
        "completed": "cs_status_completed",
        "cancelled": "cs_status_cancelled",
    }
    lines = [t(lang, "cs_list_title", cohort=cohort_name)]
    for _sid, num, sched_utc, topic, _link, status in sessions:
        date_display = to_user_tz(sched_utc, p_tz, "%d.%m %H:%M")
        topic_display = topic if topic else t(lang, "cs_no_topic")
        status_display = t(lang, status_key_map.get(status, "cs_status_scheduled"))
        lines.append(t(lang, "cs_row", num=num, date=date_display,
                       topic=topic_display, status=status_display))
    await callback.message.answer("\n".join(lines))


# ══════════════════════════════════════════════════════════════════════════
# COHORT_SESSION: /cohort_attendance — FSM + stateless mark callbacks
# ══════════════════════════════════════════════════════════════════════════

@router.message(Command("cohort_attendance"))
async def cohort_attendance_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await state.set_state(CohortAttendanceForm.cohort)
    await message.answer(t(lang, "cs_att_pick_cohort"),
                         reply_markup=_cohort_picker_kb(cohorts, "catt_coh"))


@router.callback_query(CohortAttendanceForm.cohort, F.data.startswith("catt_coh_"))
async def catt_got_cohort(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    cohort_id = int(callback.data[len("catt_coh_"):])
    sessions = await _get_scheduled_sessions(cohort_id)
    await callback.answer()
    if not sessions:
        await state.clear()
        await callback.message.answer(t(lang, "cs_att_no_sessions"))
        return
    await state.update_data(cohort_id=cohort_id)
    await state.set_state(CohortAttendanceForm.session)
    p_tz, _ = await get_user_timezone(callback.from_user.id)
    rows = []
    for sid, num, sched_utc, topic in sessions:
        date_str = to_user_tz(sched_utc, p_tz, "%d.%m %H:%M")
        label = f"#{num} — {date_str}"
        if topic:
            label += f" — {topic[:20]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"catt_ses_{sid}")])
    await callback.message.answer(t(lang, "cs_att_pick_session"),
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(CohortAttendanceForm.session, F.data.startswith("catt_ses_"))
async def catt_got_session(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    session_id = int(callback.data[len("catt_ses_"):])
    row = await _get_cohort_for_session(session_id)
    if not row:
        await callback.answer()
        await state.clear()
        return
    cohort_id, cohort_name, session_num = row
    await state.clear()
    await callback.answer()
    header, kb = await _attendance_kb(session_id, cohort_id, lang)
    title = t(lang, "cs_att_title", num=session_num, cohort=cohort_name)
    if kb is None:
        await callback.message.answer(title + "\n" + header)
    else:
        await callback.message.answer(title, reply_markup=kb)
    log.info("COHORT_SESSION: attendance shown session_id=%d by user_id=%d",
             session_id, callback.from_user.id)


@router.callback_query(F.data.startswith("catt_mk_"))
async def catt_mark(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    parts = callback.data[len("catt_mk_"):].split("_")
    if len(parts) != 3:
        await callback.answer()
        return
    session_id, member_id, new_status = int(parts[0]), int(parts[1]), parts[2]
    if new_status not in ("present", "absent", "pending"):
        await callback.answer()
        return
    await upsert_attendance(session_id, member_id, new_status)
    row = await _get_cohort_for_session(session_id)
    if not row:
        await callback.answer(t(lang, "cs_att_saved"))
        return
    cohort_id, cohort_name, session_num = row
    _, kb = await _attendance_kb(session_id, cohort_id, lang)
    title = t(lang, "cs_att_title", num=session_num, cohort=cohort_name)
    await callback.answer(t(lang, "cs_att_saved"))
    try:
        await callback.message.edit_text(title, reply_markup=kb)
    except Exception:
        pass
    log.info("COHORT_SESSION: attendance marked session_id=%d member_id=%d status=%s",
             session_id, member_id, new_status)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_coh_list — back to cohort list (from cohort action keyboard)
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "cv2_coh_list")
async def cv2_coh_list_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await get_cohorts_for_psych(uid)
    await callback.answer()
    if not cohorts:
        await callback.message.answer(t(lang, "no_cohorts"))
        return
    rows = [[InlineKeyboardButton(text=name, callback_data=f"cv2_pick_{cid}")]
            for cid, name, _max in cohorts]
    await callback.message.answer(t(lang, "cohort_list_title"),
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_pick_{cid} — show action keyboard for a specific cohort
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_pick_"))
async def cv2_pick_cohort(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_id = int(callback.data[len("cv2_pick_"):])
    row = await get_cohort_for_owner(cohort_id, uid)
    if not row:
        await callback.answer()
        return
    cohort_name, _ = row
    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_action_title", name=cohort_name),
        reply_markup=cohort_action_keyboard(cohort_id, lang),
    )


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_mem — members list
# ══════════════════════════════════════════════════════════════════════════

async def _render_members_text(cid: int, lang: str) -> str:
    """Build the formatted members list text."""
    cohort_name = await get_cohort_name(cid)
    members = await get_active_members(cid)
    if not members:
        return (t(lang, "cv2_no_members") + "\n\n"
                + t(lang, "cv2_members_empty_note"))
    lines = [t(lang, "cv2_members_title", cohort=cohort_name, count=len(members))]
    for _, tg_id, name in members:
        if tg_id and tg_id > 0:
            lines.append(t(lang, "cv2_member_row_tg", name=name, tg_id=tg_id))
        else:
            lines.append(t(lang, "cv2_member_row_manual", name=name))
    return "\n".join(lines)


@router.callback_query(F.data.startswith("cv2_mem_"))
async def cv2_members(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    cid = int(callback.data[len("cv2_mem_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted cv2_members on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    text = await _render_members_text(cid, lang)
    kb = cohort_members_keyboard(cid, lang)
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_addmem — add member manually (FSM)
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_addmem_"))
async def cv2_addmem_start(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data[len("cv2_addmem_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted addmem on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    await state.set_state(CohortAddMemberManualForm.name)
    await state.update_data(cohort_id=cid)
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cv2_back"), callback_data=f"cv2_mem_{cid}")
    ]])
    await callback.message.answer(t(lang, "cv2_add_member_ask"), reply_markup=kb)


@router.message(CohortAddMemberManualForm.name)
async def cv2_addmem_got_name(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    data = await state.get_data()
    cid = data["cohort_id"]
    name = message.text.strip()
    if not name:
        await message.answer(t(lang, "cv2_add_member_ask"))
        return
    psych_id = message.from_user.id
    allowed, err_msg = await check_add_cohort_member(psych_id, cid, lang=lang)
    if not allowed:
        await state.clear()
        await message.answer(err_msg)
        return
    manual_tg_id = await get_next_manual_id(cid)
    await add_member(cid, manual_tg_id, name)
    await state.clear()
    text = await _render_members_text(cid, lang)
    kb = cohort_members_keyboard(cid, lang)
    await message.answer(t(lang, "cv2_member_added", name=name))
    await message.answer(text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_invite — show invite link
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_invite_"))
async def cv2_invite(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_invite_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted invite on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    token, cohort_name = await get_cohort_invite_token(cid)
    await callback.answer()
    if not token:
        await callback.message.answer(t(lang, "cv2_no_members"))
        return
    link = f"https://t.me/{BOT_USERNAME}?start=join_{token}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cv2_back"), callback_data=f"cv2_mem_{cid}")
    ]])
    await callback.message.answer(
        t(lang, "cv2_invite_text", cohort=cohort_name, link=link),
        reply_markup=kb,
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_sched — shortcut into CohortScheduleForm.session_number
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_sched_"))
async def cv2_schedule(callback: CallbackQuery, state: FSMContext):
    """SESSIONS: session number is auto-assigned here too — straight to date/time."""
    cid = int(callback.data[len("cv2_sched_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted schedule on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    existing = await _get_cohort_sessions(cid)
    next_num = max((row[1] for row in existing), default=0) + 1
    await state.update_data(cohort_id=cid, session_number=next_num)
    await state.set_state(CohortScheduleForm.datetime_)
    await callback.answer()
    await callback.message.answer(t(lang, "cs_ask_datetime"), reply_markup=cancel_keyboard(lang))


# ══════════════════════════════════════════════════════════════════════════
# SESSIONS: cv2_slist — browsable session list + per-session detail/actions
# ══════════════════════════════════════════════════════════════════════════

_SESSIONS_HORIZON_DAYS = 45


async def _render_session_list(uid: int, cohort_id: int, lang: str):
    """SESSIONS: builds (text, keyboard) for the session list, or None if the
    caller doesn't own this cohort."""
    cohort_name = await verify_cohort_owner(cohort_id, uid)
    if cohort_name is None:
        return None
    sessions = await _get_upcoming_sessions(cohort_id, _SESSIONS_HORIZON_DAYS)
    p_tz, _ = await get_user_timezone(uid)
    if not sessions:
        text = t(lang, "cs2_list_empty", cohort=cohort_name, days=_SESSIONS_HORIZON_DAYS)
    else:
        text = t(lang, "cs2_list_title", cohort=cohort_name, days=_SESSIONS_HORIZON_DAYS)
    rows = []
    for sid, num, sched_utc, topic, _link, recurring, _dow in sessions:
        date_display = to_user_tz(sched_utc, p_tz, "%d.%m %H:%M")
        badge = " 🔁" if recurring else ""
        label = f"{date_display} · #{num}{badge}"
        if topic:
            label += f" · {topic[:18]}"
        rows.append((sid, label))
    kb = cohort_session_list_keyboard(rows, cohort_id, lang)
    return text, kb


async def _render_session_detail(uid: int, session_id: int, lang: str):
    """SESSIONS: builds (text, keyboard) for one session's detail/action view,
    or None if the session is gone or doesn't belong to this psychologist."""
    row = await _get_session(session_id)
    if not row:
        return None
    sid, cohort_id, num, sched_utc, topic, link, _status, recurring, days_csv = row
    cohort_name = await verify_cohort_owner(cohort_id, uid)
    if cohort_name is None:
        return None
    p_tz, _ = await get_user_timezone(uid)
    date_display = to_user_tz(sched_utc, p_tz, "%d.%m.%Y %H:%M")

    lines = [
        t(lang, "cs2_detail_header", num=num, cohort=cohort_name),
        t(lang, "cs2_detail_date", date=date_display),
        t(lang, "cs2_detail_topic", topic=topic if topic else t(lang, "cs_no_topic")),
        t(lang, "cs2_detail_link", link=link if link else t(lang, "cs2_no_link")),
    ]
    paused = False
    if recurring:
        try:
            day_idxs = sorted(int(d) for d in days_csv.split(",") if d.strip() != "")
        except ValueError:
            day_idxs = []
        days_display = ", ".join(t(lang, _DOW_KEYS[d]) for d in day_idxs if 0 <= d <= 6)
        lines.append(t(lang, "cs2_detail_recurring", days=days_display))
        paused = await is_recurring_paused(cohort_id)
        if paused:
            lines.append(t(lang, "cs2_detail_paused"))

    text = "\n".join(lines)
    kb = cohort_session_detail_keyboard(sid, cohort_id, bool(recurring), paused, lang)
    return text, kb


@router.callback_query(F.data.startswith("cv2_slist_"))
async def cv2_session_list(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_slist_"):])
    lang = await get_user_lang(callback.from_user.id)
    result = await _render_session_list(callback.from_user.id, cid, lang)
    await callback.answer()
    if result is None:
        return
    text, kb = result
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("csd_"))
async def csd_session_detail(callback: CallbackQuery):
    session_id = int(callback.data[len("csd_"):])
    lang = await get_user_lang(callback.from_user.id)
    result = await _render_session_detail(callback.from_user.id, session_id, lang)
    if result is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    text, kb = result
    await callback.answer()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


# ── SESSIONS: edit date/time ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("csdt_"))
async def csdt_start(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data[len("csdt_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    await state.update_data(session_id=session_id, cohort_id=row[1])
    await state.set_state(CohortSessionEditForm.datetime_)
    await callback.answer()
    await callback.message.answer(t(lang, "cs2_ask_datetime_new"), reply_markup=cancel_keyboard(lang))


@router.message(CohortSessionEditForm.datetime_)
async def csdt_got_value(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    raw = message.text.strip()
    try:
        datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    data = await state.get_data()
    session_id = data["session_id"]
    _, p_offset = await get_user_timezone(message.from_user.id)
    scheduled_at_utc = local_to_utc(raw, p_offset)
    await _update_session_field(session_id, "scheduled_at", scheduled_at_utc)
    await state.clear()
    await message.answer(t(lang, "cs2_updated_dt"))
    result = await _render_session_detail(message.from_user.id, session_id, lang)
    if result:
        text, kb = result
        await message.answer(text, reply_markup=kb)
    log.info("SESSIONS: session_id=%d datetime updated by user_id=%d", session_id, message.from_user.id)


# ── SESSIONS: edit topic ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cstp_"))
async def cstp_start(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data[len("cstp_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    await state.update_data(session_id=session_id, cohort_id=row[1])
    await state.set_state(CohortSessionEditForm.topic)
    await callback.answer()
    await callback.message.answer(t(lang, "cs2_ask_topic_new"),
                                  reply_markup=cohort_clear_field_keyboard("csed_clr_topic", lang))


@router.callback_query(CohortSessionEditForm.topic, F.data == "csed_clr_topic")
async def cstp_clear(callback: CallbackQuery, state: FSMContext):
    await _finish_field_edit(callback, state, "topic", "", "cs2_updated_topic")


@router.message(CohortSessionEditForm.topic)
async def cstp_got_value(message: Message, state: FSMContext):
    await _finish_field_edit(message, state, "topic", message.text.strip(), "cs2_updated_topic")


# ── SESSIONS: edit link ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cslk_"))
async def cslk_start(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data[len("cslk_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    await state.update_data(session_id=session_id, cohort_id=row[1])
    await state.set_state(CohortSessionEditForm.link)
    await callback.answer()
    await callback.message.answer(t(lang, "cs2_ask_link_new"),
                                  reply_markup=cohort_clear_field_keyboard("csed_clr_link", lang))


@router.callback_query(CohortSessionEditForm.link, F.data == "csed_clr_link")
async def cslk_clear(callback: CallbackQuery, state: FSMContext):
    await _finish_field_edit(callback, state, "link", "", "cs2_updated_link")


@router.message(CohortSessionEditForm.link)
async def cslk_got_value(message: Message, state: FSMContext):
    await _finish_field_edit(message, state, "link", message.text.strip(), "cs2_updated_link")


async def _finish_field_edit(source, state: FSMContext, field: str, value: str, ok_key: str):
    """SESSIONS: shared tail for topic/link edits — persists the value, clears
    the FSM, confirms, then re-shows the (now updated) session detail view."""
    uid = source.from_user.id
    lang = await get_user_lang(uid)
    data = await state.get_data()
    session_id = data["session_id"]
    await _update_session_field(session_id, field, value)
    await state.clear()
    reply = t(lang, ok_key)
    result = await _render_session_detail(uid, session_id, lang)
    if isinstance(source, CallbackQuery):
        await source.answer(reply)
        if result:
            text, kb = result
            await source.message.answer(text, reply_markup=kb)
    else:
        await source.answer(reply)
        if result:
            text, kb = result
            await source.answer(text, reply_markup=kb)
    log.info("SESSIONS: session_id=%d field=%s updated by user_id=%d", session_id, field, uid)


# ── SESSIONS: delete session ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("csdl_"))
async def csdl_ask(callback: CallbackQuery):
    session_id = int(callback.data[len("csdl_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    _, _cid, num, sched_utc, *_ = row
    p_tz, _ = await get_user_timezone(callback.from_user.id)
    date_display = to_user_tz(sched_utc, p_tz, "%d.%m.%Y %H:%M")
    await callback.answer()
    kb = cohort_confirm_keyboard("cs2_delete_yes", "cs2_delete_no",
                                 f"csdy_{session_id}", f"csdn_{session_id}", lang)
    await callback.message.answer(t(lang, "cs2_delete_confirm", num=num, date=date_display), reply_markup=kb)


@router.callback_query(F.data.startswith("csdy_"))
async def csdy_confirm(callback: CallbackQuery):
    session_id = int(callback.data[len("csdy_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    _, cohort_id, num, *_ = row
    await _delete_cohort_session(session_id)
    await callback.answer(t(lang, "cs2_deleted_ok", num=num))
    result = await _render_session_list(callback.from_user.id, cohort_id, lang)
    if result:
        text, kb = result
        await callback.message.answer(text, reply_markup=kb)
    log.info("SESSIONS: session_id=%d deleted by user_id=%d", session_id, callback.from_user.id)


@router.callback_query(F.data.startswith("csdn_"))
async def csdn_cancel(callback: CallbackQuery):
    session_id = int(callback.data[len("csdn_"):])
    lang = await get_user_lang(callback.from_user.id)
    result = await _render_session_detail(callback.from_user.id, session_id, lang)
    await callback.answer()
    if result:
        text, kb = result
        await callback.message.answer(text, reply_markup=kb)


# ── SESSIONS: pause / resume the recurrence rule ────────────────────────────

@router.callback_query(F.data.startswith("cspz_"))
async def cspz_toggle(callback: CallbackQuery):
    session_id = int(callback.data[len("cspz_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    cohort_id = row[1]
    cohort_name = await get_cohort_name(cohort_id)
    currently_paused = await is_recurring_paused(cohort_id)
    await set_recurring_paused(cohort_id, not currently_paused)
    feedback = t(lang, "cs2_resumed_ok" if currently_paused else "cs2_paused_ok", cohort=cohort_name)
    await callback.answer(feedback, show_alert=True)
    result = await _render_session_detail(callback.from_user.id, session_id, lang)
    if result:
        text, kb = result
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
    log.info("SESSIONS: cohort_id=%d recurring_paused=%s by user_id=%d",
             cohort_id, not currently_paused, callback.from_user.id)


# ── SESSIONS: delete the recurrence rule ────────────────────────────────────

@router.callback_query(F.data.startswith("csrl_"))
async def csrl_ask(callback: CallbackQuery):
    session_id = int(callback.data[len("csrl_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    cohort_id = row[1]
    cohort_name = await get_cohort_name(cohort_id)
    await callback.answer()
    kb = cohort_confirm_keyboard("cs2_delrule_yes", "cs2_delrule_no",
                                 f"csry_{session_id}", f"csrn_{session_id}", lang)
    await callback.message.answer(t(lang, "cs2_delrule_confirm", cohort=cohort_name), reply_markup=kb)


@router.callback_query(F.data.startswith("csry_"))
async def csry_confirm(callback: CallbackQuery):
    session_id = int(callback.data[len("csry_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_session(session_id)
    if not row or await verify_cohort_owner(row[1], callback.from_user.id) is None:
        await callback.answer(t(lang, "cs2_not_found"), show_alert=True)
        return
    cohort_id = row[1]
    cohort_name = await get_cohort_name(cohort_id)
    await _delete_recurring_rule(cohort_id)
    await callback.answer(t(lang, "cs2_delrule_ok", cohort=cohort_name), show_alert=True)
    result = await _render_session_detail(callback.from_user.id, session_id, lang)
    if result:
        text, kb = result
        await callback.message.answer(text, reply_markup=kb)
    log.info("SESSIONS: recurring rule deleted cohort_id=%d by user_id=%d",
             cohort_id, callback.from_user.id)


@router.callback_query(F.data.startswith("csrn_"))
async def csrn_cancel(callback: CallbackQuery):
    session_id = int(callback.data[len("csrn_"):])
    lang = await get_user_lang(callback.from_user.id)
    result = await _render_session_detail(callback.from_user.id, session_id, lang)
    await callback.answer()
    if result:
        text, kb = result
        await callback.message.answer(text, reply_markup=kb)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_att — shortcut into CohortAttendanceForm.session
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_att_"))
async def cv2_attendance(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data[len("cv2_att_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted attendance on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    sessions = await _get_scheduled_sessions(cid)
    await callback.answer()
    if not sessions:
        await callback.message.answer(t(lang, "cs_att_no_sessions"))
        return
    await state.update_data(cohort_id=cid)
    await state.set_state(CohortAttendanceForm.session)
    p_tz, _ = await get_user_timezone(callback.from_user.id)
    rows = []
    for sid, num, sched_utc, topic in sessions:
        date_str = to_user_tz(sched_utc, p_tz, "%d.%m %H:%M")
        label = f"#{num} — {date_str}"
        if topic:
            label += f" — {topic[:20]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"catt_ses_{sid}")])
    await callback.message.answer(t(lang, "cs_att_pick_session"),
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_ci — check-in options menu
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_ci_"))
async def cv2_checkins_menu(callback: CallbackQuery):
    # COHORT_V2: only handle cv2_ci_{number} — other cv2_ci* prefixes are distinct
    cid = int(callback.data[len("cv2_ci_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_name = await verify_cohort_owner(cid, uid)
    if cohort_name is None:
        log.warning("SECURITY: user_id=%d attempted ci_menu on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cv2_checkin_btn_setup"),
                              callback_data=f"cv2_cistp_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_checkin_btn_summary"),
                              callback_data=f"cv2_cisum_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_checkin_btn_send_now"),
                              callback_data=f"cv2_cisnd_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_back"),
                              callback_data=f"cv2_pick_{cid}")],
    ])
    await callback.message.answer(
        t(lang, "cv2_checkin_options_title", cohort=cohort_name), reply_markup=kb
    )


# ── Check-in setup FSM ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cv2_cistp_"))
async def cv2_checkin_setup_start(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data[len("cv2_cistp_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted cistp on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    await state.update_data(cohort_id=cid)
    await state.set_state(CohortCheckinSetupForm.question)
    await callback.answer()
    await callback.message.answer(t(lang, "cv2_checkin_ask_question"),
                                  reply_markup=cancel_keyboard(lang))


@router.message(CohortCheckinSetupForm.question)
async def cv2_ci_got_question(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(question=message.text.strip())
    await state.set_state(CohortCheckinSetupForm.interval)
    await message.answer(t(lang, "cv2_checkin_ask_interval"), reply_markup=cancel_keyboard(lang))


@router.message(CohortCheckinSetupForm.interval)
async def cv2_ci_got_interval(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    try:
        interval_h = int(message.text.strip())
        if interval_h < 1:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "minutes_invalid"))
        return
    data = await state.get_data()
    cid = data["cohort_id"]
    question = data["question"]
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_checkin_configs (cohort_id, question, interval_h) VALUES (?, ?, ?) "
            "ON CONFLICT(cohort_id) DO UPDATE SET question=excluded.question, "
            "interval_h=excluded.interval_h, enabled=1",
            (cid, question, interval_h),
        )
        await db.commit()
    await message.answer(t(lang, "cv2_checkin_saved", q=question, h=interval_h))
    log.info("COHORT_V2: checkin config saved cohort_id=%d interval_h=%d", cid, interval_h)


# ── Check-in summary ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cv2_cisum_"))
async def cv2_checkin_summary(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_cisum_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_name = await verify_cohort_owner(cid, uid)
    if cohort_name is None:
        log.warning("SECURITY: user_id=%d attempted cisum on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT cm.telegram_id, cm.name, COUNT(cc.id), "
            "COALESCE(ROUND(AVG(cc.score), 1), 0.0) "
            "FROM cohort_members cm "
            "LEFT JOIN cohort_checkins cc "
            "  ON cc.cohort_id = cm.cohort_id AND cc.member_telegram_id = cm.telegram_id "
            "WHERE cm.cohort_id = ? AND cm.status = 'active' "
            "GROUP BY cm.telegram_id, cm.name ORDER BY cm.name",
            (cid,),
        )
        rows = await cur.fetchall()
    await callback.answer()
    if not rows:
        await callback.message.answer(t(lang, "cv2_no_checkin_data"))
        return
    lines = [t(lang, "cv2_checkin_summary_title", cohort=cohort_name)]
    for _, name, count, avg in rows:
        lines.append(t(lang, "cv2_checkin_row", name=name, count=count, avg=avg or 0.0))
    await callback.message.answer("\n".join(lines))


# ── Send check-in now ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cv2_cisnd_"))
async def cv2_checkin_send_now(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_cisnd_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted cisnd on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT question FROM cohort_checkin_configs WHERE cohort_id = ?", (cid,)
        )
        cfg = await cur.fetchone()
    if not cfg or not cfg[0]:
        await callback.answer(t(lang, "cv2_checkin_ask_question"), show_alert=True)
        return
    question = cfg[0]
    members = await get_active_members(cid)
    if not members:
        await callback.answer(t(lang, "cv2_broadcast_no_members"), show_alert=True)
        return
    await callback.answer()
    sent = 0
    for _, member_tg, _ in members:
        try:
            kb = _cohort_checkin_kb(cid, member_tg)
            await callback.bot.send_message(member_tg, question, reply_markup=kb)
            sent += 1
        except Exception as e:
            log.warning("COHORT_V2: send checkin fail member_tg=%d: %s", member_tg, e)
    await callback.message.answer(t(lang, "cv2_checkin_sent", count=sent))
    log.info("COHORT_V2: checkin sent cohort_id=%d sent=%d/%d", cid, sent, len(members))


# ── Member check-in response ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("cci_"))
async def cci_response(callback: CallbackQuery):
    """COHORT_V2: Member submits their check-in score."""
    parts = callback.data[len("cci_"):].split("_")
    if len(parts) != 3:
        await callback.answer()
        return
    cohort_id, _member_tg, score = int(parts[0]), int(parts[1]), int(parts[2])
    tg_id = callback.from_user.id
    lang = await get_cohort_member_lang(tg_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT question FROM cohort_checkin_configs WHERE cohort_id = ?", (cohort_id,)
        )
        cfg = await cur.fetchone()
        question = cfg[0] if cfg else ""
        await db.execute(
            "INSERT INTO cohort_checkins "
            "(cohort_id, member_telegram_id, score, question_text, answered_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (cohort_id, tg_id, score, question, now_str()),
        )
        await db.commit()
    await callback.answer(t(lang, "cv2_checkin_member_thanks"), show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    log.info("COHORT_V2: checkin response cohort_id=%d tg_id=%d score=%d", cohort_id, tg_id, score)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_notes — session note picker
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_notes_"))
async def cv2_notes(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_notes_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted notes on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    p_tz, _ = await get_user_timezone(uid)
    sessions = await _get_scheduled_sessions(cid)
    await callback.answer()
    if not sessions:
        await callback.message.answer(t(lang, "cs_att_no_sessions"))
        return
    rows = []
    for sid, num, sched_utc, topic in sessions:
        date_str = to_user_tz(sched_utc, p_tz, "%d.%m %H:%M")
        label = f"#{num} — {date_str}"
        if topic:
            label += f" — {topic[:20]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"cv2_nses_{sid}")])
    await callback.message.answer(t(lang, "cv2_notes_pick_session"),
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("cv2_nses_"))
async def cv2_notes_session(callback: CallbackQuery):
    session_id = int(callback.data[len("cv2_nses_"):])
    lang = await get_user_lang(callback.from_user.id)
    uid = callback.from_user.id
    row = await _get_cohort_for_session(session_id)
    if not row:
        await callback.answer()
        return
    cohort_id, _, session_num = row
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT note_type, text FROM cohort_session_notes "
            "WHERE session_id = ? AND psychologist_id = ? ORDER BY created_at",
            (session_id, uid),
        )
        notes = await cur.fetchall()
    await callback.answer()
    lines = [t(lang, "cv2_notes_title", num=session_num)]
    if not notes:
        lines.append(t(lang, "cv2_notes_empty"))
    else:
        for note_type, text in notes:
            key = "cv2_soap_row" if note_type == "soap" else "cv2_note_row"
            lines.append(t(lang, key, text=text))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cv2_note_btn_add"),
                              callback_data=f"cv2_nadd_{session_id}"),
         InlineKeyboardButton(text=t(lang, "cv2_note_btn_soap"),
                              callback_data=f"cv2_nsoap_{session_id}")],
        [InlineKeyboardButton(text=t(lang, "cv2_back"),
                              callback_data=f"cv2_notes_{cohort_id}")],
    ])
    await callback.message.answer("\n".join(lines), reply_markup=kb)


# ── Add plain note FSM ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cv2_nadd_"))
async def cv2_note_add_start(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data[len("cv2_nadd_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_cohort_for_session(session_id)
    session_num = row[2] if row else "?"
    await state.update_data(session_id=session_id, note_type="general")
    await state.set_state(CohortSessionNoteForm.note_text)
    await callback.answer()
    await callback.message.answer(t(lang, "cv2_note_ask", num=session_num),
                                  reply_markup=cancel_keyboard(lang))


@router.message(CohortSessionNoteForm.note_text)
async def cv2_note_text_got(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    data = await state.get_data()
    session_id = data["session_id"]
    note_type = data.get("note_type", "general")
    text = message.text.strip()
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_session_notes "
            "(session_id, psychologist_id, note_type, text, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, message.from_user.id, note_type, text, now_str()),
        )
        await db.commit()
    row = await _get_cohort_for_session(session_id)
    session_num = row[2] if row else "?"
    if note_type == "soap":
        await message.answer(t(lang, "cv2_soap_saved", num=session_num))
    else:
        await message.answer(t(lang, "cv2_note_saved"))
    log.info("COHORT_V2: session note saved session_id=%d type=%s by user_id=%d",
             session_id, note_type, message.from_user.id)


# ── SOAP note FSM (4 steps) ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("cv2_nsoap_"))
async def cv2_soap_start(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data[len("cv2_nsoap_"):])
    lang = await get_user_lang(callback.from_user.id)
    row = await _get_cohort_for_session(session_id)
    session_num = row[2] if row else "?"
    await state.update_data(session_id=session_id, session_num=session_num)
    await state.set_state(CohortSOAPNoteForm.s)
    await callback.answer()
    await callback.message.answer(t(lang, "cv2_soap_s", num=session_num),
                                  reply_markup=cancel_keyboard(lang))


@router.message(CohortSOAPNoteForm.s)
async def cv2_soap_s(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(soap_s=message.text.strip())
    await state.set_state(CohortSOAPNoteForm.o)
    await message.answer(t(lang, "cv2_soap_o"), reply_markup=cancel_keyboard(lang))


@router.message(CohortSOAPNoteForm.o)
async def cv2_soap_o(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(soap_o=message.text.strip())
    await state.set_state(CohortSOAPNoteForm.a)
    await message.answer(t(lang, "cv2_soap_a"), reply_markup=cancel_keyboard(lang))


@router.message(CohortSOAPNoteForm.a)
async def cv2_soap_a(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(soap_a=message.text.strip())
    await state.set_state(CohortSOAPNoteForm.p)
    await message.answer(t(lang, "cv2_soap_p"), reply_markup=cancel_keyboard(lang))


@router.message(CohortSOAPNoteForm.p)
async def cv2_soap_p(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    data = await state.get_data()
    session_id = data["session_id"]
    session_num = data.get("session_num", "?")
    text = (
        f"S: {data.get('soap_s', '')}\n"
        f"O: {data.get('soap_o', '')}\n"
        f"A: {data.get('soap_a', '')}\n"
        f"P: {message.text.strip()}"
    )
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_session_notes "
            "(session_id, psychologist_id, note_type, text, created_at) "
            "VALUES (?, ?, 'soap', ?, ?)",
            (session_id, message.from_user.id, text, now_str()),
        )
        await db.commit()
    await message.answer(t(lang, "cv2_soap_saved", num=session_num))
    log.info("COHORT_V2: SOAP note saved session_id=%d by user_id=%d",
             session_id, message.from_user.id)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_bc — broadcast FSM
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_bc_"))
async def cv2_broadcast_start(callback: CallbackQuery, state: FSMContext):
    cid = int(callback.data[len("cv2_bc_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    if await verify_cohort_owner(cid, uid) is None:
        log.warning("SECURITY: user_id=%d attempted broadcast on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    members = await get_active_members(cid)
    if not members:
        await callback.answer(t(lang, "cv2_broadcast_no_members"), show_alert=True)
        return
    cohort_name = await get_cohort_name(cid)
    await state.update_data(cohort_id=cid, cohort_name=cohort_name, member_count=len(members))
    await state.set_state(CohortBroadcastForm.message)
    await callback.answer()
    await callback.message.answer(
        t(lang, "cv2_broadcast_ask", count=len(members), cohort=cohort_name),
        reply_markup=cancel_keyboard(lang),
    )


@router.message(CohortBroadcastForm.message)
async def cv2_broadcast_got_message(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    data = await state.get_data()
    text = message.text.strip()
    count = data["member_count"]
    await state.update_data(broadcast_text=text)
    await state.set_state(CohortBroadcastForm.confirm)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cv2_broadcast_send"),
                             callback_data="cv2_bcsend"),
        InlineKeyboardButton(text=t(lang, "cv2_broadcast_cancel"),
                             callback_data="cv2_bccancel"),
    ]])
    await message.answer(t(lang, "cv2_broadcast_preview", text=text, count=count),
                         reply_markup=kb)


@router.callback_query(CohortBroadcastForm.confirm, F.data == "cv2_bcsend")
async def cv2_broadcast_send(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    data = await state.get_data()
    cid = data["cohort_id"]
    text = data["broadcast_text"]
    members = await get_active_members(cid)
    await state.clear()
    await callback.answer()
    sent = 0
    for _, member_tg, _ in members:
        try:
            await callback.bot.send_message(member_tg, text)
            sent += 1
        except Exception as e:
            log.warning("COHORT_V2: broadcast fail member_tg=%d: %s", member_tg, e)
    await callback.message.answer(t(lang, "cv2_broadcast_done", sent=sent, total=len(members)))
    log.info("COHORT_V2: broadcast cohort_id=%d sent=%d/%d", cid, sent, len(members))


@router.callback_query(CohortBroadcastForm.confirm, F.data == "cv2_bccancel")
async def cv2_broadcast_cancel_cb(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.answer()
    await callback.message.answer(t(lang, "fsm_cancelled"))


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_stats — cohort statistics
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_stats_"))
async def cv2_stats(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_stats_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_name = await verify_cohort_owner(cid, uid)
    if cohort_name is None:
        log.warning("SECURITY: user_id=%d attempted stats on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    member_count = await get_member_count(cid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*), SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) "
            "FROM cohort_sessions WHERE cohort_id = ?", (cid,)
        )
        srow = await cur.fetchone()
        total_sessions = srow[0] or 0
        completed_sessions = srow[1] or 0
        att_pct = 0
        if total_sessions > 0 and member_count > 0:
            cur = await db.execute(
                "SELECT COUNT(*) FROM cohort_attendance ca "
                "JOIN cohort_sessions cs ON cs.id = ca.session_id "
                "WHERE cs.cohort_id = ? AND ca.status = 'present'", (cid,)
            )
            present_count = (await cur.fetchone())[0]
            possible = total_sessions * member_count
            att_pct = round(present_count * 100 / possible) if possible else 0
        cur = await db.execute(
            "SELECT COUNT(*), ROUND(AVG(score), 1) FROM cohort_checkins WHERE cohort_id = ?", (cid,)
        )
        cirow = await cur.fetchone()
        ci_count = cirow[0] or 0
        ci_avg = cirow[1] or 0.0
    await callback.answer()
    lines = [
        t(lang, "cv2_stats_title", cohort=cohort_name),
        t(lang, "cv2_stats_members", count=member_count),
        t(lang, "cv2_stats_sessions", total=total_sessions, completed=completed_sessions),
        t(lang, "cv2_stats_attendance_pct", pct=att_pct),
        t(lang, "cv2_stats_checkins", count=ci_count),
        t(lang, "cv2_stats_avg_score", avg=ci_avg),
    ]
    await callback.message.answer("\n".join(lines))
    log.info("COHORT_V2: stats shown cohort_id=%d by user_id=%d", cid, callback.from_user.id)


# ══════════════════════════════════════════════════════════════════════════
# COHORT_V2: cv2_arch — archive cohort (confirm + execute)
# ══════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("cv2_arch_"))
async def cv2_archive_confirm(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_arch_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    row = await get_cohort_for_owner(cid, uid)
    if not row:
        log.warning("SECURITY: user_id=%d attempted archive_confirm on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    cohort_name, status = row
    if status == "archived":
        await callback.answer(t(lang, "cv2_already_archived"), show_alert=True)
        return
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cv2_archive_yes"),
                             callback_data=f"cv2_arcy_{cid}"),
        InlineKeyboardButton(text=t(lang, "cv2_archive_no"),
                             callback_data=f"cv2_pick_{cid}"),
    ]])
    await callback.message.answer(t(lang, "cv2_archive_confirm", cohort=cohort_name),
                                  reply_markup=kb)


@router.callback_query(F.data.startswith("cv2_arcy_"))
async def cv2_archive_do(callback: CallbackQuery):
    cid = int(callback.data[len("cv2_arcy_"):])
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_name = await verify_cohort_owner(cid, uid)
    if cohort_name is None:
        log.warning("SECURITY: user_id=%d attempted archive_do on cohort_id=%d (not owner)", uid, cid)
        await callback.answer()
        return
    await archive_cohort(cid)
    await callback.answer()
    await callback.message.answer(t(lang, "cv2_archived_ok", cohort=cohort_name))
    log.info("COHORT_V2: cohort_id=%d archived by user_id=%d", cid, callback.from_user.id)
