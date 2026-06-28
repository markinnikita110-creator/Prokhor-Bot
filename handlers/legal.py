"""Legal handlers: consent gate, /privacy, /delete_my_data, /terms."""

import logging
import os
from datetime import datetime, timezone as _tz

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from database import DB_PATH, ensure_user, get_user_lang
from keyboards import lang_keyboard, main_menu_keyboard
from states import OnboardingForm
from translations import t

router = Router()
log = logging.getLogger(__name__)

CONSENT_VERSION = "1.0"

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


# ── DB helpers ──────────────────────────────────────────────────────────────

async def has_consent(user_id: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT 1 FROM user_consents WHERE user_id = ?", (user_id,)
            )
            return (await cur.fetchone()) is not None
    except Exception as e:
        log.error("has_consent error: %s", e)
        return False


async def save_consent(user_id: int) -> None:
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
        log.error("save_consent error: %s", e)


# ── Keyboard helpers ────────────────────────────────────────────────────────

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


# ── Consent callbacks ───────────────────────────────────────────────────────

@router.callback_query(F.data == "legal_accept")
async def legal_accept_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await callback.answer("✅ Принято")
    # Always clear any stale FSM state first
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
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(
        "❌ Прохор не может работать без вашего согласия.\n"
        "Если передумаете — напишите /start."
    )
    log.info("Consent declined: user_id=%d", callback.from_user.id)


# ── /privacy ────────────────────────────────────────────────────────────────

@router.message(Command("privacy"))
async def cmd_privacy(message: Message):
    await message.answer(PRIVACY_TEXT_RU)
    pdf_path = "./documents/privacy_policy.pdf"
    if os.path.exists(pdf_path):
        try:
            await message.answer_document(
                FSInputFile(pdf_path, filename="privacy_policy.pdf")
            )
        except Exception as e:
            log.error("Privacy PDF send error: %s", e)
    else:
        log.warning("Privacy PDF not found: %s", pdf_path)


# ── /terms ──────────────────────────────────────────────────────────────────

@router.message(Command("terms"))
async def cmd_terms(message: Message):
    pdf_path = "./documents/terms.pdf"
    if os.path.exists(pdf_path):
        try:
            await message.answer_document(
                FSInputFile(pdf_path, filename="terms.pdf")
            )
        except Exception as e:
            log.error("Terms PDF send error: %s", e)
    else:
        await message.answer(
            "📄 Условия использования будут доступны в ближайшее время."
        )


# ── /delete_my_data ─────────────────────────────────────────────────────────

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

    deleted_from: list[str] = []
    skipped: list[str] = []
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in await cur.fetchall()]

            for table in tables:
                try:
                    await db.execute(
                        f"DELETE FROM {table} WHERE user_id = ?", (uid,)
                    )
                    deleted_from.append(table)
                except Exception:
                    skipped.append(table)

            await db.commit()
        await state.clear()
        log.info(
            "Data deleted: user_id=%d tables=%s skipped=%s",
            uid, deleted_from, skipped,
        )
        await callback.message.answer(
            "✅ Все ваши данные удалены.\n"
            "Если захотите вернуться — напишите /start"
        )
    except Exception as e:
        log.error("delete_my_data error: %s", e)
        await callback.message.answer("⚠️ Произошла ошибка при удалении данных. Попробуйте позже.")


@router.callback_query(F.data == "legal_delete_cancel")
async def legal_delete_cancel_cb(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer("Отменено. Ваши данные на месте.")
