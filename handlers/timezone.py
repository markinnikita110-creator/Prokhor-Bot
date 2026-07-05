"""Timezone management: /timezone command, preset keyboard callbacks, custom text input."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    OFFSET_TO_IANA,
    format_offset,
    get_user_lang,
    get_user_timezone,
    set_user_timezone,
)
from core.db.clients_repository import get_client_lang, get_user_roles, set_client_timezone
from keyboards import timezone_keyboard
from states import TimezoneInputForm
from translations import t
from utils import parse_timezone

router = Router()
log = logging.getLogger(__name__)


@router.message(Command("timezone"))
async def timezone_cmd(message: Message):
    uid = message.from_user.id
    is_psych, client_row = await get_user_roles(uid)

    if is_psych:
        lang = await get_user_lang(uid)
    elif client_row:
        lang = await get_client_lang(uid)
    else:
        lang = "en"

    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        # No argument: show the preset keyboard
        await message.answer(t(lang, "ask_timezone_settings"),
                             reply_markup=timezone_keyboard(lang))
        return

    # Argument provided: parse and save directly
    parsed = parse_timezone(args[1])
    if parsed is None:
        await message.answer(t(lang, "timezone_invalid"))
        return

    tz_name, offset_minutes = parsed
    offset_str = format_offset(offset_minutes)
    if is_psych:
        await set_user_timezone(uid, tz_name, offset_minutes)
    if client_row:
        await set_client_timezone(uid, tz_name, offset_minutes)

    await message.answer(t(lang, "timezone_saved", tz=tz_name, offset=offset_str))
    log.info("Timezone set via /timezone: user_id=%d tz=%s offset_min=%d",
             uid, tz_name, offset_minutes)


# ── tz_set_<minutes> — preset button (settings / non-onboarding path) ─────
# Onboarding takes priority because menu.router is registered first with a
# state filter; this handler catches the same callback with no active state.
@router.callback_query(F.data.regexp(r'^tz_set_-?\d+$'))
async def tz_set_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    offset_min = int(callback.data.split("_")[2])
    tz_name = OFFSET_TO_IANA.get(offset_min, format_offset(offset_min))
    is_psych, client_row = await get_user_roles(uid)
    if is_psych:
        await set_user_timezone(uid, tz_name, offset_min)
    if client_row:
        await set_client_timezone(uid, tz_name, offset_min)
    lang = await get_user_lang(uid) if is_psych else await get_client_lang(uid)
    await callback.answer()
    await callback.message.answer(
        t(lang, "timezone_saved", tz=tz_name, offset=format_offset(offset_min))
    )
    log.info("Timezone set via preset: user_id=%d offset_min=%d", uid, offset_min)


# ── tz_custom — "Enter manually" button (settings path) ───────────────────
@router.callback_query(F.data == "tz_custom")
async def tz_custom_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    is_psych, client_row = await get_user_roles(uid)
    lang = await get_user_lang(uid) if is_psych else await get_client_lang(uid)
    await state.set_state(TimezoneInputForm.input)
    await callback.answer()
    await callback.message.answer(t(lang, "ask_timezone_custom"))


# ── TimezoneInputForm.input — manual text input (settings path) ───────────
@router.message(TimezoneInputForm.input)
async def tz_input_handler(message: Message, state: FSMContext):
    uid = message.from_user.id
    is_psych, client_row = await get_user_roles(uid)
    lang = await get_user_lang(uid) if is_psych else await get_client_lang(uid)
    parsed = parse_timezone(message.text.strip())
    if parsed is None:
        await message.answer(t(lang, "timezone_invalid"))
        return
    tz_name, offset_min = parsed
    offset_str = format_offset(offset_min)
    if is_psych:
        await set_user_timezone(uid, tz_name, offset_min)
    if client_row:
        await set_client_timezone(uid, tz_name, offset_min)
    await state.clear()
    await message.answer(t(lang, "timezone_saved", tz=tz_name, offset=offset_str))
    log.info("Timezone set via text: user_id=%d tz=%s", uid, tz_name)
