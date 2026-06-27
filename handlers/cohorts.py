"""COHORT: Cohort management — create, list, and join via invite link."""

import logging
import secrets

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

from database import DB_PATH, get_user_lang, now_str
from keyboards import cancel_keyboard, cohort_type_keyboard
from states.cohort_states import CohortCreateForm
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


# ── COHORT: /cohort_create — FSM wizard ───────────────────────────────────

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

    # COHORT: skip button for description
    skip_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(lang, "btn_cohort_skip_desc"),
            callback_data="cohort_skip_desc",
        )
    ]])
    await message.answer(t(lang, "cohort_ask_description"), reply_markup=skip_kb)


@router.callback_query(CohortCreateForm.description, F.data == "cohort_skip_desc")
async def cohort_skip_description(callback: CallbackQuery, state: FSMContext):
    """COHORT: Step 2 skip — no description, go to max participants."""
    lang = await get_user_lang(callback.from_user.id)
    await state.update_data(description="")
    await state.set_state(CohortCreateForm.max_participants)
    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_ask_max"), reply_markup=cancel_keyboard(lang)
    )


@router.message(CohortCreateForm.description)
async def cohort_got_description(message: Message, state: FSMContext):
    """COHORT: Step 2 — save description, ask for max participants."""
    lang = await get_user_lang(message.from_user.id)
    await state.update_data(description=message.text.strip())
    await state.set_state(CohortCreateForm.max_participants)
    await message.answer(t(lang, "cohort_ask_max"), reply_markup=cancel_keyboard(lang))


@router.message(CohortCreateForm.max_participants)
async def cohort_got_max(message: Message, state: FSMContext):
    """COHORT: Step 3 — save max participants, ask for type."""
    lang = await get_user_lang(message.from_user.id)
    raw = message.text.strip()

    # COHORT: allow empty input to use default of 12
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

    # COHORT: map callback data to display name
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

    # COHORT: build invite link using bot username
    bot_username = BOT_USERNAME
    invite_link = f"https://t.me/{bot_username}?start=cohort_{token}"

    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_created", name=name, type=type_display, max=max_p, link=invite_link),
        parse_mode="HTML",
    )
    log.info("COHORT: created cohort_id=%d by user_id=%d token=%s", cohort_id, uid, token)


# ── COHORT: /cohorts — list all cohorts ───────────────────────────────────

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


# ── COHORT: join confirmation callback (triggered from deep-link in menu.py) ──

@router.callback_query(F.data.startswith("cohort_join_"))
async def cohort_join_confirm(callback: CallbackQuery):
    """COHORT: User presses 'Join cohort' button from the invite link flow."""
    uid = callback.from_user.id
    token = callback.data[len("cohort_join_"):]

    # COHORT: determine display language (fall back to 'en' if not a psychologist)
    lang = await get_user_lang(uid)

    row = await _get_cohort_by_token(token)
    if not row:
        await callback.answer(t(lang, "cohort_invalid_token"), show_alert=True)
        return

    cohort_id, psych_id, name, max_p = row

    # COHORT: psychologist cannot join their own cohort
    if psych_id == uid:
        await callback.answer(t(lang, "cohort_is_leader"), show_alert=True)
        return

    # COHORT: prevent duplicate membership
    if await _is_member(cohort_id, uid):
        await callback.answer(t(lang, "cohort_already_member"), show_alert=True)
        return

    # COHORT: enforce capacity limit
    if await _get_member_count(cohort_id) >= max_p:
        await callback.answer(t(lang, "cohort_full"), show_alert=True)
        return

    # COHORT: add member — use Telegram first_name as display name
    first_name = callback.from_user.first_name or f"user_{uid}"
    await _add_member(cohort_id, uid, first_name)

    await callback.answer()
    await callback.message.answer(
        t(lang, "cohort_join_confirm", name=name), parse_mode="HTML"
    )
    log.info("COHORT: user_id=%d joined cohort_id=%d", uid, cohort_id)
