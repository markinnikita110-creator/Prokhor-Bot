"""Analytics section: dashboard, alerts."""

import logging
from datetime import datetime, timedelta

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import DB_PATH, get_user_lang
from core.db.clients_repository import resolve_client
from keyboards import analytics_section_keyboard
from translations import t
from utils import engagement_label, smart_flags

router = Router()
log = logging.getLogger(__name__)


async def _dashboard_text(psych_id: int, lang: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM clients WHERE psychologist_id = ? AND is_archived = 0 ORDER BY name",
            (psych_id,)
        )
        clients = await cur.fetchall()
    if not clients:
        return t(lang, "no_clients")
    blocks = []
    for client_id, name in clients:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM notes WHERE client_id = ?", (client_id,))
            note_count = (await cur.fetchone())[0]
            cur = await db.execute("SELECT score FROM checkins WHERE client_id = ?", (client_id,))
            scores = [r[0] for r in await cur.fetchall()]
        real = [s for s in scores if s > 0]
        avg_str = f"{sum(real)/len(real):.1f}" if real else "N/A"
        label = engagement_label(sum(real)/len(real), lang) if real else t(lang, "no_data")
        blocks.append(t(lang, "dashboard_row", name=name, notes=note_count,
                        checkins=len(scores), avg=avg_str, status=label))
    return t(lang, "dashboard_title") + "\n\n" + "\n\n".join(blocks)


async def _alerts_text(psych_id: int, lang: str) -> str:
    now = datetime.utcnow()
    cut_ci  = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
    cut_ses = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, name FROM clients WHERE psychologist_id = ? AND is_archived = 0",
            (psych_id,)
        )
        clients = await cur.fetchall()
    alerts = []
    for client_id, name in clients:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT score FROM checkins WHERE client_id = ? AND score > 0", (client_id,))
            scores = [r[0] for r in await cur.fetchall()]
            if scores and (sum(scores)/len(scores)) < 4:
                alerts.append(t(lang, "alert_low_score", client=name))

            cur = await db.execute(
                "SELECT MAX(timestamp) FROM checkins WHERE client_id = ?", (client_id,))
            last_ci = (await cur.fetchone())[0]
            if not last_ci or last_ci < cut_ci:
                alerts.append(t(lang, "alert_no_checkin", client=name))

            cur = await db.execute(
                "SELECT MAX(scheduled_at) FROM sessions WHERE psychologist_id = ? AND client_name = ?",
                (psych_id, name))
            last_s = (await cur.fetchone())[0]
            if not last_s or last_s < cut_ses:
                alerts.append(t(lang, "alert_no_session", client=name))
    if not alerts:
        return t(lang, "no_alerts")
    return t(lang, "alerts_title") + "\n" + "\n".join(alerts)


# ── Callbacks ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "m_analytics")
async def analytics_section(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    try:
        await callback.message.edit_text(t(lang, "section_analytics"),
                                         reply_markup=analytics_section_keyboard(lang))
    except Exception:
        await callback.message.answer(t(lang, "section_analytics"),
                                      reply_markup=analytics_section_keyboard(lang))


@router.callback_query(F.data == "an_dash")
async def analytics_dashboard(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    text = await _dashboard_text(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=analytics_section_keyboard(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=analytics_section_keyboard(lang))


@router.callback_query(F.data == "an_alerts")
async def analytics_alerts(callback: CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    text = await _alerts_text(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=analytics_section_keyboard(lang))
    except Exception:
        await callback.message.answer(text, reply_markup=analytics_section_keyboard(lang))


# ── Legacy slash commands ──────────────────────────────────────────────────
@router.message(Command("dashboard"))
async def dashboard_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(await _dashboard_text(message.from_user.id, lang))


@router.message(Command("alerts"))
async def alerts_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    await message.answer(await _alerts_text(message.from_user.id, lang))


@router.message(Command("engagement"))
async def engagement_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Usage: /engagement <client>")
        return
    client_name = args[1].strip()
    client_id = await resolve_client(message.from_user.id, client_name, create=False)
    if not client_id:
        await message.answer(t(lang, "client_not_found", name=client_name))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM notes WHERE client_id = ?", (client_id,))
        note_count = (await cur.fetchone())[0]
        cur = await db.execute("SELECT score FROM checkins WHERE client_id = ? ORDER BY id", (client_id,))
        scores = [r[0] for r in await cur.fetchall()]
    real = [s for s in scores if s > 0]
    avg_str = f"{sum(real)/len(real):.1f}" if real else "N/A"
    label = engagement_label(sum(real)/len(real), lang) if real else t(lang, "no_checkin_data")
    flags = smart_flags(scores, lang)
    flag_text = ("\n" + "\n".join(flags)) if flags else ""
    await message.answer(t(lang, "engagement_text", client=client_name,
                           notes=note_count, checkins=len(scores), avg=avg_str,
                           label=label) + flag_text)
