"""Legal handlers: consent gate, /privacy, /delete_my_data, /terms.

Public API used by other modules:
  - CONSENT_TEXT_RU, consent_keyboard  → imported by handlers/menu.py
  - check_consent_status(uid)          → 'accepted' | 'declined' | 'none'
  - clear_consent_record(uid)          → deletes any existing record
  - ConsentMiddleware                  → registered on dp in main.py
"""

import logging
import os
from datetime import datetime, timezone as _tz
from typing import Any, Awaitable, Callable

import aiosqlite
from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,
    Message, TelegramObject,
)

from database import DB_PATH, ensure_user, get_user_lang
from keyboards import lang_keyboard, main_menu_keyboard
from states import OnboardingForm
from translations import t

router = Router()
log = logging.getLogger(__name__)

CONSENT_VERSION = "1.0"

# Commands and callbacks that never require consent check
_EXEMPT_COMMANDS  = frozenset({"start", "privacy", "terms", "consent", "admin"})
_EXEMPT_CALLBACKS = frozenset({"legal_accept", "legal_decline"})


# ─────────────────────────────────────────────────────────────────────────────
# Static text
# ─────────────────────────────────────────────────────────────────────────────

CONSENT_TEXT_RU = (
    "👋 Добро пожаловать в Прохора!\n\n"
    "Прохор — инструмент для организации административной рутины "
    "специалистов (психологов, коучей, педагогов).\n\n"
    "⚠️ Прохор не является медицинской информационной системой "
    "и не хранит медицинскую документацию.\n\n"
    "🔒 Для работы сохраняется ваш Telegram ID и данные, "
    "которые вы вносите самостоятельно.\n\n"
    "📄 Используя Прохора для работы с клиентами, вы подтверждаете, "
    "что самостоятельно получили их согласие на обработку данных.\n\n"
    "Подробнее: /privacy"
)

PRIVACY_TEXT_RU = (
    "🔒 Политика конфиденциальности\n\n"
    "Прохор сохраняет:\n"
    "- Ваш Telegram ID\n"
    "- Данные, которые вы вносите сами: имена клиентов, "
    "рабочие заметки, расписание\n\n"
    "Прохор НЕ сохраняет:\n"
    "- Содержимое ваших переписок в Telegram\n"
    "- Медицинские диагнозы или заключения\n"
    "- Аудио и видео материалы\n\n"
    "Ваши права:\n"
    "- Удалить все свои данные: /delete_my_data\n\n"
    "Прохор не является медицинской информационной системой.\n"
    "Специалист самостоятельно несёт ответственность за данные "
    "своих клиентов.\n\n"
    "Версия 1.0"
)

_BLOCKED_MSG = (
    "Для работы со мной необходимо принять условия. "
    "Напишите /start"
)


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

async def check_consent_status(user_id: int) -> str:
    """Return 'accepted', 'declined', or 'none'."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT version FROM user_consents WHERE user_id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
        if row is None:
            return "none"
        return "accepted" if row[0] == CONSENT_VERSION else "declined"
    except Exception as e:
        log.error("check_consent_status error user_id=%d: %s", user_id, e)
        return "none"


async def save_consent(user_id: int) -> None:
    """Save accepted consent (version=1.0)."""
    accepted_at = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_consents (user_id, accepted_at, version) "
                "VALUES (?, ?, ?)",
                (user_id, accepted_at, CONSENT_VERSION),
            )
            await db.commit()
        log.info("Consent saved: user_id=%d version=%s", user_id, CONSENT_VERSION)
    except Exception as e:
        log.error("save_consent error user_id=%d: %s", user_id, e)


async def save_decline(user_id: int) -> None:
    """Record that the user declined consent (version=declined)."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_consents (user_id, accepted_at, version) "
                "VALUES (?, ?, ?)",
                (user_id, "declined", "declined"),
            )
            await db.commit()
        log.info("Consent declined and recorded: user_id=%d", user_id)
    except Exception as e:
        log.error("save_decline error user_id=%d: %s", user_id, e)


async def clear_consent_record(user_id: int) -> None:
    """Delete any existing consent/decline record so the user can re-accept."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM user_consents WHERE user_id = ?", (user_id,)
            )
            await db.commit()
        log.info("Consent record cleared: user_id=%d", user_id)
    except Exception as e:
        log.error("clear_consent_record error user_id=%d: %s", user_id, e)


# ─────────────────────────────────────────────────────────────────────────────
# Consent middleware — blocks ALL handlers if user hasn't accepted
# ─────────────────────────────────────────────────────────────────────────────

class ConsentMiddleware(BaseMiddleware):
    """Outer middleware registered on dp.message and dp.callback_query.

    Passes through:
      - exempt commands (/start, /privacy, /terms)
      - exempt callbacks (legal_accept, legal_decline)
      - users with accepted consent

    Blocks (with a prompt to /start):
      - users who declined
      - users with no consent record
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        uid: int | None = None

        if isinstance(event, Message):
            if not event.from_user:
                return await handler(event, data)
            uid = event.from_user.id
            # Exempt commands
            if event.text:
                raw = event.text.lstrip("/").split("@")[0].split()[0].lower()
                if event.text.startswith("/") and raw in _EXEMPT_COMMANDS:
                    return await handler(event, data)

        elif isinstance(event, CallbackQuery):
            if not event.from_user:
                return await handler(event, data)
            uid = event.from_user.id
            # Exempt consent-gate callbacks
            if event.data and event.data in _EXEMPT_CALLBACKS:
                return await handler(event, data)

        else:
            return await handler(event, data)

        if uid is None:
            return await handler(event, data)

        status = await check_consent_status(uid)
        if status == "accepted":
            return await handler(event, data)

        # User hasn't accepted — block and prompt
        if isinstance(event, Message):
            await event.answer(_BLOCKED_MSG)
        elif isinstance(event, CallbackQuery):
            await event.answer(_BLOCKED_MSG, show_alert=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Keyboard helpers
# ─────────────────────────────────────────────────────────────────────────────

def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принимаю условия", callback_data="legal_accept"),
        InlineKeyboardButton(text="❌ Не принимаю",      callback_data="legal_decline"),
    ]])


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Да, удалить всё", callback_data="legal_delete_confirm"),
        InlineKeyboardButton(text="Отмена",             callback_data="legal_delete_cancel"),
    ]])


# ─────────────────────────────────────────────────────────────────────────────
# Consent callbacks
# ─────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "legal_accept")
async def legal_accept_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await callback.answer("✅ Принято")
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await save_consent(uid)

    try:
        is_new = await ensure_user(uid, callback.from_user.username or "")
    except Exception as e:
        log.error("legal_accept_cb ensure_user failed user_id=%d: %s", uid, e)
        is_new = False

    if is_new:
        await state.set_state(OnboardingForm.language)
        await callback.message.answer(
            t("en", "onboarding_welcome"), reply_markup=lang_keyboard()
        )
        log.info("Consent accepted → onboarding: user_id=%d", uid)
    else:
        lang = await get_user_lang(uid)
        await callback.message.answer(
            t(lang, "welcome"), reply_markup=main_menu_keyboard(lang)
        )
        log.info("Consent accepted → main menu: user_id=%d lang=%s", uid, lang)


@router.callback_query(F.data == "legal_decline")
async def legal_decline_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await save_decline(uid)
    await callback.message.answer(
        "Без согласия я не могу работать.\n"
        "Если передумаете — напишите /start."
    )
    log.info("Consent declined: user_id=%d", uid)


_FALLBACK_MSG = "📄 Документ временно недоступен.\nНапишите нам: @nick_mnm"


async def _send_document(message: Message, path: str, caption: str, label: str) -> None:
    """Send a PDF document; fall back gracefully if the file is missing."""
    if os.path.exists(path):
        try:
            await message.answer_document(
                FSInputFile(path),
                caption=caption,
            )
        except Exception as e:
            log.error("%s PDF send error: %s", label, e)
            await message.answer(_FALLBACK_MSG)
    else:
        log.warning("%s PDF not found: %s", label, path)
        await message.answer(_FALLBACK_MSG)


# ─────────────────────────────────────────────────────────────────────────────
# /privacy
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("privacy"))
async def cmd_privacy(message: Message):
    await message.answer(PRIVACY_TEXT_RU)
    await _send_document(
        message,
        path="documents/privacy_policy.pdf",
        caption="📄 Политика конфиденциальности Прохора",
        label="Privacy",
    )


# ─────────────────────────────────────────────────────────────────────────────
# /terms
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("terms"))
async def cmd_terms(message: Message):
    await message.answer("📋 Пользовательское соглашение (оферта)")
    await _send_document(
        message,
        path="documents/terms.pdf",
        caption="📄 Пользовательское соглашение Прохора",
        label="Terms",
    )


# ─────────────────────────────────────────────────────────────────────────────
# /consent
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("consent"))
async def cmd_consent(message: Message):
    await message.answer("✍️ Согласие на обработку персональных данных")
    await _send_document(
        message,
        path="documents/consent.pdf",
        caption="📄 Согласие на обработку ПД",
        label="Consent",
    )


# ─────────────────────────────────────────────────────────────────────────────
# /delete_my_data
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("delete_my_data"))
async def cmd_delete_my_data(message: Message):
    await message.answer(
        "⚠️ Вы уверены? Все ваши данные будут безвозвратно удалены.\n"
        "Это действие нельзя отменить.",
        reply_markup=delete_confirm_keyboard(),
    )


@router.callback_query(F.data == "legal_delete_confirm")
async def legal_delete_confirm_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    try:
        async with aiosqlite.connect(DB_PATH) as db:

            # ── 1. Tables that reference client_id (must go before clients) ──────
            # notes, checkins, homeworks, client_tags have no psychologist_id column;
            # they link to the psychologist only through clients.psychologist_id.
            for tbl in ("client_tags", "notes", "checkins", "homeworks"):
                await db.execute(
                    f"DELETE FROM {tbl} WHERE client_id IN "
                    f"(SELECT id FROM clients WHERE psychologist_id = ?)",
                    (uid,),
                )

            # ── 2. Cohort cascade (must go before cohorts) ────────────────────────
            # cohort_session_notes has a direct psychologist_id column.
            await db.execute(
                "DELETE FROM cohort_session_notes WHERE psychologist_id = ?",
                (uid,),
            )
            # cohort_attendance links through cohort_sessions → cohorts.
            await db.execute(
                "DELETE FROM cohort_attendance WHERE session_id IN ("
                "  SELECT id FROM cohort_sessions WHERE cohort_id IN ("
                "    SELECT id FROM cohorts WHERE psychologist_id = ?"
                "  )"
                ")",
                (uid,),
            )
            for tbl in ("cohort_sessions", "cohort_checkins",
                        "cohort_checkin_configs", "cohort_members"):
                await db.execute(
                    f"DELETE FROM {tbl} WHERE cohort_id IN "
                    f"(SELECT id FROM cohorts WHERE psychologist_id = ?)",
                    (uid,),
                )

            # ── 3. Tables with psychologist_id ────────────────────────────────────
            for tbl in ("cohorts", "supervision_cases", "auto_checkins",
                        "reminders", "sessions", "clients"):
                await db.execute(
                    f"DELETE FROM {tbl} WHERE psychologist_id = ?", (uid,)
                )

            # ── 4. Tables with psych_id (booking system) ──────────────────────────
            for tbl in ("availability_exceptions", "availability_rules",
                        "booking_profile"):
                await db.execute(
                    f"DELETE FROM {tbl} WHERE psych_id = ?", (uid,)
                )
            # booking_requests_log: delete both as psychologist AND as booking client
            await db.execute(
                "DELETE FROM booking_requests_log WHERE psych_id = ? OR client_telegram_id = ?",
                (uid, uid),
            )

            # ── 5. Tables with user_id (psychologists row last) ───────────────────
            for tbl in ("user_plans", "user_consents", "psychologists"):
                await db.execute(
                    f"DELETE FROM {tbl} WHERE user_id = ?", (uid,)
                )

            # ── 7. FSM storage ────────────────────────────────────────────────────
            # Key format: bot_id:user_id:chat_id:thread_id::destiny
            # Extract the 2nd colon-delimited segment and compare exactly — avoids
            # matching other users whose IDs happen to be a substring of this uid.
            await db.execute(
                "DELETE FROM fsm_storage WHERE "
                "CAST(SUBSTR(key, INSTR(key,':')+1, "
                "INSTR(SUBSTR(key, INSTR(key,':')+1), ':')-1) AS INTEGER) = ?",
                (uid,),
            )

            await db.commit()

        # ── Verification: one probe per ownership family ───────────────────────
        # psychologist_id family → clients + sessions
        # psych_id family        → booking_profile
        # user_id family         → psychologists (the root row)
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM clients WHERE psychologist_id = ?", (uid,)
            )
            clients_left = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM sessions WHERE psychologist_id = ?", (uid,)
            )
            sessions_left = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM cohorts WHERE psychologist_id = ?", (uid,)
            )
            cohorts_left = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM booking_profile WHERE psych_id = ?", (uid,)
            )
            booking_left = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM psychologists WHERE user_id = ?", (uid,)
            )
            psych_row_left = (await cur.fetchone())[0]

        residual = (
            clients_left + sessions_left + cohorts_left
            + booking_left + psych_row_left
        )
        if residual > 0:
            log.error(
                "delete_my_data INCOMPLETE: user_id=%d "
                "clients=%d sessions=%d cohorts=%d booking=%d psych_row=%d",
                uid, clients_left, sessions_left,
                cohorts_left, booking_left, psych_row_left,
            )
            await callback.message.answer(
                "⚠️ Удаление выполнено не полностью. Обратитесь в поддержку: @nick_mnm"
            )
            return

        await state.clear()
        log.info("delete_my_data SUCCESS: user_id=%d", uid)
        await callback.message.answer(
            "✅ Все ваши данные удалены.\n"
            "Если захотите вернуться — напишите /start"
        )

    except Exception as e:
        log.error("delete_my_data error: user_id=%d %s", uid, e)
        await callback.message.answer(
            "⚠️ Произошла ошибка при удалении данных. Попробуйте позже."
        )


@router.callback_query(F.data == "legal_delete_cancel")
async def legal_delete_cancel_cb(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer("Отменено. Ваши данные на месте.")
