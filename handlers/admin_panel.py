"""Hidden admin panel — accessible only to the bot owner (ADMIN_ID env var).

Entry point: /admin command (NOT registered in setMyCommands).
Non-admins get silent ignore. Every callback re-checks admin_id independently.
All destructive actions require a confirmation screen before executing.
All state-changing actions are logged to admin_actions_log table.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from database import DB_PATH, now_str
from states.admin_states import AdminBroadcastForm, AdminFindForm, AdminGrantPlanForm, AdminPromoForm

router = Router()
log = logging.getLogger(__name__)

_PAGE_SIZE = 10

# Set by main.py at startup
_BOT_START_TIME: datetime = datetime.utcnow()


def set_start_time(dt: datetime) -> None:
    global _BOT_START_TIME
    _BOT_START_TIME = dt


# ── Admin guard ──────────────────────────────────────────────────────────────

def _get_admin_id() -> int:
    return int(os.environ.get("ADMIN_ID", "0"))


def _is_admin(uid: int) -> bool:
    a = _get_admin_id()
    return a != 0 and uid == a


# ── Shared keyboards ─────────────────────────────────────────────────────────

def _main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика",          callback_data="adm:stats"),
            InlineKeyboardButton(text="💳 Подписки",            callback_data="adm:subs"),
        ],
        [
            InlineKeyboardButton(text="🔍 Найти пользователя",  callback_data="adm:find"),
            InlineKeyboardButton(text="🗂 Когорты",             callback_data="adm:cohorts:0"),
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка",            callback_data="adm:broadcast"),
            InlineKeyboardButton(text="⚙️ Система",             callback_data="adm:system"),
        ],
        [
            InlineKeyboardButton(text="🎟 Промокоды",           callback_data="adm:promo"),
            InlineKeyboardButton(text="💾 Бэкап",               callback_data="adm:backup"),
        ],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Главная", callback_data="adm:home"),
    ]])


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="adm:cancel"),
    ]])


async def _edit_or_answer(msg, text: str, kb: InlineKeyboardMarkup, **kwargs):
    """Try to edit the existing message; fall back to a new message."""
    try:
        await msg.edit_text(text, reply_markup=kb, **kwargs)
    except Exception:
        await msg.answer(text, reply_markup=kb, **kwargs)


# ── DB helpers ───────────────────────────────────────────────────────────────

async def _apply_plan_db(target_id: int, plan_name: str, days: int | None) -> str | None:
    """Insert/update user_plans and log the action. Returns expires_at or None."""
    expires_at = (
        (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        if days else None
    )
    action_type = "revoke_plan" if plan_name == "start" else "give_plan"
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
        await db.execute(
            "INSERT INTO admin_actions_log (action_type, details, created_at_utc) VALUES (?,?,?)",
            (
                action_type,
                f"user_id={target_id} plan={plan_name} days={days}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        await db.commit()
    return expires_at


async def _get_broadcast_recipients(audience: str) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        if audience == "all":
            cur = await db.execute("SELECT user_id FROM psychologists")
        elif audience == "start":
            cur = await db.execute(
                """SELECT p.user_id FROM psychologists p
                   LEFT JOIN user_plans up ON up.user_id = p.user_id
                   WHERE COALESCE(up.plan, 'start') = 'start'"""
            )
        else:  # pro
            cur = await db.execute(
                """SELECT p.user_id FROM psychologists p
                   JOIN user_plans up ON up.user_id = p.user_id
                   WHERE up.plan = 'pro'
                     AND (up.expires_at IS NULL OR up.expires_at > datetime('now'))"""
            )
        return [row[0] for row in await cur.fetchall()]


# ── Entry point: /admin ───────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return  # silent ignore — do NOT reveal the command exists
    await state.clear()
    await message.answer(
        "🔐 *Административная панель*", reply_markup=_main_kb(), parse_mode="Markdown"
    )


# ── Home / cancel ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:home")
async def adm_home(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await _edit_or_answer(
        callback.message,
        "🔐 *Административная панель*",
        _main_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "adm:cancel")
async def adm_cancel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer("Отменено")
    await _edit_or_answer(
        callback.message,
        "🔐 *Административная панель*",
        _main_kb(),
        parse_mode="Markdown",
    )


# ── Section: Statistics ──────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()

    now = datetime.utcnow()
    ago7  = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    ago30 = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB_PATH) as db:
        def _q(sql, *args):
            return db.execute(sql, args)

        (total_psychs,) = await (await _q("SELECT COUNT(*) FROM psychologists")).fetchone()
        (new_7d,)       = await (await _q(
            "SELECT COUNT(*) FROM psychologists WHERE created_at >= ?", ago7)).fetchone()
        (new_30d,)      = await (await _q(
            "SELECT COUNT(*) FROM psychologists WHERE created_at >= ?", ago30)).fetchone()
        (total_clients,) = await (await _q("SELECT COUNT(*) FROM clients")).fetchone()
        (total_cohorts,) = await (await _q("SELECT COUNT(*) FROM cohorts")).fetchone()
        (total_members,) = await (await _q(
            "SELECT COUNT(*) FROM cohort_members WHERE status = 'active'")).fetchone()
        (sess_today,)   = await (await _q(
            "SELECT COUNT(*) FROM sessions WHERE scheduled_at >= ? AND scheduled_at < ?",
            today, tomorrow)).fetchone()
        (sess_7d,)      = await (await _q(
            "SELECT COUNT(*) FROM sessions WHERE scheduled_at >= ?", ago7)).fetchone()
        (sess_total,)   = await (await _q("SELECT COUNT(*) FROM sessions")).fetchone()
        try:
            (active_fsm,) = await (await _q(
                "SELECT COUNT(*) FROM fsm_storage WHERE state IS NOT NULL AND state != 'None'"
            )).fetchone()
        except Exception:
            active_fsm = "н/д"

    db_mb = os.path.getsize(DB_PATH) / 1024 / 1024

    text = (
        f"📊 *Статистика*\n\n"
        f"👤 Психологов: *{total_psychs}*  (за 7 дн: +{new_7d}, за 30 дн: +{new_30d})\n"
        f"🧑 Клиентов всего: *{total_clients}*\n"
        f"🗂 Когорт: *{total_cohorts}*  ·  участников: *{total_members}*\n\n"
        f"📅 Сессий:\n"
        f"  • Сегодня: {sess_today}\n"
        f"  • За 7 дней: {sess_7d}\n"
        f"  • Всего: {sess_total}\n\n"
        f"🤖 Активных FSM-диалогов: {active_fsm}\n"
        f"💾 Размер БД: {db_mb:.2f} МБ"
    )
    await _edit_or_answer(callback.message, text, _back_kb(), parse_mode="Markdown")


# ── Section: Subscriptions ───────────────────────────────────────────────────

def _subs_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏰ Истекают в 7 дней", callback_data="adm:subs:exp:0")],
        [InlineKeyboardButton(text="🎁 Выдать / отозвать тариф", callback_data="adm:subs:grant")],
        [InlineKeyboardButton(text="⬅️ Главная", callback_data="adm:home")],
    ])


@router.callback_query(F.data == "adm:subs")
async def adm_subs(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT COALESCE(up.plan, 'start') AS p, COUNT(*)
               FROM psychologists ps
               LEFT JOIN user_plans up ON up.user_id = ps.user_id
               GROUP BY p ORDER BY p"""
        )
        dist = await cur.fetchall()

    dist_str = "\n".join(f"  • {plan.upper()}: {cnt}" for plan, cnt in dist) or "  нет данных"
    text = f"💳 *Подписки*\n\nРаспределение:\n{dist_str}"
    await _edit_or_answer(callback.message, text, _subs_kb(), parse_mode="Markdown")


@router.callback_query(F.data.regexp(r"^adm:subs:exp:\d+$"))
async def adm_subs_expiring(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT p.user_id, p.username, up.plan, up.expires_at
               FROM user_plans up
               JOIN psychologists p ON p.user_id = up.user_id
               WHERE up.expires_at IS NOT NULL
                 AND up.expires_at > datetime('now')
                 AND up.expires_at <= datetime('now', '+7 days')
               ORDER BY up.expires_at"""
        )
        rows = await cur.fetchall()

    total = len(rows)
    page_rows = rows[page * _PAGE_SIZE:(page + 1) * _PAGE_SIZE]

    if not rows:
        text = "⏰ *Истекают в ближайшие 7 дней*\n\n_Нет истекающих подписок._"
    else:
        items = "\n".join(
            f"  • `{uid}` (@{uname or '—'}) · {plan.upper()} · до {exp}"
            for uid, uname, plan, exp in page_rows
        )
        text = f"⏰ *Истекают в 7 дней* (стр. {page + 1}):\n\n{items}"

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="← Пред.", callback_data=f"adm:subs:exp:{page - 1}"))
    if (page + 1) * _PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Далее →", callback_data=f"adm:subs:exp:{page + 1}"))

    kb_rows = []
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="⬅️ Подписки", callback_data="adm:subs")])
    await _edit_or_answer(
        callback.message, text,
        InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown"
    )


# ── Grant plan FSM ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:subs:grant")
async def adm_subs_grant(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await state.set_state(AdminGrantPlanForm.target_id)
    await callback.message.answer(
        "Введите *Telegram ID* пользователя (число):",
        reply_markup=_cancel_kb(), parse_mode="Markdown"
    )


@router.callback_query(F.data.regexp(r"^adm:grant_for:\d+$"))
async def adm_grant_for(callback: CallbackQuery, state: FSMContext):
    """From user card — pre-fill target_id, then ask plan."""
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    target_id = int(callback.data.rsplit(":", 1)[-1])
    await state.clear()
    await callback.answer()
    await state.update_data(target_id=target_id)
    await state.set_state(AdminGrantPlanForm.plan_name)
    await callback.message.answer(
        f"Пользователь: `{target_id}`\nВведите тариф — `start` или `pro`:",
        reply_markup=_cancel_kb(), parse_mode="Markdown"
    )


@router.callback_query(F.data.regexp(r"^adm:grant_pro:\d+$"))
async def adm_grant_pro(callback: CallbackQuery, state: FSMContext):
    """From user card — pre-fill target_id + plan='pro', ask only days."""
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    target_id = int(callback.data.rsplit(":", 1)[-1])
    await state.clear()
    await callback.answer()
    await state.update_data(target_id=target_id, plan_name="pro")
    await state.set_state(AdminGrantPlanForm.days)
    await callback.message.answer(
        f"Выдать *Pro* пользователю `{target_id}`\n\nСрок в днях (0 — бессрочно):",
        reply_markup=_cancel_kb(), parse_mode="Markdown"
    )


@router.message(AdminGrantPlanForm.target_id)
async def adm_grant_got_target(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ Нужен числовой Telegram ID. Попробуйте ещё раз:", reply_markup=_cancel_kb())
        return
    await state.update_data(target_id=uid)
    await state.set_state(AdminGrantPlanForm.plan_name)
    await message.answer(
        f"Пользователь: `{uid}`\nВведите тариф — `start` или `pro`:",
        reply_markup=_cancel_kb(), parse_mode="Markdown"
    )


@router.message(AdminGrantPlanForm.plan_name)
async def adm_grant_got_plan(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    plan = (message.text or "").strip().lower()
    if plan not in ("start", "pro"):
        await message.answer("❌ Допустимые значения: `start` или `pro`", reply_markup=_cancel_kb(), parse_mode="Markdown")
        return
    await state.update_data(plan_name=plan)
    if plan == "start":
        await state.update_data(days=None)
        await state.set_state(AdminGrantPlanForm.confirm)
        await _send_grant_confirm(message, await state.get_data())
    else:
        await state.set_state(AdminGrantPlanForm.days)
        await message.answer("Срок в днях (0 — бессрочно):", reply_markup=_cancel_kb())


@router.message(AdminGrantPlanForm.days)
async def adm_grant_got_days(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    try:
        raw = int((message.text or "").strip())
        if raw < 0:
            raise ValueError
        days = None if raw == 0 else raw
    except (ValueError, AttributeError):
        await message.answer("❌ Введите целое число ≥ 0:", reply_markup=_cancel_kb())
        return
    await state.update_data(days=days)
    await state.set_state(AdminGrantPlanForm.confirm)
    await _send_grant_confirm(message, await state.get_data())


async def _send_grant_confirm(target: Message, data: dict) -> None:
    target_id = data["target_id"]
    plan_name = data["plan_name"]
    days: int | None = data.get("days")
    if days:
        exp_str = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")
    else:
        exp_str = "никогда"
    action_label = "Отозвать (→ Start)" if plan_name == "start" else f"Выдать {plan_name.upper()}"
    text = (
        f"🔔 *Подтвердите действие*\n\n"
        f"Пользователь: `{target_id}`\n"
        f"Действие: {action_label}\n"
        f"Истекает: {exp_str}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, применить", callback_data="adm:grant_ok"),
        InlineKeyboardButton(text="❌ Отмена",        callback_data="adm:grant_cancel"),
    ]])
    await target.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "adm:grant_ok", AdminGrantPlanForm.confirm)
async def adm_grant_ok(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    target_id: int = data["target_id"]
    plan_name: str = data["plan_name"]
    days: int | None = data.get("days")
    await state.clear()
    await callback.answer("Применяю...")

    expires_at = await _apply_plan_db(target_id, plan_name, days)
    label = "отозван (→ Start)" if plan_name == "start" else f"выдан {plan_name.upper()}"
    await callback.message.edit_text(
        f"✅ Тариф *{label}* для пользователя `{target_id}`\nИстекает: {expires_at or 'никогда'}",
        reply_markup=_back_kb(), parse_mode="Markdown"
    )
    log.info("ADMIN: %s plan='%s' user=%d days=%s", "revoke" if plan_name == "start" else "give", plan_name, target_id, days)


@router.callback_query(F.data == "adm:grant_cancel", AdminGrantPlanForm.confirm)
async def adm_grant_cancel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=_back_kb())


# ── Section: Find user ───────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:find")
async def adm_find(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()
    await state.set_state(AdminFindForm.query)
    await _edit_or_answer(
        callback.message,
        "🔍 Введите *Telegram ID* (число) или *@username*:",
        _cancel_kb(), parse_mode="Markdown"
    )


@router.message(AdminFindForm.query)
async def adm_find_got_query(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    query = (message.text or "").strip()
    await state.clear()

    async with aiosqlite.connect(DB_PATH) as db:
        if query.lstrip("+").isdigit() and not query.startswith("@"):
            uid = int(query)
            cur = await db.execute(
                """SELECT p.user_id, p.username, p.created_at,
                          COALESCE(up.plan, 'start') AS plan, up.expires_at,
                          COUNT(DISTINCT c.id) AS client_count
                   FROM psychologists p
                   LEFT JOIN user_plans up ON up.user_id = p.user_id
                   LEFT JOIN clients c ON c.psychologist_id = p.user_id
                   WHERE p.user_id = ? GROUP BY p.user_id""", (uid,)
            )
        else:
            uname = query.lstrip("@")
            cur = await db.execute(
                """SELECT p.user_id, p.username, p.created_at,
                          COALESCE(up.plan, 'start') AS plan, up.expires_at,
                          COUNT(DISTINCT c.id) AS client_count
                   FROM psychologists p
                   LEFT JOIN user_plans up ON up.user_id = p.user_id
                   LEFT JOIN clients c ON c.psychologist_id = p.user_id
                   WHERE p.username = ? GROUP BY p.user_id""", (uname,)
            )
        row = await cur.fetchone()

    if not row:
        await message.answer(
            f"😕 Пользователь *не найден*: `{query}`",
            reply_markup=_back_kb(), parse_mode="Markdown"
        )
        return

    uid, uname, created_at, plan, expires_at, client_count = row
    exp_str = expires_at or "—"
    text = (
        f"👤 *Пользователь*\n\n"
        f"ID: `{uid}`\n"
        f"@username: {('@' + uname) if uname else '—'}\n"
        f"Зарегистрирован: {created_at or '—'}\n"
        f"Тариф: *{plan.upper()}* (до {exp_str})\n"
        f"Клиентов: {client_count}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💎 Выдать Pro",     callback_data=f"adm:grant_pro:{uid}"),
            InlineKeyboardButton(text="🔄 Изменить тариф", callback_data=f"adm:grant_for:{uid}"),
        ],
        [InlineKeyboardButton(text="⬅️ Главная", callback_data="adm:home")],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


# ── Section: Cohorts ─────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^adm:cohorts:\d+$"))
async def adm_cohorts(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()

    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT c.id, c.name, c.status, COUNT(cm.telegram_id) AS cnt
               FROM cohorts c
               LEFT JOIN cohort_members cm ON cm.cohort_id = c.id AND cm.status = 'active'
               GROUP BY c.id ORDER BY c.created_at DESC"""
        )
        all_cohorts = await cur.fetchall()
        (new_superv,) = await (await db.execute(
            "SELECT COUNT(*) FROM supervision_cases WHERE created_at >= ?", (week_ago,)
        )).fetchone()

    total = len(all_cohorts)
    page_rows = all_cohorts[page * _PAGE_SIZE:(page + 1) * _PAGE_SIZE]
    items = "\n".join(
        f"  #{cid} {name} [{status}] · {cnt} уч."
        for cid, name, status, cnt in page_rows
    ) or "  _нет когорт_"

    text = (
        f"🗂 *Когорты* (стр. {page + 1}, всего {total})\n\n"
        f"{items}\n\n"
        f"📋 Новых кейсов супервизии за неделю: *{new_superv}*"
    )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="← Пред.", callback_data=f"adm:cohorts:{page - 1}"))
    if (page + 1) * _PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Далее →", callback_data=f"adm:cohorts:{page + 1}"))

    kb_rows = []
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="⬅️ Главная", callback_data="adm:home")])
    await _edit_or_answer(
        callback.message, text,
        InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown"
    )


# ── Section: Broadcast ───────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="adm:bc:all")],
        [
            InlineKeyboardButton(text="🟢 Только Start", callback_data="adm:bc:start"),
            InlineKeyboardButton(text="💎 Только Pro",   callback_data="adm:bc:pro"),
        ],
        [InlineKeyboardButton(text="⬅️ Главная", callback_data="adm:home")],
    ])
    await _edit_or_answer(
        callback.message,
        "📢 *Рассылка*\n\nВыберите аудиторию:",
        kb, parse_mode="Markdown"
    )


_AUDIENCE_LABELS = {"all": "Все", "start": "только Start", "pro": "только Pro"}


@router.callback_query(F.data.regexp(r"^adm:bc:(all|start|pro)$"))
async def adm_bc_audience(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    audience = callback.data.rsplit(":", 1)[-1]
    await state.update_data(bc_audience=audience)
    await state.set_state(AdminBroadcastForm.text)
    await callback.answer()

    label = _AUDIENCE_LABELS[audience]
    await _edit_or_answer(
        callback.message,
        f"📢 Аудитория: *{label}*\n\nВведите текст рассылки:",
        _cancel_kb(), parse_mode="Markdown"
    )


@router.message(AdminBroadcastForm.text)
async def adm_bc_got_text(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    bc_text = (message.text or "").strip()
    if not bc_text:
        await message.answer("❌ Текст не может быть пустым:", reply_markup=_cancel_kb())
        return

    await state.update_data(bc_text=bc_text)
    data = await state.get_data()
    audience = data.get("bc_audience", "all")

    recipients = await _get_broadcast_recipients(audience)
    count = len(recipients)
    await state.update_data(bc_count=count)
    await state.set_state(AdminBroadcastForm.confirm)

    preview = bc_text[:200] + ("…" if len(bc_text) > 200 else "")
    label = _AUDIENCE_LABELS.get(audience, audience)
    text = (
        f"📢 *Подтверждение рассылки*\n\n"
        f"Аудитория: {label}\n"
        f"Получателей: *{count}*\n\n"
        f"Текст:\n{preview}"
    )

    if count == 0:
        await message.answer(
            "⚠️ В этой аудитории *0 получателей* — рассылка невозможна.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Рассылка", callback_data="adm:broadcast"),
            ]]),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, отправить", callback_data="adm:bc_ok"),
        InlineKeyboardButton(text="❌ Отмена",        callback_data="adm:bc_cancel"),
    ]])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "adm:bc_ok", AdminBroadcastForm.confirm)
async def adm_bc_ok(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    data = await state.get_data()
    audience: str = data.get("bc_audience", "all")
    bc_text: str  = data.get("bc_text", "")
    await state.clear()
    await callback.answer("Запускаю рассылку…")
    await callback.message.edit_text("⏳ Рассылка запущена…", reply_markup=None)

    recipients = await _get_broadcast_recipients(audience)
    sent = failed = 0
    for uid in recipients:
        try:
            await bot.send_message(uid, bc_text)
            sent += 1
        except Exception as exc:
            failed += 1
            log.warning("ADMIN broadcast: failed uid=%d: %s", uid, exc)
        await asyncio.sleep(0.05)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO admin_actions_log (action_type, details, created_at_utc) VALUES (?,?,?)",
            (
                "broadcast",
                f"audience={audience} sent={sent} failed={failed} text={bc_text[:100]}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        await db.commit()

    label = _AUDIENCE_LABELS.get(audience, audience)
    await callback.message.answer(
        f"✅ *Рассылка завершена*\n\n"
        f"Аудитория: {label}\n"
        f"Отправлено: *{sent}*\n"
        f"Не доставлено: {failed}",
        reply_markup=_back_kb(), parse_mode="Markdown"
    )
    log.info("ADMIN: broadcast audience=%s sent=%d failed=%d", audience, sent, failed)


@router.callback_query(F.data == "adm:bc_cancel", AdminBroadcastForm.confirm)
async def adm_bc_cancel(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Рассылка отменена.", reply_markup=_back_kb())


# ── Section: System ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:system")
async def adm_system(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    await callback.answer()

    uptime = datetime.utcnow() - _BOT_START_TIME
    # Remove microseconds for clean display
    uptime_str = str(uptime).split(".")[0]
    db_mb = os.path.getsize(DB_PATH) / 1024 / 1024

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("PRAGMA journal_mode")
        (journal_mode,) = await cur.fetchone()

    text = (
        f"⚙️ *Система*\n\n"
        f"⏱ Аптайм: `{uptime_str}`\n"
        f"💾 Размер БД: {db_mb:.2f} МБ\n"
        f"📁 Журнальный режим: `{journal_mode}`"
    )
    await _edit_or_answer(callback.message, text, _back_kb(), parse_mode="Markdown")


# ── /backup — ручной бэкап (только для владельца) ────────────────────────────

@router.message(Command("backup"))
async def backup_cmd(message: Message, bot: Bot):
    """Немедленно создаёт резервную копию БД и отправляет в канал.

    Доступна только владельцу бота (ADMIN_ID). Не регистрируется в setMyCommands.
    """
    if not _is_admin(message.from_user.id):
        return  # тихий игнор — не раскрывать существование команды

    notice = await message.answer("⏳ Создаю резервную копию...")

    try:
        from backup_service import create_backup_and_send
        await create_backup_and_send(bot)
        await notice.edit_text("✅ Бэкап создан и отправлен в канал.")
    except ImportError:
        await notice.edit_text(
            "❌ `apscheduler` не установлен.\n"
            "Выполните: `pip install apscheduler`",
            parse_mode="Markdown",
        )
    except Exception as exc:
        log.exception("BACKUP CMD: ошибка при ручном бэкапе")
        await notice.edit_text(f"❌ Ошибка бэкапа:\n`{exc}`", parse_mode="Markdown")
