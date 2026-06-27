"""Homework section: assign, list, client-side view."""

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from aiogram import Bot

from database import DB_PATH, get_client_lang, get_user_lang, now_str, resolve_client
from keyboards import cancel_keyboard, homework_section_keyboard
from states import AssignHomeworkForm, AssignHomeworkFromCardForm
from translations import t

router = Router()
log = logging.getLogger(__name__)


# ── Section callback ───────────────────────────────────────────────────────
@router.callback_query(F.data == "m_homework")
async def homework_section(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "section_homework"),
                                         reply_markup=homework_section_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "section_homework"),
                                      reply_markup=homework_section_keyboard(lang))


# ── hw_add: assign from menu (ask client name first) ──────────────────────
@router.callback_query(F.data == "hw_add")
async def hw_add_start(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(lang=lang)
    await state.set_state(AssignHomeworkForm.client_name)
    await callback.message.answer(t(lang, "ask_client_name"),
                                   reply_markup=cancel_keyboard(lang))


@router.message(AssignHomeworkForm.client_name)
async def hw_got_client(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(client_name=message.text.strip())
    await state.set_state(AssignHomeworkForm.text)
    await message.answer(t(lang, "ask_homework_text"), reply_markup=cancel_keyboard(lang))


@router.message(AssignHomeworkForm.text)
async def hw_got_text(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_name = data["client_name"]
    hw_text = message.text.strip()
    await state.clear()
    await _save_and_send_homework(message.from_user.id, client_name, hw_text, lang, message, bot)


# ── From client card: text only (client already in FSM data) ──────────────
@router.message(AssignHomeworkFromCardForm.text)
async def hw_card_got_text(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_name = data.get("client_name", "")
    hw_text = message.text.strip()
    await state.clear()
    await _save_and_send_homework(message.from_user.id, client_name, hw_text, lang, message, bot)


# ── hw_list: show active homework across all clients ──────────────────────
@router.callback_query(F.data == "hw_list")
async def hw_list(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, h.text FROM homeworks h "
            "JOIN clients c ON c.id = h.client_id "
            "WHERE c.psychologist_id = ? AND h.completed = 0 AND c.is_archived = 0 "
            "ORDER BY h.id DESC LIMIT 30",
            (callback.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        text = t(lang, "no_active_homework")
    else:
        lines = [f"• {name}: {hw[:60]}" for name, hw in rows]
        text = t(lang, "homework_list_title") + "\n" + "\n".join(lines)
    try:
        await callback.message.edit_text(text, reply_markup=homework_section_keyboard(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=homework_section_keyboard(lang))


# ── Shared helper ──────────────────────────────────────────────────────────
async def _save_and_send_homework(psych_id: int, client_name: str, hw_text: str,
                                   lang: str, message: Message, bot: Bot):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (psych_id, client_name)
        )
        row = await cur.fetchone()
    if row:
        client_id, client_tg = row
    else:
        client_id = await resolve_client(psych_id, client_name)
        client_tg = None

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO homeworks (client_id, text, created_at) VALUES (?, ?, ?)",
            (client_id, hw_text, now_str())
        )
        await db.commit()

    if client_tg and bot:
        c_lang = await get_client_lang(client_tg)
        await bot.send_message(client_tg, t(c_lang, "new_homework_client", text=hw_text))
        await message.answer(t(lang, "homework_sent", client=client_name))
    else:
        await message.answer(t(lang, "homework_saved_offline", client=client_name))
    log.info("Homework assigned to client_id=%d by psych=%d", client_id, psych_id)


# ── Legacy slash commands ──────────────────────────────────────────────────
@router.message(Command("homework"))
async def homework_cmd(message: Message, bot: Bot):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /homework <client> <text>")
        return
    await _save_and_send_homework(message.from_user.id, args[1].strip(), args[2].strip(), lang, message, bot)


@router.message(Command("homeworks"))
async def homeworks_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /homeworks <client>")
        return
    client_name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, client_name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=client_name))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT text, completed FROM homeworks WHERE client_id = ? ORDER BY id", (client_id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_homework", client=client_name))
        return
    lines = [f"{'✅' if done else '🕓'} {text}" for text, done in rows]
    await message.answer(t(lang, "homeworks_title", client=client_name) + "\n" + "\n".join(lines))


@router.message(Command("my_homeworks"))
async def my_homeworks_cmd(message: Message):
    from database import find_connected_client
    client_row = await find_connected_client(message.from_user.id)
    if not client_row:
        await message.answer(t("en", "not_a_client"))
        return
    client_id, _, _ = client_row
    lang = await get_client_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT text, completed FROM homeworks WHERE client_id = ? ORDER BY id", (client_id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_my_homeworks"))
        return
    lines = [f"{'✅' if done else '🕓'} {text}" for text, done in rows]
    await message.answer(t(lang, "my_homeworks_title") + "\n" + "\n".join(lines))
