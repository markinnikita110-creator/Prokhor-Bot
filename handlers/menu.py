"""Main menu routing and /start.
MENU: Hierarchical reply keyboard navigation.
"""

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from database import (
    DB_PATH,
    OFFSET_TO_IANA,
    ensure_user,
    format_offset,
    get_user_lang,
    make_token,
    needs_tz_confirm,
    now_str,
    set_user_lang,
    set_user_timezone,
)
from core.db.clients_repository import (
    find_connected_client,
    get_client_lang,
    get_user_roles,
    needs_tz_confirm_client,
    reset_client_role,
    set_client_lang,
)
from handlers.legal import (
    CONSENT_TEXT_RU, consent_keyboard,
    check_consent_status, clear_consent_record,
)
from keyboards import (
    # MENU: new hierarchical menu constants
    MENU_INDIVIDUAL, MENU_COHORTS_BTN, MENU_SUMMARY, MENU_SETTINGS_BTN, MENU_BACK,
    MENU_IND_ADD_CLIENT, MENU_IND_CLIENT_LIST, MENU_IND_NEW_NOTE,
    MENU_IND_SCHEDULE, MENU_IND_REMINDERS,
    MENU_COH_CREATE, MENU_COH_LIST,
    MENU_SUM_CLIENTS, MENU_SUM_COHORTS, MENU_SUM_STATS,
    MENU_SET_LANGUAGE, MENU_SET_TIMEZONE, MENU_SET_NOTIFS, MENU_SET_TARIFF,
    MENU_SET_BOOKING,
    # keyboard builders
    analytics_section_keyboard,
    cancel_keyboard,
    checkins_section_keyboard,
    clients_section_keyboard,
    cohorts_menu_keyboard,
    individual_menu_keyboard,
    lang_keyboard,
    main_menu_keyboard,
    role_select_keyboard,
    sessions_section_keyboard,
    settings_menu_keyboard,
    summary_menu_keyboard,
    timezone_keyboard,
)
from states import OnboardingForm
from states.cohort_states import CohortCreateForm
from translations import t
from utils import parse_timezone

router = Router()
log = logging.getLogger(__name__)


# ── /start ─────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def start_handler(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = message.from_user.id

    # LEGAL: show consent gate for new or declined users
    consent = await check_consent_status(uid)
    if consent == "declined":
        # User previously declined — clear old record so they can re-accept
        await clear_consent_record(uid)
        await message.answer(CONSENT_TEXT_RU, reply_markup=consent_keyboard())
        log.info("Consent gate shown (re-consent after decline): user_id=%d", uid)
        return
    elif consent == "none":
        await message.answer(CONSENT_TEXT_RU, reply_markup=consent_keyboard())
        log.info("Consent gate shown (new user): user_id=%d", uid)
        return
    # consent == "accepted": fall through to normal bot logic

    # BOOKING: self-booking deep-link via public profile slug
    if command.args and command.args.startswith("book_"):
        slug = command.args[len("book_"):].strip()
        from handlers.booking import show_booking_card
        await show_booking_card(message, slug, state)
        return

    # COHORT: Deep-link via cohort invite token
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
        if psych_id == uid:
            await message.answer(t(lang, "cohort_is_leader"))
            return
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT 1 FROM cohort_members WHERE cohort_id = ? AND telegram_id = ? AND status = 'active'",
                (cohort_id, uid),
            )
            already = await cur.fetchone()
        if already:
            await message.answer(t(lang, "cohort_already_member"))
            return
        join_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(lang, "btn_cohort_join"),
                callback_data=f"cohort_join_{token}",
            )
        ]])
        await message.answer(
            t(lang, "cohort_join_prompt", name=cohort_name),
            reply_markup=join_kb, parse_mode="HTML",
        )
        log.info("COHORT: join prompt shown to user_id=%d cohort_id=%d", uid, cohort_id)
        return

    # Deep-link: connecting via client invite token
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
        is_psych, _ = await get_user_roles(uid)
        lang = await get_user_lang(uid) if is_psych else "en"
        await message.answer(t(lang, "client_connected", specialist=psych_name))
        if is_psych:
            await message.answer(t(lang, "dual_role_select"),
                                 reply_markup=role_select_keyboard(lang))
        else:
            await message.answer(t("en", "language_select"), reply_markup=lang_keyboard())
        return

    # No deep-link: determine roles and route
    is_psych, client_row = await get_user_roles(uid)

    if is_psych and client_row:
        lang = await get_user_lang(uid)
        await message.answer(t(lang, "dual_role_select"),
                             reply_markup=role_select_keyboard(lang))
        log.info("Dual-role menu shown: user_id=%d", uid)
        return

    if client_row and not is_psych:
        lang = await get_client_lang(uid)
        if await needs_tz_confirm_client(uid):
            await message.answer(t(lang, "tz_confirm_prompt"),
                                 reply_markup=timezone_keyboard(lang))
        await message.answer(t(lang, "client_menu"))
        return

    is_new = await ensure_user(uid, message.from_user.username or "")
    if is_new:
        await state.set_state(OnboardingForm.language)
        await message.answer(t("en", "onboarding_welcome"), reply_markup=lang_keyboard())
        log.info("New psychologist onboarding started: user_id=%d", uid)
        return
    lang = await get_user_lang(uid)
    if await needs_tz_confirm(uid):
        await message.answer(t(lang, "tz_confirm_prompt"),
                             reply_markup=timezone_keyboard(lang))
    await message.answer(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))
    log.info("Psychologist started: user_id=%d", uid)


# ── Role selection callbacks ───────────────────────────────────────────────

@router.callback_query(F.data == "role_psych")
async def role_psych_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    await callback.answer()
    if await needs_tz_confirm(uid):
        await callback.message.answer(t(lang, "tz_confirm_prompt"),
                                      reply_markup=timezone_keyboard(lang))
    await callback.message.answer(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))
    log.info("Switched to psychologist role: user_id=%d", uid)


@router.callback_query(F.data == "role_client")
async def role_client_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = await get_client_lang(uid)
    await callback.answer()
    if await needs_tz_confirm_client(uid):
        await callback.message.answer(t(lang, "tz_confirm_prompt"),
                                      reply_markup=timezone_keyboard(lang))
    await callback.message.answer(t(lang, "client_menu"))
    log.info("Switched to client role: user_id=%d", uid)


# ── /switch — show role selector ──────────────────────────────────────────

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


# ── /reset_role ───────────────────────────────────────────────────────────

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


# ── /language ─────────────────────────────────────────────────────────────

@router.message(Command("language"))
async def language_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "language_select"), reply_markup=lang_keyboard())


# ══ Onboarding handlers ════════════════════════════════════════════════════

@router.callback_query(OnboardingForm.language, F.data.startswith("setlang_"))
async def onboarding_setlang(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    lang = callback.data.split("_")[1]
    uid = callback.from_user.id
    await set_user_lang(uid, lang)
    await state.set_state(OnboardingForm.timezone)
    await callback.message.answer(
        t(lang, "ask_timezone_onboarding"),
        reply_markup=timezone_keyboard(lang, show_skip=True),
    )
    log.info("Onboarding lang set: user_id=%d lang=%s", uid, lang)


@router.callback_query(OnboardingForm.timezone, F.data.func(lambda d: d.startswith("tz_set_")))
async def onboarding_tz_set(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    try:
        offset_min = int(callback.data[len("tz_set_"):])
    except ValueError:
        await callback.answer()
        return
    tz_name = OFFSET_TO_IANA.get(offset_min, format_offset(offset_min))
    await set_user_timezone(uid, tz_name, offset_min)
    lang = await get_user_lang(uid)
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        t(lang, "timezone_saved", tz=tz_name, offset=format_offset(offset_min)) + "\n\n" + t(lang, "welcome"),
        reply_markup=main_menu_keyboard(lang),
    )
    log.info("Onboarding tz set: user_id=%d tz=%s", uid, tz_name)


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


# ── Language callback ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("setlang_"))
async def setlang_callback(callback: CallbackQuery):
    # Always answer immediately so the button stops spinning
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    lang = callback.data.split("_")[1]   # "en" or "ru"
    uid  = callback.from_user.id

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT 1 FROM psychologists WHERE user_id = ?", (uid,))
            is_psych = await cur.fetchone()
            cur = await db.execute(
                "SELECT 1 FROM clients WHERE telegram_id = ?", (uid,))
            is_client = await cur.fetchone()

        if is_psych:
            await set_user_lang(uid, lang)

        if is_client:
            await set_client_lang(uid, lang)

        if is_psych:
            await callback.message.answer(
                t(lang, "language_saved"),
                reply_markup=main_menu_keyboard(lang),
            )
        elif is_client:
            await callback.message.answer(t(lang, "language_saved"))
        else:
            # User record not found yet — still acknowledge the change
            log.warning("setlang_callback: user_id=%d not in psychologists or clients", uid)
            await callback.message.answer(
                t(lang, "language_saved"),
                reply_markup=main_menu_keyboard(lang),
            )

        log.info("Language set: user_id=%d lang=%s psych=%s client=%s",
                 uid, lang, bool(is_psych), bool(is_client))
    except Exception as e:
        log.error("setlang_callback error user_id=%d: %s", uid, e)
        await callback.message.answer("⚠️ Не удалось сохранить язык. Попробуйте ещё раз.")


# ── FSM cancel (global) ────────────────────────────────────────────────────

@router.callback_query(F.data == "fsm_cancel")
async def fsm_cancel(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()
    await callback.answer()
    await callback.message.answer(t(lang, "fsm_cancelled"),
                                  reply_markup=main_menu_keyboard(lang))


# ── Noop ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# ── Main menu home callback ────────────────────────────────────────────────

@router.callback_query(F.data == "m_home")
async def main_menu_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    lang = await get_user_lang(uid)
    await state.clear()
    await callback.answer()
    if await needs_tz_confirm(uid):
        await callback.message.answer(t(lang, "tz_confirm_prompt"),
                                      reply_markup=timezone_keyboard(lang))
    await callback.message.answer(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))


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


# ══ MENU: New hierarchical routing ════════════════════════════════════════

# ── Main menu: top-level buttons ──────────────────────────────────────────

@router.message(F.text.in_(MENU_INDIVIDUAL))
async def menu_individual(message: Message):
    # MENU: show Individual submenu
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_individual"),
                         reply_markup=individual_menu_keyboard(lang))


@router.message(F.text.in_(MENU_COHORTS_BTN))
async def menu_cohorts_btn(message: Message):
    # MENU: show Cohorts submenu
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_cohorts_menu"),
                         reply_markup=cohorts_menu_keyboard(lang))


@router.message(F.text.in_(MENU_SUMMARY))
async def menu_summary(message: Message):
    # MENU: show Summary submenu
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_summary"),
                         reply_markup=summary_menu_keyboard(lang))


@router.message(F.text.in_(MENU_SETTINGS_BTN))
async def menu_settings_btn(message: Message):
    # MENU: show Settings submenu
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_settings_menu"),
                         reply_markup=settings_menu_keyboard(lang))


@router.message(F.text.in_(MENU_BACK))
async def menu_back(message: Message):
    # MENU: any Back button → return to main menu
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "welcome"), reply_markup=main_menu_keyboard(lang))


# ── Individual submenu buttons ─────────────────────────────────────────────

@router.message(F.text.in_(MENU_IND_ADD_CLIENT))
async def menu_ind_add_client(message: Message, state: FSMContext):
    # MENU: directly start add-client flow
    from states import AddClientForm
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(AddClientForm.name)
    await message.answer(t(lang, "ask_client_name"), reply_markup=cancel_keyboard(lang))


@router.message(F.text.in_(MENU_IND_CLIENT_LIST))
async def menu_ind_client_list(message: Message):
    # MENU: show inline client list
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_clients"),
                         reply_markup=clients_section_keyboard(lang))


@router.message(F.text.in_(MENU_IND_NEW_NOTE))
async def menu_ind_new_note(message: Message):
    # MENU: show client section (user picks client then adds note)
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_clients"),
                         reply_markup=clients_section_keyboard(lang))


@router.message(F.text.in_(MENU_IND_SCHEDULE))
async def menu_ind_schedule(message: Message):
    # MENU: show sessions section
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_sessions"),
                         reply_markup=sessions_section_keyboard(lang))


@router.message(F.text.in_(MENU_IND_REMINDERS))
async def menu_ind_reminders(message: Message):
    # MENU: show check-ins / reminders section
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_checkins"),
                         reply_markup=checkins_section_keyboard(lang))


# ── Cohorts submenu buttons ────────────────────────────────────────────────

@router.message(F.text.in_(MENU_COH_CREATE))
async def menu_coh_create(message: Message, state: FSMContext):
    # MENU: directly start cohort-create FSM
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(CohortCreateForm.name)
    await message.answer(t(lang, "cohort_ask_name"), reply_markup=cancel_keyboard(lang))


@router.message(F.text.in_(MENU_COH_LIST))
async def menu_coh_list(message: Message):
    # MENU: show cohort list as inline picker → leads to cohort_action_keyboard
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM cohorts WHERE psychologist_id = ? ORDER BY created_at DESC",
            (uid,),
        )
        cohorts = await cur.fetchall()
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    rows = [[InlineKeyboardButton(text=name, callback_data=f"cv2_pick_{cid}")]
            for cid, name in cohorts]
    await message.answer(t(lang, "cohort_list_title"),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ── Summary submenu buttons ────────────────────────────────────────────────

@router.message(F.text.in_(MENU_SUM_CLIENTS))
async def menu_sum_clients(message: Message):
    # MENU: client section in summary context
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_clients"),
                         reply_markup=clients_section_keyboard(lang))


@router.message(F.text.in_(MENU_SUM_COHORTS))
async def menu_sum_cohorts(message: Message):
    # MENU: cohort list for summary/stats view
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM cohorts WHERE psychologist_id = ? ORDER BY created_at DESC",
            (uid,),
        )
        cohorts = await cur.fetchall()
    if not cohorts:
        await message.answer(t(lang, "no_cohorts"))
        return
    rows = [[InlineKeyboardButton(text=name, callback_data=f"cv2_pick_{cid}")]
            for cid, name in cohorts]
    await message.answer(t(lang, "cohort_list_title"),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.message(F.text.in_(MENU_SUM_STATS))
async def menu_sum_stats(message: Message):
    # MENU: analytics/dashboard
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "section_analytics"),
                         reply_markup=analytics_section_keyboard(lang))


# ── Settings submenu buttons ───────────────────────────────────────────────

@router.message(F.text.in_(MENU_SET_LANGUAGE))
async def menu_set_language(message: Message):
    # MENU: language picker
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "language_select"), reply_markup=lang_keyboard())


@router.message(F.text.in_(MENU_SET_TIMEZONE))
async def menu_set_timezone(message: Message):
    # MENU: timezone picker
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "ask_timezone_settings"),
                         reply_markup=timezone_keyboard(lang))


@router.message(F.text.in_(MENU_SET_TARIFF))
async def menu_set_tariff(message: Message):
    # MENU: open tariff screen with inline keyboard
    import aiosqlite
    from database import DB_PATH
    from keyboards import tariff_keyboard
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT plan, expires_at FROM user_plans WHERE user_id = ?", (uid,)
        )
        row = await cur.fetchone()
    plan_name = row[0] if row else "start"
    expires_at = row[1] if row else None
    is_pro = plan_name == "pro"
    if is_pro:
        expires_str = (f"\n до {expires_at}" if lang == "ru" else f"\n until {expires_at}") if expires_at else ""
        text = t(lang, "tariff_screen_pro", expires=expires_str)
    else:
        text = t(lang, "tariff_screen_start")
    await message.answer(text, parse_mode="Markdown",
                         reply_markup=tariff_keyboard(lang, is_pro=is_pro))


@router.message(F.text.in_(MENU_SET_NOTIFS))
async def menu_set_notifs(message: Message):
    # MENU: notification settings (stub)
    lang = await get_user_lang(message.from_user.id)
    await message.answer(t(lang, "notifs_not_implemented"))


@router.message(F.text.in_(MENU_SET_BOOKING))
async def menu_set_booking(message: Message, state: FSMContext):
    # MENU: booking settings screen
    lang = await get_user_lang(message.from_user.id)
    from handlers.booking_settings import _booking_settings_screen
    await _booking_settings_screen(message, message.from_user.id, lang, edit=False)

