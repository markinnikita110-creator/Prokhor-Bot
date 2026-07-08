"""Notes: plain notes, SOAP notes, tags — FSM handlers + legacy slash commands."""

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import DB_PATH, now_str
from core.db.users_repository import get_user_lang
from core.db.clients_repository import resolve_client
from core.services.notes import (
    get_notes_text_only,
    insert_plain_note,
    insert_soap_note,
)
from keyboards import cancel_keyboard
from states.note_states import AddNoteForm, SOAPForm, TagForm
from translations import t

router = Router()
log = logging.getLogger(__name__)


# ── AddNoteForm: triggered by ca_{id}_note in clients.py ──────────────────
@router.message(AddNoteForm.text)
async def note_got_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_id = data.get("client_id")
    client_name = data.get("client_name", "?")
    await state.clear()
    await insert_plain_note(client_id, message.text.strip(), now_str())
    await message.answer(t(lang, "note_saved", client=client_name))
    log.info("Note saved for client_id=%s", client_id)


# ── SOAPForm: triggered by ca_{id}_soap or /note_soap ─────────────────────
@router.message(SOAPForm.subjective)
async def soap_subjective(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(subjective=message.text)
    await state.set_state(SOAPForm.objective)
    await message.answer(t(lang, "soap_o"), reply_markup=cancel_keyboard(lang))


@router.message(SOAPForm.objective)
async def soap_objective(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(objective=message.text)
    await state.set_state(SOAPForm.assessment)
    await message.answer(t(lang, "soap_a"), reply_markup=cancel_keyboard(lang))


@router.message(SOAPForm.assessment)
async def soap_assessment(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(assessment=message.text)
    await state.set_state(SOAPForm.plan)
    await message.answer(t(lang, "soap_p"), reply_markup=cancel_keyboard(lang))


@router.message(SOAPForm.plan)
async def soap_plan(message: Message, state: FSMContext):
    await state.update_data(plan=message.text)
    data = await state.get_data()
    await state.clear()
    lang = data.get("lang", "en")
    client_name = data.get("client_name", "?")
    client_id = data.get("client_id")
    psych_id = message.from_user.id

    # client_id may be None if triggered via slash command with a name
    if not client_id:
        client_id = await resolve_client(psych_id, client_name)

    text = (f"S: {data['subjective']}\nO: {data['objective']}\n"
            f"A: {data['assessment']}\nP: {data['plan']}")
    await insert_soap_note(client_id, text, now_str())
    await message.answer(t(lang, "soap_saved", client=client_name, text=text))
    log.info("SOAP note saved for client_id=%s", client_id)


# ── TagForm: triggered by ca_{id}_tag ─────────────────────────────────────
@router.message(TagForm.tag)
async def tag_got_tag(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    client_id = data.get("client_id")
    client_name = data.get("client_name", "?")
    tag = message.text.strip()
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO client_tags (client_id, tag) VALUES (?, ?)", (client_id, tag))
        await db.commit()
    await message.answer(t(lang, "tag_added", tag=tag, client=client_name))


# ── Legacy slash commands ──────────────────────────────────────────────────

@router.message(Command("note"))
async def note_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /note <client> <text>")
        return
    client_name, text = args[1].strip(), args[2].strip()
    client_id = await resolve_client(message.from_user.id, client_name)
    await insert_plain_note(client_id, text, now_str())
    await message.answer(t(lang, "note_saved", client=client_name))


@router.message(Command("notes"))
async def notes_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /notes <client>")
        return
    name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    rows = await get_notes_text_only(client_id)
    if not rows:
        await message.answer(t(lang, "no_notes", client=name))
        return
    lines = [f"{i+1}. {r[0]}" for i, r in enumerate(rows)]
    await message.answer(t(lang, "notes_title", client=name) + "\n" + "\n".join(lines))


@router.message(Command("note_soap"))
async def note_soap_cmd(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /note_soap <client>")
        return
    client_name = args[1].strip()
    await state.update_data(client_name=client_name, client_id=None, lang=lang)
    await state.set_state(SOAPForm.subjective)
    await message.answer(t(lang, "soap_s", client=client_name), reply_markup=cancel_keyboard(lang))
