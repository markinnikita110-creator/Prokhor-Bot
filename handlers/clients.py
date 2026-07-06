"""Client management: list, card, all client-scoped actions."""

import csv
import io
import logging
from datetime import datetime

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from database import (
    DB_PATH,
    get_user_lang,
    get_user_timezone,
    make_token,
    now_str,
    to_user_tz,
)
from core.db.clients_repository import get_client_lang, resolve_client
from core.services.notes import (
    count_notes,
    get_notes_created_text,
    get_notes_full,
    get_notes_text_only,
)
from core.services.homework import (
    get_client_homeworks_created_text,
    get_client_homeworks_full,
)
from core.services.checkins import (
    get_all_scores_ordered,
    get_positive_checkins_timestamped,
    get_positive_checkins_timestamped_ordered,
    get_positive_scores,
)
from core.services.sessions import (
    get_all_session_times,
    get_next_session,
    get_sessions_for_export,
)
from keyboards import (
    archived_list_keyboard,
    cancel_keyboard,
    checkin_score_keyboard,
    client_card_keyboard,
    client_card_more_keyboard,
    client_list_keyboard,
    clients_section_keyboard,
    export_format_keyboard,
    note_type_keyboard,
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

        notes = await count_notes(client_id)

        scores = [r[0] for r in await get_positive_scores(client_id)]

        now_dt = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        cur = await db.execute(
            "SELECT timezone FROM psychologists WHERE user_id = ?", (psych_id,))
        tz_row = await cur.fetchone()

    next_sess = await get_next_session(psych_id, name, now_dt)
    psych_tz = tz_row[0] if tz_row else None
    avg = f"{sum(scores)/len(scores):.1f}" if scores else "N/A"
    session_str = (
        to_user_tz(next_sess[0], psych_tz, "%d.%m.%Y %H:%M")
        if next_sess else t(lang, "no_next_session")
    )
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

    # ── Export: format selection ────────────────────────────────────────────
    elif action == "exp":
        from plan_limits import get_user_plan
        plan = await get_user_plan(psych_id)
        if not plan.get("export"):
            msg = (
                "⚠️ Экспорт доступен только на тарифе Pro.\nВведите промокод: /promo"
                if lang == "ru" else
                "⚠️ Export is available on the Pro plan only.\nEnter a promo code: /promo"
            )
            await callback.message.answer(msg)
            return
        await callback.message.answer(
            t(lang, "export_select_format"),
            reply_markup=export_format_keyboard(client_id, lang),
        )

    # ── Export: TXT ────────────────────────────────────────────────────────
    elif action == "exp_txt":
        from plan_limits import get_user_plan
        plan = await get_user_plan(psych_id)
        if not plan.get("export"):
            await callback.message.answer(
                "⚠️ Экспорт доступен только на тарифе Pro.\nВведите промокод: /promo"
                if lang == "ru" else
                "⚠️ Export is available on the Pro plan only.\nEnter a promo code: /promo"
            )
            return
        content, filename = await _build_export_txt(client_id, psych_id, client_name, lang)
        await callback.message.answer_document(
            BufferedInputFile(content, filename=filename),
            caption=t(lang, "export_done", name=client_name),
        )

    # ── Export: CSV ────────────────────────────────────────────────────────
    elif action == "exp_csv":
        from plan_limits import get_user_plan
        plan = await get_user_plan(psych_id)
        if not plan.get("export"):
            await callback.message.answer(
                "⚠️ Экспорт доступен только на тарифе Pro.\nВведите промокод: /promo"
                if lang == "ru" else
                "⚠️ Export is available on the Pro plan only.\nEnter a promo code: /promo"
            )
            return
        content, filename = await _build_export_csv(client_id, psych_id, client_name, lang)
        await callback.message.answer_document(
            BufferedInputFile(content, filename=filename),
            caption=t(lang, "export_done", name=client_name),
        )

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

    # ── Note type picker (merged Note button → choose plain or SOAP) ────────
    elif action == "notepick":
        try:
            await callback.message.edit_text(
                t(lang, "note_type_prompt"),
                reply_markup=note_type_keyboard(client_id, lang))
        except Exception:
            await callback.message.answer(
                t(lang, "note_type_prompt"),
                reply_markup=note_type_keyboard(client_id, lang))

    # ── More screen (secondary client card with extended actions) ───────────
    elif action == "more":
        try:
            await callback.message.edit_reply_markup(
                reply_markup=client_card_more_keyboard(client_id, bool(is_archived), lang))
        except Exception:
            card_text, _, _ = await _client_card(client_id, psych_id, lang)
            await callback.message.answer(
                card_text or client_name,
                reply_markup=client_card_more_keyboard(client_id, bool(is_archived), lang))


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
    session_utc_times: set[str] = set()  # scheduled_at is stored UTC — needs conversion
    for ts, text in await get_notes_created_text(client_id):
        events.append((ts, t(lang, "timeline_note", text=text[:60])))
    for ts, text in await get_client_homeworks_created_text(client_id):
        events.append((ts, t(lang, "timeline_homework", text=text[:60])))

    for ts, score in await get_positive_checkins_timestamped(client_id):
        events.append((ts, t(lang, "timeline_checkin", score=score)))

    for (ts,) in await get_all_session_times(psych_id, client_name):
        session_utc_times.add(ts)
        events.append((ts, t(lang, "timeline_session")))

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone FROM psychologists WHERE user_id = ?", (psych_id,))
        tz_row = await cur.fetchone()

    if not events:
        return t(lang, "no_timeline")
    psych_tz = tz_row[0] if tz_row else None
    events.sort(key=lambda x: x[0])
    lines = []
    for ts, label in events:
        # Only session.scheduled_at is stored in UTC; other timestamps (created_at,
        # checkin.timestamp) come from now_str() which is server-local (UTC on Replit).
        ts_display = (to_user_tz(ts, psych_tz, "%Y-%m-%d %H:%M")
                      if ts in session_utc_times else ts)
        lines.append(f"{ts_display}  {label}")
    return t(lang, "timeline_title", client=client_name) + "\n" + "\n".join(lines)


async def _build_engagement(client_id: int, client_name: str, lang: str) -> str:
    note_count = await count_notes(client_id)
    scores = [r[0] for r in await get_all_scores_ordered(client_id)]
    real = [s for s in scores if s > 0]
    avg_str = f"{sum(real)/len(real):.1f}" if real else "N/A"
    label = engagement_label(sum(real)/len(real), lang) if real else t(lang, "no_checkin_data")
    flags = smart_flags(scores, lang)
    flag_text = ("\n" + "\n".join(flags)) if flags else ""
    return t(lang, "engagement_text", client=client_name, notes=note_count,
             checkins=len(scores), avg=avg_str, label=label) + flag_text


async def _fetch_client_data(client_id: int, psych_id: int, client_name: str) -> dict:
    """Fetch all exportable data for a client into a dict of lists."""
    data: dict = {"notes": [], "checkins": [], "homeworks": [], "sessions": []}
    data["notes"] = await get_notes_full(client_id)
    data["homeworks"] = await get_client_homeworks_full(client_id)
    data["checkins"] = await get_positive_checkins_timestamped_ordered(client_id)
    data["sessions"] = await get_sessions_for_export(psych_id, client_name)
    async with aiosqlite.connect(DB_PATH) as db:
        # Individual sessions (may or may not exist)
        try:
            cur = await db.execute(
                "SELECT scheduled_at, duration_min FROM individual_sessions "
                "WHERE psychologist_id = ? AND client_id = ? ORDER BY scheduled_at",
                (psych_id, client_id))
            indiv = await cur.fetchall()
            data["sessions"] = list(data["sessions"]) + [(ts, f"{dur}min") for ts, dur in indiv]
        except Exception:
            pass

    return data


async def _build_export(client_id: int, psych_id: int, client_name: str,
                        lang: str) -> tuple[bytes, str]:
    """Legacy TXT export — delegates to _build_export_txt."""
    return await _build_export_txt(client_id, psych_id, client_name, lang)


async def _build_export_txt(client_id: int, psych_id: int, client_name: str,
                            lang: str) -> tuple[bytes, str]:
    """Build a human-readable TXT export for one client."""
    data = await _fetch_client_data(client_id, psych_id, client_name)
    exported_label = "Экспорт" if lang == "ru" else "Exported"
    lines = [f"=== {client_name} ===", f"{exported_label}: {now_str()}", ""]

    if data["notes"]:
        header = "--- ЗАМЕТКИ ---" if lang == "ru" else "--- NOTES ---"
        lines += [header]
        for ts, nt, tx in data["notes"]:
            lines.append(f"[{ts}] ({nt})\n{tx}")
        lines.append("")

    if data["checkins"]:
        header = "--- ЧЕК-ИНЫ ---" if lang == "ru" else "--- CHECK-INS ---"
        lines += [header]
        for ts, sc in data["checkins"]:
            lines.append(f"[{ts}] {sc}/10")
        lines.append("")

    if data["homeworks"]:
        header = "--- ЗАДАНИЯ ---" if lang == "ru" else "--- HOMEWORK ---"
        lines += [header]
        for ts, tx, done in data["homeworks"]:
            lines.append(f"[{ts}] {'✅' if done else '🕓'} {tx}")
        lines.append("")

    if data["sessions"]:
        header = "--- СЕССИИ ---" if lang == "ru" else "--- SESSIONS ---"
        lines += [header]
        for row in data["sessions"]:
            ts = row[0]
            extra = row[1] if len(row) > 1 and row[1] else ""
            lines.append(f"[{ts}]" + (f" {extra}" if extra else ""))
        lines.append("")

    content = "\n".join(lines).encode("utf-8")
    filename = t(lang, "export_filename", client=client_name)
    return content, filename


async def _build_export_csv(client_id: int, psych_id: int, client_name: str,
                            lang: str) -> tuple[bytes, str]:
    """Build a CSV export for one client (importable in Excel/Sheets)."""
    data = await _fetch_client_data(client_id, psych_id, client_name)

    if lang == "ru":
        col_section = "Раздел"
        col_date    = "Дата"
        col_content = "Содержание"
        col_extra   = "Доп."
        sec_note    = "Заметка"
        sec_checkin = "Чек-ин"
        sec_hw      = "Задание"
        sec_session = "Сессия"
    else:
        col_section = "Section"
        col_date    = "Date"
        col_content = "Content"
        col_extra   = "Extra"
        sec_note    = "Note"
        sec_checkin = "Check-in"
        sec_hw      = "Homework"
        sec_session = "Session"

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([col_section, col_date, col_content, col_extra])

    for ts, nt, tx in data["notes"]:
        writer.writerow([sec_note, ts, tx, nt])
    for ts, sc in data["checkins"]:
        writer.writerow([sec_checkin, ts, f"{sc}/10", ""])
    for ts, tx, done in data["homeworks"]:
        status = "✅" if done else "🕓"
        writer.writerow([sec_hw, ts, tx, status])
    for row in data["sessions"]:
        ts = row[0]
        extra = row[1] if len(row) > 1 and row[1] else ""
        writer.writerow([sec_session, ts, "", extra])

    content = ("\ufeff" + buf.getvalue()).encode("utf-8")  # BOM for Excel
    filename = t(lang, "export_csv_filename", client=client_name)
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
    from plan_limits import get_user_plan
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    plan = await get_user_plan(uid)
    if not plan.get("export"):
        msg = (
            "⚠️ Экспорт доступен только на тарифе Pro.\nВведите промокод: /promo"
            if lang == "ru" else
            "⚠️ Export is available on the Pro plan only.\nEnter a promo code: /promo"
        )
        await message.answer(msg)
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /export <client>")
        return
    name = args[1].strip()
    client_id = await resolve_client(uid, name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=name))
        return
    content, filename = await _build_export_txt(client_id, uid, name, lang)
    await message.answer_document(
        BufferedInputFile(content, filename=filename),
        caption=t(lang, "export_done", name=name),
    )


@router.message(Command("export_all"))
async def export_all_cmd(message: Message):
    """Export all active clients as a single TXT archive (Pro only)."""
    from plan_limits import get_user_plan
    uid = message.from_user.id
    lang = await get_user_lang(uid)
    plan = await get_user_plan(uid)
    if not plan.get("export"):
        msg = (
            "⚠️ Экспорт доступен только на тарифе Pro.\nВведите промокод: /promo"
            if lang == "ru" else
            "⚠️ Export is available on the Pro plan only.\nEnter a promo code: /promo"
        )
        await message.answer(msg)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM clients WHERE psychologist_id = ? AND is_archived = 0 ORDER BY name",
            (uid,)
        )
        clients = await cur.fetchall()

    if not clients:
        await message.answer(t(lang, "export_all_no_clients"))
        return

    exported_label = "Экспорт всех клиентов" if lang == "ru" else "All clients export"
    all_lines = [f"=== {exported_label} — {now_str()} ===", ""]

    for cid, cname in clients:
        data = await _fetch_client_data(cid, uid, cname)
        all_lines.append(f"\n{'='*40}")
        all_lines.append(f"  {cname}")
        all_lines.append(f"{'='*40}")

        if data["notes"]:
            h = "ЗАМЕТКИ" if lang == "ru" else "NOTES"
            all_lines.append(f"\n--- {h} ---")
            for ts, nt, tx in data["notes"]:
                all_lines.append(f"[{ts}] ({nt})\n{tx}")

        if data["checkins"]:
            h = "ЧЕК-ИНЫ" if lang == "ru" else "CHECK-INS"
            all_lines.append(f"\n--- {h} ---")
            for ts, sc in data["checkins"]:
                all_lines.append(f"[{ts}] {sc}/10")

        if data["homeworks"]:
            h = "ЗАДАНИЯ" if lang == "ru" else "HOMEWORK"
            all_lines.append(f"\n--- {h} ---")
            for ts, tx, done in data["homeworks"]:
                all_lines.append(f"[{ts}] {'✅' if done else '🕓'} {tx}")

        if data["sessions"]:
            h = "СЕССИИ" if lang == "ru" else "SESSIONS"
            all_lines.append(f"\n--- {h} ---")
            for row in data["sessions"]:
                ts = row[0]
                extra = row[1] if len(row) > 1 and row[1] else ""
                all_lines.append(f"[{ts}]" + (f" {extra}" if extra else ""))

    content = "\n".join(all_lines).encode("utf-8")
    filename = t(lang, "export_all_filename")
    count = len(clients)
    await message.answer_document(
        BufferedInputFile(content, filename=filename),
        caption=t(lang, "export_all_done", count=count),
    )


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
    rows = await get_notes_text_only(client_id)
    count = len(rows)
    text = t(lang, "summary_text", client=name, count=count)
    if rows:
        text += t(lang, "summary_last", last=rows[-1][0])
    await message.answer(text)
