"""COHORT / COHORT_SESSION: Cohort management — create, list, join, schedule sessions, attendance."""

import logging
import secrets
from datetime import datetime

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
    utc_to_local,
)
from keyboards import cancel_keyboard, cohort_type_keyboard
from states.cohort_states import CohortAttendanceForm, CohortCreateForm, CohortScheduleForm
from translations import t

# COHORT: import bot username from clients module (set at startup)
from handlers.clients import BOT_USERNAME

router = Router()
log = logging.getLogger(__name__)


# ── COHORT: DB helpers ─────────────────────────────────────────────────────

def _make_cohort_token() -> str:
    # COHORT: short random hex token for invite links
    return secrets.token_hex(6)


async def _create_cohort(
    psychologist_id: int,
    name: str,
    description: str,
    type_: str,
    max_participants: int,
) -> tuple[int, str]:
    """COHORT: Insert new cohort row. Returns (cohort_id, invite_token)."""
    token = _make_cohort_token()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cohorts "
            "(psychologist_id, name, description, type, max_participants, status, created_at, invite_token) "
            "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
            (psychologist_id, name, description, type_, max_participants, now_str(), token),
        )
        cohort_id = cur.lastrowid
        await db.commit()
    return cohort_id, token


async def _get_cohort_by_token(token: str):
    """COHORT: Return cohort row or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, psychologist_id, name, max_participants FROM cohorts WHERE invite_token = ?",
            (token,),
        )
        return await cur.fetchone()


async def _get_member_count(cohort_id: int) -> int:
    """COHORT: Count active members in a cohort."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM cohort_members WHERE cohort_id = ? AND status = 'active'",
            (cohort_id,),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def _is_member(cohort_id: int, telegram_id: int) -> bool:
    """COHORT: Check if a user is already an active member."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM cohort_members WHERE cohort_id = ? AND telegram_id = ? AND status = 'active'",
            (cohort_id, telegram_id),
        )
        return bool(await cur.fetchone())


async def _add_member(cohort_id: int, telegram_id: int, name: str):
    """COHORT: Add a participant to cohort_members."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO cohort_members (cohort_id, telegram_id, name, joined_at, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (cohort_id, telegram_id, name, now_str()),
        )
        await db.commit()


async def _get_cohorts_for_psych(psychologist_id: int) -> list:
    """COHORT: Return list of (id, name, max_participants) for a psychologist."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name, max_participants FROM cohorts WHERE psychologist_id = ? ORDER BY created_at DESC",
            (psychologist_id,),
        )
        return await cur.fetchall()


# ── COHORT_SESSION: DB helpers ─────────────────────────────────────────────

async def _create_cohort_session(
    cohort_id: int,
    session_number: int,
    scheduled_at_utc: str,
    topic: str,
    link: str,
) -> int:
    """COHORT_SESSION: Insert a cohort session. Returns session_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cohort_sessions "
            "(cohort_id, session_number, scheduled_at, topic, link, status) "
            "VALUES (?, ?, ?, ?, ?, 'scheduled')",
            (cohort_id, session_number, scheduled_at_utc, topic, link),
        )
        session_id = cur.lastrowid
        await db.commit()
    return session_id


async def _get_cohort_sessions(cohort_id: int) -> list:
    """COHORT_SESSION: Return all sessions for a cohort ordered by scheduled_at."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic, link, status "
            "FROM cohort_sessions WHERE cohort_id = ? ORDER BY scheduled_at ASC",
            (cohort_id,),
        )
        return await cur.fetchall()


async def _get_scheduled_sessions(cohort_id: int) -> list:
    """COHORT_SESSION: Return only scheduled/completed sessions (for attendance)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, session_number, scheduled_at, topic "
            "FROM cohort_sessions "
            "WHERE cohort_id = ? AND status IN ('scheduled', 'completed') "
            "ORDER BY scheduled_at ASC",
            (cohort_id,),
        )
        return await cur.fetchall()


async def _get_active_members(cohort_id: int) -> list:
    """COHORT_SESSION: Return (id, telegram_id, name) for all active members."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, telegram_id, name FROM cohort_members "
            "WHERE cohort_id = ? AND status = 'active' ORDER BY name",
            (cohort_id,),
        )
        return await cur.fetchall()


async def _upsert_attendance(session_id: int, member_id: int, status: str):
    """COHORT_SESSION: Insert or update attendance record."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO cohort_attendance (session_id, member_id, status) VALUES (?, ?, ?) "
            "ON CONFLICT(session_id, member_id) DO UPDATE SET status = excluded.status",
            (session_id, member_id, status),
        )
        await db.commit()


async def _get_attendance_for_session(session_id: int) -> dict:
    """COHORT_SESSION: Return {member_id: status} for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT member_id, status FROM cohort_attendance WHERE session_id = ?",
            (session_id,),
        )
        rows = await cur.fetchall()
    return {row[0]: row[1] for row in rows}


async def _get_cohort_for_session(session_id: int):
    """COHORT_SESSION: Return (cohort_id, cohort_name, session_number) for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT cs.cohort_id, c.name, cs.session_number "
            "FROM cohort_sessions cs JOIN cohorts c ON c.id = cs.cohort_id "
            "WHERE cs.id = ?",
            (session_id,),
        )
        return await cur.fetchone()


# ── COHORT_SESSION: attendance keyboard builder ────────────────────────────

STATUS_EMOJI = {"present": "✅", "absent": "❌", "pending": "⏳"}

async def _attendance_kb(session_id: int, cohort_id: int, lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """COHORT_SESSION: Build attendance inline keyboard and header text."""
    members = await _get_active_members(cohort_id)
    if not members:
        return t(lang, "cs_att_no_members"), None
    attendance = await _get_attendance_for_session(session_id)
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


# ── COHORT: cohort picker keyboard ─────────────────────────────────────────

def _cohort_picker_kb(cohorts: list, cb_prefix: str) -> InlineKeyboardMarkup:
    """COHORT_SESSION: Inline keyboard listing cohorts. cb_prefix_{cohort_id} per button."""
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"{cb_prefix}_{cid}")]
        for cid, name, _ in cohorts
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ══ COHORT: /cohort_create — FSM wizard ═══════════════════════════════════

@router.message(Command("cohort_create"))
async def cohort_create_start(message: Message, state: FSMContext):
    """COHORT: Step 1 — ask for cohort name."""
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(CohortCreateForm.name)
    await message.answer(t(lang, "cohort_ask_name"), reply_markup=cancel_keyboard(lang))
    log.info("COHORT: create started by user_id=%d", message.from_user.id)


@router.message(CohortCreateForm.name)
async def cohort_got_name(message: Message, state: FSMContext):
    """COHORT: Step 2 — save name, ask for description."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(name=message.text.strip())
    await state.set_state(CohortCreateForm.description)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_cohort_skip_desc"), callback_data="cohort_skip_desc")
    ]])
    await message.answer(t(lang, "cohort_ask_description"), reply_markup=skip_kb)


@router.callback_query(CohortCreateForm.description, F.data == "cohort_skip_desc")
async def cohort_skip_description(callback: CallbackQuery, state: FSMContext):
    """COHORT: Step 2 skip."""
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(description="")
    await state.set_state(CohortCreateForm.max_participants)
    await callback.answer()
    await callback.message.answer(t(lang, "cohort_ask_max"), reply_markup=cancel_keyboard(lang))


@router.message(CohortCreateForm.description)
async def cohort_got_description(message: Message, state: FSMContext):
    """COHORT: Step 2 — save description, ask for max."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(description=message.text.strip())
    await state.set_state(CohortCreateForm.max_participants)
    await message.answer(t(lang, "cohort_ask_max"), reply_markup=cancel_keyboard(lang))


@router.message(CohortCreateForm.max_participants)
async def cohort_got_max(message: Message, state: FSMContext):
    """COHORT: Step 3 — save max participants, ask for type."""
    lang = await get_user_lang(message.from_user.id)
    raw = message.text.strip()
    if raw == "":
        max_p = 12
    else:
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
    """COHORT: Step 4 — save type, create cohort, show invite link."""
    lang = await get_user_lang(callback.from_user.id)
    uid = callback.from_user.id
    type_map = {
        "cohort_type_course":      ("course",      t(lang, "btn_cohort_type_course")),
        "cohort_type_group":       ("group",        t(lang, "btn_cohort_type_group")),
        "cohort_type_supervision": ("supervision",  t(lang, "btn_cohort_type_supervision")),
    }
    type_key, type_display = type_map.get(callback.data, ("group", "Group"))
    data = await state.get_data()
    name = data["name"]
    description = data.get("description", "")
    max_p = data.get("max_participants", 12)
    cohort_id, token = await _create_cohort(uid, name, description, type_key, max_p)
    invite_link = f"https://t.me/{BOT_USERNAME}?start=cohort_{token}"
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_created", name=name, type=type_display, max=max_p, link=invite_link),
        parse_mode="HTML",
    )
    log.info("COHORT: created cohort_id=%d by user_id=%d token=%s", cohort_id, uid, token)


# ══ COHORT: /cohorts — list cohorts ════════════════════════════════════════

@router.message(Command("cohorts"))
async def cohorts_list(message: Message):
    """COHORT: Show all cohorts owned by this psychologist."""
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await _get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    lines = [t(lang, "cohort_list_title")]
    for cid, name, max_p in cohorts:
        count = await _get_member_count(cid)
        lines.append(t(lang, "cohort_list_row", name=name, count=count, max=max_p))
    await message.answer("\n".join(lines))
    log.info("COHORT: listed cohorts for user_id=%d count=%d", uid, len(cohorts))


# ══ COHORT: join confirmation callback ═════════════════════════════════════

@router.callback_query(F.data.startswith("cohort_join_"))
async def cohort_join_confirm(callback: CallbackQuery):
    """COHORT: User presses 'Join cohort' button from the invite link flow."""
    uid = callback.from_user.id
    token = callback.data[len("cohort_join_"):]
    lang = await get_user_lang(uid)
    row = await _get_cohort_by_token(token)
    if not row:
        await callback.answer(t(lang, "cohort_invalid_token"), show_alert=True)
        return
    cohort_id, psych_id, name, max_p = row
    if psych_id == uid:
        await callback.answer(t(lang, "cohort_is_leader"), show_alert=True)
        return
    if await _is_member(cohort_id, uid):
        await callback.answer(t(lang, "cohort_already_member"), show_alert=True)
        return
    if await _get_member_count(cohort_id) >= max_p:
        await callback.answer(t(lang, "cohort_full"), show_alert=True)
        return
    first_name = callback.from_user.first_name or f"user_{uid}"
    await _add_member(cohort_id, uid, first_name)
    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_join_confirm", name=name), parse_mode="HTML"
    )
    log.info("COHORT: user_id=%d joined cohort_id=%d", uid, cohort_id)


# ══ COHORT_SESSION: /cohort_schedule — FSM wizard ══════════════════════════

@router.message(Command("cohort_schedule"))
async def cohort_schedule_start(message: Message, state: FSMContext):
    """COHORT_SESSION: Start cohort session scheduling — pick cohort."""
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await _get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await state.set_state(CohortScheduleForm.cohort)
    await message.answer(
        t(lang, "cs_pick_cohort_schedule"),
        reply_markup=_cohort_picker_kb(cohorts, "csch_coh"),
    )


@router.callback_query(CohortScheduleForm.cohort, F.data.startswith("csch_coh_"))
async def cs_got_cohort(callback: CallbackQuery, state: FSMContext):
    """COHORT_SESSION: Cohort selected — ask for session number."""
    lang = await get_user_lang(callback.from_user.id)
    cohort_id = int(callback.data[len("csch_coh_"):])
    await state.update_data(cohort_id=cohort_id)
    await state.set_state(CohortScheduleForm.session_number)
    await callback.answer()
    await callback.message.answer(t(lang, "cs_ask_session_num"), reply_markup=cancel_keyboard(lang))


@router.message(CohortScheduleForm.session_number)
async def cs_got_session_number(message: Message, state: FSMContext):
    """COHORT_SESSION: Session number received — ask for date/time."""
    lang = await get_user_lang(message.from_user.id)
    raw = message.text.strip()
    try:
        num = int(raw)
        if num < 1:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "minutes_invalid"))
        return
    await state.update_data(session_number=num)
    await state.set_state(CohortScheduleForm.datetime_)
    await message.answer(t(lang, "cs_ask_datetime"), reply_markup=cancel_keyboard(lang))


@router.message(CohortScheduleForm.datetime_)
async def cs_got_datetime(message: Message, state: FSMContext):
    """COHORT_SESSION: Datetime received — validate, convert to UTC, ask topic."""
    lang = await get_user_lang(message.from_user.id)
    uid = message.from_user.id
    raw = message.text.strip()
    try:
        datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer(t(lang, "date_invalid"))
        return
    # COHORT_SESSION: convert from psychologist's local time to UTC for storage
    _, p_offset = await get_user_timezone(uid)
    scheduled_at_utc = local_to_utc(raw, p_offset)
    await state.update_data(scheduled_at_utc=scheduled_at_utc, scheduled_at_local=raw)
    await state.set_state(CohortScheduleForm.topic)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="csch_skip_topic")
    ]])
    await message.answer(t(lang, "cs_ask_topic"), reply_markup=skip_kb)


@router.callback_query(CohortScheduleForm.topic, F.data == "csch_skip_topic")
async def cs_skip_topic(callback: CallbackQuery, state: FSMContext):
    """COHORT_SESSION: Topic skipped — ask for link."""
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(topic="")
    await state.set_state(CohortScheduleForm.link)
    await callback.answer()
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="csch_skip_link")
    ]])
    await callback.message.answer(t(lang, "cs_ask_link"), reply_markup=skip_kb)


@router.message(CohortScheduleForm.topic)
async def cs_got_topic(message: Message, state: FSMContext):
    """COHORT_SESSION: Topic received — ask for link."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(topic=message.text.strip())
    await state.set_state(CohortScheduleForm.link)
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "cs_skip"), callback_data="csch_skip_link")
    ]])
    await message.answer(t(lang, "cs_ask_link"), reply_markup=skip_kb)


@router.callback_query(CohortScheduleForm.link, F.data == "csch_skip_link")
async def cs_skip_link(callback: CallbackQuery, state: FSMContext):
    """COHORT_SESSION: Link skipped — create session."""
    await state.update_data(link="")
    await _finalize_schedule(callback, state)


@router.message(CohortScheduleForm.link)
async def cs_got_link(message: Message, state: FSMContext):
    """COHORT_SESSION: Link received — create session."""
    await state.update_data(link=message.text.strip())
    await _finalize_schedule(message, state)


async def _finalize_schedule(source, state: FSMContext):
    """COHORT_SESSION: Create session row and confirm to psychologist."""
    uid = source.from_user.id
    lang = await get_user_lang(uid)
    data = await state.get_data()
    cohort_id = data["cohort_id"]
    session_number = data["session_number"]
    scheduled_at_utc = data["scheduled_at_utc"]
    scheduled_at_local = data["scheduled_at_local"]
    topic = data.get("topic", "")
    link = data.get("link", "")

    session_id = await _create_cohort_session(
        cohort_id, session_number, scheduled_at_utc, topic, link
    )

    # COHORT_SESSION: fetch cohort name for confirmation message
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM cohorts WHERE id = ?", (cohort_id,))
        cohort_row = await cur.fetchone()
    cohort_name = cohort_row[0] if cohort_row else str(cohort_id)

    topic_display = topic if topic else t(lang, "cs_no_topic")
    date_display = datetime.strptime(scheduled_at_local, "%Y-%m-%d %H:%M").strftime("%d.%m %H:%M")

    await state.clear()
    reply_text = t(
        lang, "cs_created",
        num=session_number, cohort=cohort_name,
        date=date_display, topic=topic_display,
    )
    if isinstance(source, CallbackQuery):
        await source.answer()
        await source.message.answer(reply_text)
    else:
        await source.answer(reply_text)
    log.info("COHORT_SESSION: created session_id=%d cohort_id=%d num=%d by user_id=%d",
             session_id, cohort_id, session_number, uid)


# ══ COHORT_SESSION: /cohort_sessions — list sessions ═══════════════════════

@router.message(Command("cohort_sessions"))
async def cohort_sessions_start(message: Message):
    """COHORT_SESSION: Show cohort picker to then display sessions list."""
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await _get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await message.answer(
        t(lang, "cs_pick_cohort_list"),
        reply_markup=_cohort_picker_kb(cohorts, "csl_coh"),
    )


@router.callback_query(F.data.startswith("csl_coh_"))
async def cohort_sessions_show(callback: CallbackQuery):
    """COHORT_SESSION: Cohort selected — show its sessions list."""
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    cohort_id = int(callback.data[len("csl_coh_"):])

    # COHORT_SESSION: fetch cohort name and verify ownership
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name FROM cohorts WHERE id = ? AND psychologist_id = ?",
            (cohort_id, uid),
        )
        row = await cur.fetchone()
    if not row:
        await callback.answer()
        return
    cohort_name = row[0]

    sessions = await _get_cohort_sessions(cohort_id)
    await callback.answer()
    if not sessions:
        await callback.message.answer(t(lang, "no_cs"))
        return

    # COHORT_SESSION: display times in psychologist's local timezone
    _, p_offset = await get_user_timezone(uid)
    status_key_map = {
        "scheduled":  "cs_status_scheduled",
        "completed":  "cs_status_completed",
        "cancelled":  "cs_status_cancelled",
    }
    lines = [t(lang, "cs_list_title", cohort=cohort_name)]
    for _sid, num, sched_utc, topic, _link, status in sessions:
        local_dt_str = utc_to_local(sched_utc, p_offset)
        date_display = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M").strftime("%d.%m %H:%M")
        topic_display = topic if topic else t(lang, "cs_no_topic")
        status_display = t(lang, status_key_map.get(status, "cs_status_scheduled"))
        lines.append(t(lang, "cs_row", num=num, date=date_display,
                       topic=topic_display, status=status_display))
    await callback.message.answer("\n".join(lines))
    log.info("COHORT_SESSION: sessions listed cohort_id=%d by user_id=%d", cohort_id, uid)


# ══ COHORT_SESSION: /cohort_attendance — FSM ══════════════════════════════

@router.message(Command("cohort_attendance"))
async def cohort_attendance_start(message: Message, state: FSMContext):
    """COHORT_SESSION: Start attendance — pick cohort."""
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    cohorts = await _get_cohorts_for_psych(uid)
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    await state.set_state(CohortAttendanceForm.cohort)
    await message.answer(
        t(lang, "cs_att_pick_cohort"),
        reply_markup=_cohort_picker_kb(cohorts, "catt_coh"),
    )


@router.callback_query(CohortAttendanceForm.cohort, F.data.startswith("catt_coh_"))
async def catt_got_cohort(callback: CallbackQuery, state: FSMContext):
    """COHORT_SESSION: Cohort selected — show session picker."""
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
    # COHORT_SESSION: build session picker keyboard
    rows = []
    _, p_offset = await get_user_timezone(callback.from_user.id)
    for sid, num, sched_utc, topic in sessions:
        local_dt = utc_to_local(sched_utc, p_offset)
        date_str = datetime.strptime(local_dt, "%Y-%m-%d %H:%M").strftime("%d.%m %H:%M")
        label = f"#{num} — {date_str}"
        if topic:
            label += f" — {topic[:20]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"catt_ses_{sid}")])
    await callback.message.answer(
        t(lang, "cs_att_pick_session"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(CohortAttendanceForm.session, F.data.startswith("catt_ses_"))
async def catt_got_session(callback: CallbackQuery, state: FSMContext):
    """COHORT_SESSION: Session selected — show attendance keyboard."""
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
    """COHORT_SESSION: Mark a member's attendance — save and refresh keyboard."""
    lang = await get_user_lang(callback.from_user.id)
    parts = callback.data[len("catt_mk_"):].split("_")
    if len(parts) != 3:
        await callback.answer()
        return
    session_id, member_id, new_status = int(parts[0]), int(parts[1]), parts[2]
    if new_status not in ("present", "absent", "pending"):
        await callback.answer()
        return

    await _upsert_attendance(session_id, member_id, new_status)

    # COHORT_SESSION: rebuild keyboard with updated status
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
        pass  # COHORT_SESSION: ignore if message unchanged
    log.info("COHORT_SESSION: attendance marked session_id=%d member_id=%d status=%s",
             session_id, member_id, new_status)
