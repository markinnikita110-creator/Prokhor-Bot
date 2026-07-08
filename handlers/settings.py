"""Settings section: language, timezone, about."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.db.users_repository import get_user_lang, set_user_lang
from core.db.clients_repository import set_client_lang
from keyboards import lang_keyboard, main_menu_keyboard, settings_keyboard, timezone_keyboard
from translations import t

router = Router()


@router.callback_query(F.data == "m_settings")
async def settings_section(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "section_settings"),
                                         reply_markup=settings_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "section_settings"),
                                      reply_markup=settings_keyboard(lang))


@router.callback_query(F.data == "st_lang")
async def settings_language(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(t(lang, "language_select"), reply_markup=lang_keyboard())


@router.callback_query(F.data == "st_tz")
async def settings_timezone_kb(callback: CallbackQuery, state: FSMContext):
    """Show preset timezone keyboard from Settings."""
    lang = await get_user_lang(callback.from_user.id)
    await state.clear()  # cancel any in-progress FSM (e.g. custom tz input)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "ask_timezone_settings"),
                                         reply_markup=timezone_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "ask_timezone_settings"),
                                      reply_markup=timezone_keyboard(lang))


@router.callback_query(F.data == "st_about")
async def settings_about(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "about_text"),
                                         reply_markup=settings_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "about_text"),
                                      reply_markup=settings_keyboard(lang))
