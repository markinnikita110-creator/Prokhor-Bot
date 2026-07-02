"""Tariff plans and promo codes handler."""

import logging
import os
from datetime import datetime, timedelta

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import DB_PATH, get_user_lang, now_str
from keyboards import main_menu_keyboard, settings_keyboard
from plan_limits import PLANS, get_user_plan
from translations import t

log = logging.getLogger(__name__)
router = Router()


class PromoForm(StatesGroup):
    waiting_code = State()


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

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT plan, duration_days, max_uses, used_count FROM promo_codes WHERE code = ?",
            (code,),
        )
        row = await cur.fetchone()

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
        expires_at = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO user_plans (user_id, plan, expires_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 plan       = excluded.plan,
                 expires_at = excluded.expires_at,
                 updated_at = excluded.updated_at""",
            (user_id, plan_name, expires_at, now_str()),
        )
        await db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
            (code,),
        )
        await db.commit()

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


# ── /myplan — view current plan ────────────────────────────────────────────

@router.message(Command("myplan"))
async def myplan_cmd(message: Message):
    await _send_myplan(message.from_user.id, message)


async def _send_myplan(user_id: int, target):
    """Send plan info to a Message or as a reply. target can be Message."""
    lang = await get_user_lang(user_id)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT plan, expires_at FROM user_plans WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()

    plan_name = row[0] if row else "start"
    expires_at = row[1] if row else None
    plan_display = PLANS.get(plan_name, {}).get("name", plan_name)
    plan_data = PLANS.get(plan_name, PLANS["start"])

    limits_ru = (
        f"• Клиентов: {plan_data['max_individual_clients'] or '∞'}\n"
        f"• Когорт: {plan_data['max_cohorts'] or '∞'}\n"
        f"• Участников в когорте: {plan_data['max_cohort_members'] or '∞'}\n"
        f"• Экспорт: {'✅' if plan_data['export'] else '❌'}\n"
        f"• Супервизия: {'✅' if plan_data['supervision'] else '❌'}"
    )
    limits_en = (
        f"• Clients: {plan_data['max_individual_clients'] or '∞'}\n"
        f"• Cohorts: {plan_data['max_cohorts'] or '∞'}\n"
        f"• Members per cohort: {plan_data['max_cohort_members'] or '∞'}\n"
        f"• Export: {'✅' if plan_data['export'] else '❌'}\n"
        f"• Supervision: {'✅' if plan_data['supervision'] else '❌'}"
    )

    if lang == "ru":
        header = f"📦 Ваш тариф: *{plan_display}*"
        if expires_at:
            header += f"\nДействует до: {expires_at}"
        text = f"{header}\n\n{limits_ru}"
    else:
        header = f"📦 Your plan: *{plan_display}*"
        if expires_at:
            header += f"\nValid until: {expires_at}"
        text = f"{header}\n\n{limits_en}"

    await target.answer(text, parse_mode="Markdown")


# ── st_myplan callback (from settings menu) ────────────────────────────────

@router.callback_query(F.data == "st_myplan")
async def settings_myplan(callback: CallbackQuery):
    await callback.answer()
    await _send_myplan(callback.from_user.id, callback.message)


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
        (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M") if days else None
    )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO user_plans (user_id, plan, expires_at, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 plan       = excluded.plan,
                 expires_at = excluded.expires_at,
                 updated_at = excluded.updated_at""",
            (target_id, plan_name, expires_at, now_str()),
        )
        await db.commit()

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

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO promo_codes
               (code, plan, duration_days, max_uses, used_count, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (code, plan_name, days, max_uses, now_str()),
        )
        await db.commit()

    await message.answer(
        f"✅ Promo '{code}' → plan '{plan_name}', {days} days, max uses: {max_uses or '∞'}"
    )


# ── Admin: /listpromos ─────────────────────────────────────────────────────

@router.message(Command("listpromos"))
async def admin_listpromos(message: Message):
    admin_id = int(os.environ.get("ADMIN_ID", 0))
    if message.from_user.id != admin_id:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT code, plan, duration_days, max_uses, used_count "
            "FROM promo_codes ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()

    if not rows:
        await message.answer("Промокодов нет.")
        return

    lines = []
    for code, plan, days, max_uses, used in rows:
        limit = f"{used}/{max_uses}" if max_uses else f"{used}/∞"
        lines.append(f"• `{code}` → {plan}, {days}д, использований: {limit}")

    await message.answer("\n".join(lines), parse_mode="Markdown")
