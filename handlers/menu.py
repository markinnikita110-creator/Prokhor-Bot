"""Main menu routing and /start."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import (
    DB_PATH,
    ensure_user,
    find_connected_client,
    format_offset,
    get_client_lang,
    get_user_lang,
    get_user_roles,
    make_token,
    now_str,
    reset_client_role,
    set_client_lang,
    set_user_lang,
    set_user_timezone,
)
from keyboards import (
    MENU_ANALYTICS,
    MENU_CHECKINS,
    MENU_CLIENTS,
    MENU_HOMEWORK,
    MENU_SESSIONS,
    MENU_SETTINGS,
    analytics_section_keyboard,
    checkins_section_keyboard,
    clients_section_keyboard,
    homework_section_keyboard,
    lang_keyboard,
    main_menu_keyboard,
    role_select_keyboard,
    sessions_section_keyboard,
    settings_keyboard,
    timezone_keyboard,
)
from states import OnboardingForm
from translations import t
from utils import parse_timezone
import aiosqlite

router = Router()
log = logging.getLogger(__name__)


# ── /start ─────────────────────────────────────────────────────────────────
@router.message(Command("start"))
async def start_handler(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = message.from_user.id

    # ── COHORT: Deep-link via cohort invite token ──────────────────────────
    if command.args and command.args.startswith("cohort_"):
        token = command.args[len("cohort_"):].strip()
        _psych_row, _ = await get_user_roles(uid)
        lang = await get_user_lang(uid) if _psych_row else "en"
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT id, psychologist_id, name, max_participants FROM cohorts WHERE invite_token = ?",
                (token,),
            )
            cohort_row = await cur.fetchone()
        if not cohort_row:
            await message.answer(t(lang, "cohort_invalid_token"))
            return
        cohort_id, psych_id, cohort_name, max_p = cohort_row
        # COHORT: psychologist cannot join their own cohort
        if psych_id == uid:
            await message.answer(t(lang, "cohort_is_leader"))
            return
        # COHORT: check if already a member
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT 1 FROM cohort_members WHERE cohort_id = ? AND telegram_id = ? AND status = 'active'",
                (cohort_id, uid),
            )
            already = await cur.fetchone()
        if already:
            await message.answer(t(lang, "cohort_already_member"))
            return
        # COHORT: show join prompt with confirmation button
        join_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(lang, "btn_cohort_join"),
                callback_data=f"cohort_join_{token}",
            )
        ]])
        await message.answer(
            t(lang, "cohort_join_prompt", name=cohort_name),
            reply_markup=join_kb,
            parse_mode="HTML",
        )
        log.info("COHORT: join prompt shown to user_id=%d cohort_id=%d", uid, cohort_id)
        return

    # ── Deep-link: connecting via invite token ─────────────────────────────
    if command.args and command.args.startswith("client_"):
        token = command.args.strip()
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT clients.id, clients.psychologist_id, psychologists.username "
                "FROM clients JOIN psychologists "
                "  ON clients.psychologist_id = psychologists.user_id "
                "WHERE clients.invite_token = ?", (token,)
            )
            row = await cur.fetchone()
        if not row:
            await message.answer(t("en", "invite_invalid"))
            return
        client_id, psych_id, psych_username = row

        # Block self-invite
        if psych_id == uid:
            lang = await get_user_lang(uid)
            await message.answer(t(lang, "self_invite_error"))
            log.warning("Self-invite blocked: user_id=%d", uid)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE clients SET telegram_id = ? WHERE id = ?", (uid, client_id)
            )
            await db.commit()
        psych_name = f"@{psych_username}" if psych_username else "your specialist"
        log.info("Client connected: telegram_id=%d client_id=%d", uid, client_id)

        # If user is also a psychologist → show role selector after connecting
        is_psych, _ = await get_user_roles(uid)
        lang = await get_user_lang(uid) if is_psych else "en"
        await message.answer(t(lang, "client_connected", specialist=psych_name))
        if is_psych:
            await message.answer(t(lang, "dual_role_select"),
                                 reply_markup=role_select_keyboard(lang))
        else:
            await message.answer(t("en", "language_select"), reply_markup=lang_keyboard())
        return

    # ── No deep-link: determine roles and route ────────────────────────────
    is_psych, client_row = await get_user_roles(uid)

    if is_psych and client_row:
        # Dual role → let the user pick which interface they want
        lang = await get_user_lang(uid)
        await message.answer(t(lang, "dual_role_select"),
                             reply_markup=role_select_keyboard(lang))
        log.info("Dual-role menu shown: user_id=%d", uid)
        return

    if client_row and not is_psych:
        # Pure client
        lang = await get_client_lang(uid)
        await message.answer(t(lang, "client_menu"))
        return

    # Psychologist (existing or new)
    is_new = await ensure_user(uid, message.from_user.username or "")
    if is_new:
        # Brand new user → onboarding step 1: choose language
        await state.set_state(OnboardingForm.language)
        await message.answer(t("en", "onboarding_welcome"), reply_markup=lang_keyboard())
        log.info("New psychologist onboarding started: user_id=%d", uid)
        return
    lang = await get_user_lang(uid)
    await message.answer(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))
    log.info("Psychologist started: user_id=%d", uid)


# ── Role selection callbacks ───────────────────────────────────────────────
@router.callback_query(F.data == "role_psych")
async def role_psych_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    await callback.answer()
    await callback.message.answer(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))
    log.info("Switched to psychologist role: user_id=%d", uid)


@router.callback_query(F.data == "role_client")
async def role_client_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_client_lang(uid)
    await callback.answer()
    await callback.message.answer(t(lang, "client_menu"))
    log.info("Switched to client role: user_id=%d", uid)


# ── /switch — show role selector (dual-role users only) ───────────────────
@router.message(Command("switch"))
async def switch_cmd(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    is_psych, client_row = await get_user_roles(uid)
    if is_psych and client_row:
        lang = await get_user_lang(uid)
        await message.answer(t(lang, "dual_role_select"),
                             reply_markup=role_select_keyboard(lang))
    else:
        lang = await get_user_lang(uid) if is_psych else await get_client_lang(uid)
        await message.answer(t(lang, "switch_no_dual_role"))


# ── /reset_role — remove client role, keep psychologist ───────────────────
@router.message(Command("reset_role"))
async def reset_role_cmd(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    removed = await reset_client_role(uid)
    lang = await get_user_lang(uid)
    if removed:
        await message.answer(t(lang, "client_role_reset"),
                             reply_markup=main_menu_keyboard(lang))
        log.info("Client role reset: user_id=%d", uid)
    else:
        await message.answer(t(lang, "client_role_not_found"))


# ── Language command (psychologist) ────────────────────────────────────────
@router.message(Command("language"))
async def language_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "language_select"), reply_markup=lang_keyboard())


# ══ Onboarding handlers ════════════════════════════════════════════════════
# State-filtered handlers take priority over the generic setlang_callback
# below because menu.router is registered first in handlers/__init__.py.

# ── Onboarding step 1: language selection ─────────────────────────────────
@router.callback_query(OnboardingForm.language, F.data.startswith("setlang_"))
async def onboarding_setlang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    uid = callback.from_user.id
    await set_user_lang(uid, lang)
    await state.set_state(OnboardingForm.timezone)
    await callback.answer()
    await callback.message.answer(
        t(lang, "ask_timezone_onboarding"),
        reply_markup=timezone_keyboard(lang, show_skip=True),
    )
    log.info("Onboarding lang set: user_id=%d lang=%s", uid, lang)


# ── Onboarding step 2a: preset timezone button ────────────────────────────
@router.callback_query(OnboardingForm.timezone, F.data.func(lambda d: d.startswith("tz_set_")))
async def onboarding_tz_set(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    try:
        offset_min = int(callback.data[len("tz_set_"):])
    except ValueError:
        await callback.answer()
        return
    tz_name = format_offset(offset_min)
    await set_user_timezone(uid, tz_name, offset_min)
    lang = await get_user_lang(uid)
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t(lang, "timezone_saved", tz=tz_name, offset=tz_name) + "\n\n" + t(lang, "welcome"),
        reply_markup=main_menu_keyboard(lang),
    )
    log.info("Onboarding tz set: user_id=%d offset_min=%d", uid, offset_min)


# ── Onboarding step 2b: "Enter manually" button ───────────────────────────
@router.callback_query(OnboardingForm.timezone, F.data == "tz_custom")
async def onboarding_tz_custom_btn(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    await state.set_state(OnboardingForm.timezone_custom)
    await callback.answer()
    await callback.message.answer(t(lang, "ask_timezone_custom"))


@router.message(OnboardingForm.timezone_custom)
async def onboarding_tz_text(message: Message, state: FSMContext):
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    parsed = parse_timezone(message.text.strip())
    if parsed is None:
        await message.answer(t(lang, "timezone_invalid"))
        return
    tz_name, offset_min = parsed
    await set_user_timezone(uid, tz_name, offset_min)
    offset_str = format_offset(offset_min)
    await state.clear()
    await message.answer(
        t(lang, "timezone_saved", tz=tz_name, offset=offset_str) + "\n\n" + t(lang, "welcome"),
        reply_markup=main_menu_keyboard(lang),
    )
    log.info("Onboarding custom tz: user_id=%d tz=%s", uid, tz_name)


# ── Onboarding step 2c: skip timezone ────────────────────────────────────
@router.callback_query(OnboardingForm.timezone, F.data == "tz_skip")
async def onboarding_tz_skip(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t(lang, "tz_skipped") + "\n\n" + t(lang, "welcome"),
        reply_markup=main_menu_keyboard(lang),
    )
    log.info("Onboarding tz skipped: user_id=%d", uid)


# ── Language callback (works for both psychologists and clients) ────────────
@router.callback_query(F.data.startswith("setlang_"))
async def setlang_callback(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    uid = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM psychologists WHERE user_id = ?", (uid,))
        is_psych = await cur.fetchone()
        cur = await db.execute("SELECT 1 FROM clients WHERE telegram_id = ?", (uid,))
        is_client = await cur.fetchone()
    if is_psych:
        await set_user_lang(uid, lang)
        await callback.answer()
        await callback.message.answer(t(lang, "language_saved"),
                                      reply_markup=main_menu_keyboard(lang))
    if is_client:
        await set_client_lang(uid, lang)
        await callback.answer()
        if not is_psych:
            await callback.message.answer(t(lang, "language_saved"))


# ── FSM cancel (global) ────────────────────────────────────────────────────
@router.callback_query(F.data == "fsm_cancel")
async def fsm_cancel(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.answer()
    await callback.message.answer(t(lang, "fsm_cancelled"))


# ── Noop (page indicator buttons) ─────────────────────────────────────────
@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# ── Main menu home callback ────────────────────────────────────────────────
@router.callback_query(F.data == "m_home")
async def main_menu_cb(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "welcome"), reply_markup=None)
    except Exception:
        await callback.message.answer(t(lang, "welcome"))


# ── Reply keyboard: route to sections ─────────────────────────────────────
@router.message(F.text.in_(MENU_CLIENTS))
async def menu_clients(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_clients"),
                         reply_markup=clients_section_keyboard(lang))


@router.message(F.text.in_(MENU_SESSIONS))
async def menu_sessions(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_sessions"),
                         reply_markup=sessions_section_keyboard(lang))


@router.message(F.text.in_(MENU_HOMEWORK))
async def menu_homework(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_homework"),
                         reply_markup=homework_section_keyboard(lang))


@router.message(F.text.in_(MENU_ANALYTICS))
async def menu_analytics(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_analytics"),
                         reply_markup=analytics_section_keyboard(lang))


@router.message(F.text.in_(MENU_CHECKINS))
async def menu_checkins(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_checkins"),
                         reply_markup=checkins_section_keyboard(lang))


@router.message(F.text.in_(MENU_SETTINGS))
async def menu_settings(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_settings"),
                         reply_markup=settings_keyboard(lang))


# ── Section callbacks (from inline Back buttons) ───────────────────────────
@router.callback_query(F.data == "m_clients")
async def cb_clients_section(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "section_clients"),
                                         reply_markup=clients_section_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "section_clients"),
                                      reply_markup=clients_section_keyboard(lang))


@router.callback_query(F.data == "m_sessions")
async def cb_sessions_section(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "section_sessions"),
                                         reply_markup=sessions_section_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "section_sessions"),
                                      reply_markup=sessions_section_keyboard(lang))
