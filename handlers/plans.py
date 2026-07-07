"""Tariff plans and promo codes handler."""

import logging
import os
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.db.plans_repository import (
    fetch_all_promos,
    fetch_promo_code,
    fetch_user_plan_row,
    increment_promo_used_count,
    insert_or_replace_promo,
    upsert_user_plan,
)
from core.services.plans import PLANS, get_user_plan
from database import get_user_lang, now_str
from keyboards import main_menu_keyboard, settings_keyboard, tariff_keyboard
from translations import t

log = logging.getLogger(__name__)
router = Router()


class PromoForm(StatesGroup):
    waiting_code = State()


# ── Helpers ────────────────────────────────────────────────────────────────

async def _build_tariff_text(user_id: int, lang: str) -> tuple[str, bool]:
    """Return (text, is_pro) for the main tariff screen."""
    row = await fetch_user_plan_row(user_id)
    plan_name, expires_at = (row[0], row[1]) if row else ("start", None)
    is_pro = plan_name == "pro"

    if is_pro:
        if expires_at:
            expires_str = f"\n до {expires_at}" if lang == "ru" else f"\n until {expires_at}"
        else:
            expires_str = ""
        text = t(lang, "tariff_screen_pro", expires=expires_str)
    else:
        text = t(lang, "tariff_screen_start")

    return text, is_pro


# ── /promo — enter promo code ──────────────────────────────────────────────

@router.message(Command("promo"))
async def promo_cmd(message: Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(PromoForm.waiting_code)
    msg = "🎟 Введите промокод:" if lang == "ru" else "🎟 Enter promo code:"
    await message.answer(msg)


@router.message(PromoForm.waiting_code)
async def promo_got_code(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    code = message.text.strip()

    row = await fetch_promo_code(code)
    if not row:
        msg = "❌ Промокод не найден." if lang == "ru" else "❌ Promo code not found."
        await message.answer(msg)
        return

    plan_name, duration_days, max_uses, used_count = row

    if max_uses is not None and used_count >= max_uses:
        msg = (
            "❌ Этот промокод достиг лимита использований."
            if lang == "ru" else
            "❌ This promo code has reached its usage limit."
        )
        await message.answer(msg)
        return

    expires_at = None
    if duration_days:
        expires_at = (datetime.utcnow() + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M")

    await upsert_user_plan(user_id, plan_name, expires_at, now_str())
    await increment_promo_used_count(code)

    plan_display = PLANS.get(plan_name, {}).get("name", plan_name)
    if expires_at:
        msg = (
            f"✅ Тариф *{plan_display}* активирован до {expires_at}!"
            if lang == "ru" else
            f"✅ Plan *{plan_display}* activated until {expires_at}!"
        )
    else:
        msg = (
            f"✅ Тариф *{plan_display}* активирован бессрочно!"
            if lang == "ru" else
            f"✅ Plan *{plan_display}* activated permanently!"
        )

    await message.answer(msg, parse_mode="Markdown", reply_markup=main_menu_keyboard(lang))
    log.info("User %d activated plan %s via promo %s", user_id, plan_name, code)


# ── /myplan — view current plan (legacy command) ───────────────────────────

@router.message(Command("myplan"))
async def myplan_cmd(message: Message):
    lang = await get_user_lang(message.from_user.id)
    text, is_pro = await _build_tariff_text(message.from_user.id, lang)
    await message.answer(text, parse_mode="Markdown",
                         reply_markup=tariff_keyboard(lang, is_pro=is_pro))


# ── st_tariff — main tariff screen (from settings menu) ───────────────────

@router.callback_query(F.data == "st_tariff")
async def tariff_screen(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_lang(callback.from_user.id)
    text, is_pro = await _build_tariff_text(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=tariff_keyboard(lang, is_pro=is_pro),
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="Markdown",
            reply_markup=tariff_keyboard(lang, is_pro=is_pro),
        )


# ── st_tariff_upgrade — "Перейти на PRO" ──────────────────────────────────

@router.callback_query(F.data == "st_tariff_upgrade")
async def tariff_upgrade(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_lang(callback.from_user.id)
    row = await fetch_user_plan_row(callback.from_user.id)
    plan_name = row[0] if row else "start"

    if plan_name == "pro":
        msg = t(lang, "tariff_already_pro")
    else:
        if lang == "ru":
            msg = (
                "💎 *Хотите перейти на Pro?*\n\n"
                "Введите промокод командой /promo — и тариф активируется мгновенно.\n\n"
                "Промокод можно получить у администратора или в основном канале бота."
            )
        else:
            msg = (
                "💎 *Ready to upgrade to Pro?*\n\n"
                "Enter a promo code via /promo — your plan activates instantly.\n\n"
                "Get a promo code from the administrator or the bot's main channel."
            )

    try:
        await callback.message.edit_text(
            msg, parse_mode="Markdown",
            reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")),
        )
    except Exception:
        await callback.message.answer(msg, parse_mode="Markdown",
                                      reply_markup=tariff_keyboard(lang, is_pro=False))


# ── st_tariff_compare — "Сравнить тарифы" ─────────────────────────────────

@router.callback_query(F.data == "st_tariff_compare")
async def tariff_compare(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_lang(callback.from_user.id)
    row = await fetch_user_plan_row(callback.from_user.id)
    plan_name = row[0] if row else "start"
    text = t(lang, "tariff_compare")
    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")),
        )
    except Exception:
        await callback.message.answer(text, parse_mode="Markdown",
                                      reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")))


# ── st_tariff_history — "История платежей" ────────────────────────────────

@router.callback_query(F.data == "st_tariff_history")
async def tariff_history(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_lang(callback.from_user.id)
    row = await fetch_user_plan_row(callback.from_user.id)
    plan_name, expires_at = (row[0], row[1]) if row else ("start", None)
    plan_display = PLANS.get(plan_name, {}).get("name", plan_name)

    lines = []
    if expires_at:
        if lang == "ru":
            lines.append(f"📦 Текущий тариф: *{plan_display}*")
            lines.append(f"📅 Действует до: {expires_at}")
        else:
            lines.append(f"📦 Current plan: *{plan_display}*")
            lines.append(f"📅 Valid until: {expires_at}")
    else:
        lines.append(t(lang, "tariff_history_empty", plan=plan_display))

    text = "\n".join(lines)
    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")),
        )
    except Exception:
        await callback.message.answer(text, parse_mode="Markdown",
                                      reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")))


# ── st_tariff_howto — "Как это работает?" ─────────────────────────────────

@router.callback_query(F.data == "st_tariff_howto")
async def tariff_howto(callback: CallbackQuery):
    await callback.answer()
    lang = await get_user_lang(callback.from_user.id)
    row = await fetch_user_plan_row(callback.from_user.id)
    plan_name = row[0] if row else "start"
    text = t(lang, "tariff_howto")
    try:
        await callback.message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")),
        )
    except Exception:
        await callback.message.answer(text, parse_mode="Markdown",
                                      reply_markup=tariff_keyboard(lang, is_pro=(plan_name == "pro")))


# ── Admin: /giveplan <user_id> <plan> [days] ──────────────────────────────

@router.message(Command("giveplan"))
async def admin_giveplan(message: Message):
    admin_id = int(os.environ.get("ADMIN_ID", 0))
    if message.from_user.id != admin_id:
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /giveplan <user_id> <plan> [days]")
        return

    target_id = int(parts[1])
    plan_name = parts[2].lower()
    days = int(parts[3]) if len(parts) > 3 else None
    expires_at = (
        (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M") if days else None
    )

    await upsert_user_plan(target_id, plan_name, expires_at, now_str())
    await message.answer(
        f"✅ User {target_id} → plan '{plan_name}', expires: {expires_at or 'never'}"
    )
    log.info("Admin gave plan '%s' to user %d (expires %s)", plan_name, target_id, expires_at)


# ── Admin: /addpromo <code> <plan> <days> [max_uses] ──────────────────────

@router.message(Command("addpromo"))
async def admin_addpromo(message: Message):
    admin_id = int(os.environ.get("ADMIN_ID", 0))
    if message.from_user.id != admin_id:
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Usage: /addpromo <code> <plan> <days> [max_uses]")
        return

    code = parts[1]
    plan_name = parts[2].lower()
    days = int(parts[3])
    max_uses = int(parts[4]) if len(parts) > 4 else None

    await insert_or_replace_promo(code, plan_name, days, max_uses, now_str())
    await message.answer(
        f"✅ Promo '{code}' → plan '{plan_name}', {days} days, max uses: {max_uses or '∞'}"
    )


# ── Admin: /listpromos ─────────────────────────────────────────────────────

@router.message(Command("listpromos"))
async def admin_listpromos(message: Message):
    admin_id = int(os.environ.get("ADMIN_ID", 0))
    if message.from_user.id != admin_id:
        return

    rows = await fetch_all_promos()
    if not rows:
        await message.answer("Промокодов нет.")
        return

    lines = []
    for code, plan, days, max_uses, used in rows:
        limit = f"{used}/{max_uses}" if max_uses else f"{used}/∞"
        lines.append(f"• `{code}` → {plan}, {days}д, использований: {limit}")

    await message.answer("\n".join(lines), parse_mode="Markdown")
