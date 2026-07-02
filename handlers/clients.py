"""Client management: list, card, all client-scoped actions."""

import logging
from datetime import datetime

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from database import (
    DB_PATH,
    get_client_lang,
    get_user_lang,
    make_token,
    now_str,
    resolve_client,
)
from keyboards import (
    archived_list_keyboard,
    cancel_keyboard,
    checkin_score_keyboard,
    client_card_keyboard,
    client_list_keyboard,
    clients_section_keyboard,
)
from states import AddClientForm, AssignHomeworkFromCardForm, TagForm
from states.note_states import AddNoteForm, SOAPForm
from states.session_states import ScheduleSessionFromCardForm
from translations import t
from utils import engagement_label, smart_flags

router = Router()
log = logging.getLogger(__name__)

BOT_USERNAME = ""  # injected from main.py


def set_bot_username(username: str):
    global BOT_USERNAME
    BOT_USERNAME = username


# ── Build client card text + meta ──────────────────────────────────────────
async def _client_card(client_id: int, psych_id: int, lang: str):
    """Returns (text, is_archived, client_name) or None on not-found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name, is_archived FROM clients WHERE id = ? AND psychologist_id = ?",
            (client_id, psych_id)
        )
        row = await cur.fetchone()
        if not row:
            return None, False, ""
        name, is_archived = row

        cur = await db.execute("SELECT COUNT(*) FROM notes WHERE client_id = ?", (client_id,))
        notes = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT score FROM checkins WHERE client_id = ? AND score > 0", (client_id,))
        scores = [r[0] for r in await cur.fetchall()]

        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur = await db.execute(
            "SELECT scheduled_at FROM sessions "
            "WHERE psychologist_id = ? AND client_name = ? AND scheduled_at >= ? "
            "ORDER BY scheduled_at LIMIT 1",
            (psych_id, name, now_dt)
        )
        next_sess = await cur.fetchone()

    avg = f"{sum(scores)/len(scores):.1f}" if scores else "N/A"
    session_str = next_sess[0] if next_sess else t(lang, "no_next_session")
    text = t(lang, "client_card", name=name, notes=notes,
             checkins=len(scores), avg=avg, session=session_str)
    return text, bool(is_archived), name


# ── Clients section (inline) ───────────────────────────────────────────────
@router.callback_query(F.data == "c_invite_pick")
async def invite_pick(callback: CallbackQuery):
    """Reuse the client list — user picks a client to get their invite link."""
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM clients WHERE psychologist_id = ? AND is_archived = 0 ORDER BY name",
            (callback.from_user.id,)
        )
        clients = await cur.fetchall()
    if not clients:
        await callback.message.answer(t(lang, "no_clients"))
        return
    try:
        await callback.message.edit_text(
            t(lang, "btn_invite_client"),
            reply_markup=client_list_keyboard(clients, 0, lang))
    except Exception:
        await callback.message.answer(
            t(lang, "btn_invite_client"),
            reply_markup=client_list_keyboard(clients, 0, lang))


# ── c_add → start AddClientForm ────────────────────────────────────────────
@router.callback_query(F.data == "c_add")
async def c_add_start(callback: CallbackQuery, state: FSMContext):
    from plan_limits import check_plan_limit
    lang = await get_user_lang(callback.from_user.id)
    allowed, err_msg = await check_plan_limit(callback.from_user.id, "add_client", lang=lang)
    if not allowed:
        await callback.answer()
        await callback.message.answer(err_msg)
        return
    await callback.answer()
    await state.update_data(lang=lang)
    await state.set_state(AddClientForm.name)
    await callback.message.answer(t(lang, "ask_client_name"), reply_markup=cancel_keyboard(lang))


@router.message(AddClientForm.name)
async def c_add_got_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    name = message.text.strip()
    await state.clear()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO clients (psychologist_id, name, created_at, invite_token) "
            "VALUES (?, ?, ?, ?)",
            (message.from_user.id, name, now_str(), make_token())
        )
        await db.commit()
    await message.answer(t(lang, "client_added", name=name),
                         reply_markup=clients_section_keyboard(lang))
    log.info("Client added: '%s' by psych=%d", name, message.from_user.id)


# ── cl_{page} → paginated client list ─────────────────────────────────────
@router.callback_query(F.data.regexp(r"^cl_\d+$"))
async def client_list_cb(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    page = int(callback.data.split("_")[1])
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM clients WHERE psychologist_id = ? AND is_archived = 0 ORDER BY name",
            (callback.from_user.id,)
        )
        clients = await cur.fetchall()
    if not clients:
        await callback.message.answer(t(lang, "no_clients"))
        return
    try:
        await callback.message.edit_text(
            t(lang, "btn_client_list"),
            reply_markup=client_list_keyboard(clients, page, lang))
    except Exception:
        await callback.message.answer(
            t(lang, "btn_client_list"),
            reply_markup=client_list_keyboard(clients, page, lang))


# ── cc_{id} → show client card ─────────────────────────────────────────────
@router.callback_query(F.data.regexp(r"^cc_\d+$"))
async def client_card_cb(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    client_id = int(callback.data.split("_")[1])
    await callback.answer()
    text, is_archived, _ = await _client_card(client_id, callback.from_user.id, lang)
    if not text:
        await callback.message.answer(t(lang, "client_not_found", name="?"))
        return
    try:
        await callback.message.edit_text(
            text, reply_markup=client_card_keyboard(client_id, is_archived, lang))
    except Exception:
        await callback.message.answer(
            text, reply_markup=client_card_keyboard(client_id, is_archived, lang))


# ── ca_{id}_{action} → client card actions (single dispatch) ──────────────
@router.callback_query(F.data.regexp(r"^ca_\d+_.+$"))
async def client_action_cb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    lang = await get_user_lang(callback.from_user.id)
    parts   = callback.data.split("_", 2)
    client_id = int(parts[1])
    action    = parts[2]
    psych_id  = callback.from_user.id

    # Fetch client name once for actions that need it
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name, telegram_id, is_archived FROM clients WHERE id = ? AND psychologist_id = ?",
            (client_id, psych_id)
        )
        row = await cur.fetchone()
    if not row:
        await callback.answer(t(lang, "client_not_found", name="?"))
        return
    client_name, client_tg, is_archived = row
    await callback.answer()

    # ── Note ──────────────────────────────────────────────────────────────
    if action == "note":
        await state.update_data(client_id=client_id, client_name=client_name, lang=lang)
        await state.set_state(AddNoteForm.text)
        await callback.message.answer(t(lang, "ask_note_text"), reply_markup=cancel_keyboard(lang))

    # ── SOAP note ──────────────────────────────────────────────────────────
    elif action == "soap":
        await state.update_data(client_id=client_id, client_name=client_name, lang=lang)
        await state.set_state(SOAPForm.subjective)
        await callback.message.answer(t(lang, "soap_s", client=client_name),
                                      reply_markup=cancel_keyboard(lang))

    # ── Homework ───────────────────────────────────────────────────────────
    elif action == "hw":
        await state.update_data(client_id=client_id, client_name=client_name, lang=lang)
        await state.set_state(AssignHomeworkFromCardForm.text)
        await callback.message.answer(t(lang, "ask_homework_text"), reply_markup=cancel_keyboard(lang))

    # ── Send check-in ──────────────────────────────────────────────────────
    elif action == "ci":
        if not client_tg:
            await callback.message.answer(t(lang, "client_not_connected_tg"))
            return
        c_lang = await get_client_lang(client_tg)
        await bot.send_message(client_tg, t(c_lang, "checkin_question"),
                               reply_markup=checkin_score_keyboard(client_id))
        await callback.message.answer(t(lang, "checkin_request_sent", client=client_name))

    # ── Schedule session ───────────────────────────────────────────────────
    elif action == "sched":
        await state.update_data(client_id=client_id, client_name=client_name, lang=lang)
        await state.set_state(ScheduleSessionFromCardForm.datetime_str)
        await callback.message.answer(t(lang, "ask_session_datetime"),
                                      reply_markup=cancel_keyboard(lang))

    # ── Timeline ───────────────────────────────────────────────────────────
    elif action == "tl":
        text = await _build_timeline(client_id, psych_id, client_name, lang)
        await callback.message.answer(text)

    # ── Tags ───────────────────────────────────────────────────────────────
    elif action == "tag":
        await state.update_data(client_id=client_id, client_name=client_name, lang=lang)
        await state.set_state(TagForm.tag)
        await callback.message.answer(t(lang, "ask_tag"), reply_markup=cancel_keyboard(lang))

    # ── Engagement ─────────────────────────────────────────────────────────
    elif action == "eng":
        text = await _build_engagement(client_id, client_name, lang)
        await callback.message.answer(text)

    # ── Export ─────────────────────────────────────────────────────────────
    elif action == "exp":
        content, filename = await _build_export(client_id, psych_id, client_name, lang)
        await callback.message.answer_document(
            BufferedInputFile(content, filename=filename))

    # ── Archive ────────────────────────────────────────────────────────────
    elif action == "arch":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE clients SET is_archived = 1 WHERE id = ?", (client_id,))
            await db.commit()
        await callback.message.answer(t(lang, "client_archived", name=client_name))

    # ── Unarchive ──────────────────────────────────────────────────────────
    elif action == "unarc":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE clients SET is_archived = 0 WHERE id = ?", (client_id,))
            await db.commit()
        await callback.message.answer(t(lang, "client_unarchived", name=client_name))

    # ── Invite link ────────────────────────────────────────────────────────
    elif action == "inv":
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT invite_token FROM clients WHERE id = ?", (client_id,))
            tok_row = await cur.fetchone()
        token = tok_row[0] if tok_row and tok_row[0] else make_token()
        if not (tok_row and tok_row[0]):
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE clients SET invite_token = ? WHERE id = ?", (token, client_id))
                await db.commit()
        link = f"https://t.me/{BOT_USERNAME}?start={token}"
        await callback.message.answer(t(lang, "invite_link", client=client_name, link=link))


# ── arc_{page} → archived clients list ────────────────────────────────────
@router.callback_query(F.data.regexp(r"^arc_\d+$"))
async def archived_list_cb(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    page = int(callback.data.split("_")[1])
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM clients WHERE psychologist_id = ? AND is_archived = 1 ORDER BY name",
            (callback.from_user.id,)
        )
        clients = await cur.fetchall()
    if not clients:
        try:
            await callback.message.edit_text(t(lang, "no_archived"),
                                             reply_markup=clients_section_keyboard(lang))
        except Exception:
            await callback.message.answer(t(lang, "no_archived"),
                                          reply_markup=clients_section_keyboard(lang))
        return
    try:
        await callback.message.edit_text(
            t(lang, "archived_title"),
            reply_markup=archived_list_keyboard(clients, page, lang))
    except Exception:
        await callback.message.answer(
            t(lang, "archived_title"),
            reply_markup=archived_list_keyboard(clients, page, lang))


# ── ac_{id} → archived client card (with restore button) ──────────────────
@router.callback_query(F.data.regexp(r"^ac_\d+$"))
async def archived_client_card(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    client_id = int(callback.data.split("_")[1])
    await callback.answer()
    text, is_archived, _ = await _client_card(client_id, callback.from_user.id, lang)
    if not text:
        await callback.message.answer(t(lang, "client_not_found", name="?"))
        return
    try:
        await callback.message.edit_text(
            text, reply_markup=client_card_keyboard(client_id, True, lang))
    except Exception:
        await callback.message.answer(
            text, reply_markup=client_card_keyboard(client_id, True, lang))


# ── Shared helpers ─────────────────────────────────────────────────────────

async def _build_timeline(client_id: int, psych_id: int, client_name: str, lang: str) -> str:
    events = []
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT created_at, text FROM notes WHERE client_id = ?", (client_id,))
        for ts, text in await cur.fetchall():
            events.append((ts, t(lang, "timeline_note", text=text[:60])))

        cur = await db.execute(
            "SELECT timestamp, score FROM checkins WHERE client_id = ? AND score > 0", (client_id,))
        for ts, score in await cur.fetchall():
            events.append((ts, t(lang, "timeline_checkin", score=score)))

        cur = await db.execute(
            "SELECT created_at, text FROM homeworks WHERE client_id = ?", (client_id,))
        for ts, text in await cur.fetchall():
            events.append((ts, t(lang, "timeline_homework", text=text[:60])))

        cur = await db.execute(
            "SELECT scheduled_at FROM sessions WHERE psychologist_id = ? AND client_name = ?",
            (psych_id, client_name))
        for (ts,) in await cur.fetchall():
            events.append((ts, t(lang, "timeline_session")))

    if not events:
        return t(lang, "no_timeline")
    events.sort(key=lambda x: x[0])
    lines = [f"{ts}  {label}" for ts, label in events]
    return t(lang, "timeline_title", client=client_name) + "\n" + "\n".join(lines)


async def _build_engagement(client_id: int, client_name: str, lang: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM notes WHERE client_id = ?", (client_id,))
        note_count = (await cur.fetchone())[0]
        cur = await db.execute(
            "SELECT score FROM checkins WHERE client_id = ? ORDER BY id", (client_id,))
        scores = [r[0] for r in await cur.fetchall()]
    real = [s for s in scores if s > 0]
    avg_str = f"{sum(real)/len(real):.1f}" if real else "N/A"
    label = engagement_label(sum(real)/len(real), lang) if real else t(lang, "no_checkin_data")
    flags = smart_flags(scores, lang)
    flag_text = ("\n" + "\n".join(flags)) if flags else ""
    return t(lang, "engagement_text", client=client_name, notes=note_count,
             checkins=len(scores), avg=avg_str, label=label) + flag_text


async def _build_export(client_id: int, psych_id: int, client_name: str,
                        lang: str) -> tuple[bytes, str]:
    lines = [f"=== {client_name} ===", f"Exported: {now_str()}", ""]
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT created_at, note_type, text FROM notes WHERE client_id = ? ORDER BY id",
            (client_id,))
        notes = await cur.fetchall()
        if notes:
            lines += ["--- NOTES ---"] + [f"[{ts}] ({nt})\n{tx}" for ts, nt, tx in notes] + [""]

        cur = await db.execute(
            "SELECT timestamp, score FROM checkins WHERE client_id = ? AND score > 0 ORDER BY id",
            (client_id,))
        cis = await cur.fetchall()
        if cis:
            lines += ["--- CHECK-INS ---"] + [f"[{ts}] {sc}/10" for ts, sc in cis] + [""]

        cur = await db.execute(
            "SELECT created_at, text, completed FROM homeworks WHERE client_id = ? ORDER BY id",
            (client_id,))
        hws = await cur.fetchall()
        if hws:
            lines += ["--- HOMEWORK ---"] + [
                f"[{ts}] {'✅' if done else '🕓'} {tx}" for ts, tx, done in hws] + [""]

        cur = await db.execute(
            "SELECT scheduled_at FROM sessions WHERE psychologist_id = ? AND client_name = ? ORDER BY scheduled_at",
            (psych_id, client_name))
        sess = await cur.fetchall()
        if sess:
            lines += ["--- SESSIONS ---"] + [f"[{ts}]" for (ts,) in sess] + [""]

    content = "\n".join(lines).encode("utf-8")
    filename = t(lang, "export_filename", client=client_name)
    return content, filename


# ── Legacy slash commands ──────────────────────────────────────────────────

@router.message(Command("add_client"))
async def add_client_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /add_client <name>")
        return
    name = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO clients (psychologist_id, name, created_at, invite_token) VALUES (?, ?, ?, ?)",
            (message.from_user.id, name, now_str(), make_token())
        )
        await db.commit()
    await message.answer(t(lang, "client_added", name=name))


@router.message(Command("clients"))
async def clients_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT c.name, COUNT(n.id) FROM clients c "
            "LEFT JOIN notes n ON n.client_id = c.id "
            "WHERE c.psychologist_id = ? AND c.is_archived = 0 "
            "GROUP BY c.id ORDER BY c.name",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_clients"))
        return
    lines = [f"- {name} ({cnt} note{'s' if cnt != 1 else ''})" for name, cnt in rows]
    await message.answer(t(lang, "clients_title") + "\n" + "\n".join(lines))


@router.message(Command("clients_status"))
async def clients_status_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name, telegram_id FROM clients "
            "WHERE psychologist_id = ? AND is_archived = 0 ORDER BY name",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_clients"))
        return
    lines = [
        f"{'🟢' if tg else '🔴'} {n} — {t(lang, 'connected' if tg else 'not_connected')}"
        for n, tg in rows
    ]
    await message.answer(t(lang, "clients_status_title") + "\n" + "\n".join(lines))


@router.message(Command("client_info"))
async def client_info_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /client_info <client>")
        return
    name = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name)
        )
        row = await cur.fetchone()
    if not row:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    tid = row[0]
    tg_line = t(lang, "tg_id_line", tid=tid) if tid else t(lang, "tg_not_connected")
    await message.answer(t(lang, "client_info",
        client=name,
        connected=t(lang, "connected" if tid else "not_connected"),
        tg_line=tg_line))


@router.message(Command("invite"))
async def invite_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /invite <client>")
        return
    name = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, invite_token FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name)
        )
        row = await cur.fetchone()
    if not row:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    client_id, token = row
    if not token:
        token = make_token()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE clients SET invite_token = ? WHERE id = ?", (token, client_id))
            await db.commit()
    link = f"https://t.me/{BOT_USERNAME}?start={token}"
    await message.answer(t(lang, "invite_link", client=name, link=link))


@router.message(Command("archive"))
async def archive_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /archive <client>")
        return
    name = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT is_archived FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name)
        )
        row = await cur.fetchone()
        if not row:
            await message.answer(t(lang, "client_not_found", name=name))
            return
        await db.execute(
            "UPDATE clients SET is_archived = 1 WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name))
        await db.commit()
    await message.answer(t(lang, "client_archived", name=name))


@router.message(Command("unarchive"))
async def unarchive_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /unarchive <client>")
        return
    name = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT is_archived FROM clients WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name)
        )
        row = await cur.fetchone()
        if not row:
            await message.answer(t(lang, "client_not_found", name=name))
            return
        if row[0] == 0:
            await message.answer(t(lang, "client_not_archived", name=name))
            return
        await db.execute(
            "UPDATE clients SET is_archived = 0 WHERE psychologist_id = ? AND name = ?",
            (message.from_user.id, name))
        await db.commit()
    await message.answer(t(lang, "client_unarchived", name=name))


@router.message(Command("archived_clients"))
async def archived_clients_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name FROM clients WHERE psychologist_id = ? AND is_archived = 1 ORDER BY name",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_archived"))
        return
    lines = [f"- {n}" for (n,) in rows]
    await message.answer(t(lang, "archived_title") + "\n" + "\n".join(lines))


@router.message(Command("export"))
async def export_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /export <client>")
        return
    name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    content, filename = await _build_export(client_id, message.from_user.id, name, lang)
    await message.answer_document(BufferedInputFile(content, filename=filename))


@router.message(Command("tag"))
async def tag_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Usage: /tag <client> <tag>")
        return
    name, tag = args[1].strip(), args[2].strip()
    client_id = await resolve_client(message.from_user.id, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO client_tags (client_id, tag) VALUES (?, ?)", (client_id, tag))
        await db.commit()
    await message.answer(t(lang, "tag_added", tag=tag, client=name))


@router.message(Command("find"))
async def find_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /find <tag>")
        return
    tag = args[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT c.name FROM clients c "
            "JOIN client_tags ct ON ct.client_id = c.id "
            "WHERE c.psychologist_id = ? AND ct.tag = ? AND c.is_archived = 0",
            (message.from_user.id, tag)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer(t(lang, "no_clients_tag", tag=tag))
        return
    lines = [f"- {n}" for (n,) in rows]
    await message.answer(t(lang, "find_title", tag=tag) + "\n" + "\n".join(lines))


@router.message(Command("timeline"))
async def timeline_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /timeline <client>")
        return
    name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    text = await _build_timeline(client_id, message.from_user.id, name, lang)
    await message.answer(text)


@router.message(Command("summary"))
async def summary_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /summary <client>")
        return
    name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT text FROM notes WHERE client_id = ? ORDER BY id", (client_id,))
        rows = await cur.fetchall()
    count = len(rows)
    text = t(lang, "summary_text", client=name, count=count)
    if rows:
        text += t(lang, "summary_last", last=rows[-1][0])
    await message.answer(text)
