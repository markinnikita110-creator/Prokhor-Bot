"""Core service layer for the tariff / plans domain.

Business rules:
  - PLANS catalogue and feature flags
  - get_user_plan: reads the plan with expiry handling
  - limit checks: clients, cohorts, cohort members, feature gates
  - check_plan_limit: unified gate called by handlers and core/services/cohorts
  - get_analytics_days_limit: analytics window helper
  - limit message helpers (sync, no DB)
"""

import logging
from datetime import datetime, timezone

from core.db.plans_repository import (
    count_active_clients,
    count_cohort_members,
    count_cohorts,
    downgrade_user_plan,
    fetch_psychologist_lang,
    fetch_user_plan_row,
)

log = logging.getLogger(__name__)

# ── Plan catalogue ─────────────────────────────────────────────────────────

PLANS: dict[str, dict] = {
    "start": {
        "name": "Start",
        "max_individual_clients": 5,
        "max_cohorts": 2,
        "max_cohort_members": 15,
        "checkins": True,
        "analytics": "30days",
        "export": False,
        "supervision": False,
        "faq": False,
        "ai_assistant": False,
        "polls": False,
        "self_booking": False,
    },
    "pro": {
        "name": "Pro",
        "max_individual_clients": None,
        "max_cohorts": 10,
        "max_cohort_members": 50,
        "checkins": True,
        "analytics": True,
        "export": True,
        "supervision": True,
        "faq": True,
        "ai_assistant": True,
        "polls": True,
        "self_booking": True,
    },
}

_EXPIRED_MSG_RU = (
    "📦 Ваш тариф Pro истёк. Вы переведены на Start.\n"
    "Для продления введите промокод: /promo"
)
_EXPIRED_MSG_EN = (
    "📦 Your Pro plan has expired. You've been moved to Start.\n"
    "To renew, enter a promo code: /promo"
)


# ── Plan resolution ────────────────────────────────────────────────────────

async def get_user_plan(user_id: int, bot=None) -> dict:
    """Return the plan limits dict for the user.

    Handles expiry: if Pro has expired, downgrades to Start in DB and
    optionally notifies the user via bot.send_message.
    """
    try:
        row = await fetch_user_plan_row(user_id)

        if not row:
            return dict(PLANS["start"])

        plan_name, expires_at = row

        if expires_at:
            try:
                exp_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M")
            except ValueError:
                exp_dt = datetime.strptime(expires_at, "%Y-%m-%d")

            if exp_dt < datetime.now(timezone.utc).replace(tzinfo=None):
                await downgrade_user_plan(user_id)
                if bot:
                    try:
                        lang = await _get_plan_lang(user_id)
                        msg = _EXPIRED_MSG_RU if lang == "ru" else _EXPIRED_MSG_EN
                        await bot.send_message(user_id, msg)
                    except Exception as e:
                        log.warning("Could not notify user %d of plan expiry: %s", user_id, e)
                return dict(PLANS["start"])

        return dict(PLANS.get(plan_name, PLANS["start"]))

    except Exception as e:
        log.error("get_user_plan error for user %d: %s", user_id, e)
        return dict(PLANS["start"])


async def _get_plan_lang(user_id: int) -> str:
    try:
        return await fetch_psychologist_lang(user_id)
    except Exception:
        return "ru"


# ── Analytics helper ───────────────────────────────────────────────────────

async def get_analytics_days_limit(user_id: int) -> int | None:
    """Return max days for analytics history. 30 for Start, None for Pro."""
    plan = await get_user_plan(user_id)
    analytics = plan.get("analytics")
    if analytics == "30days":
        return 30
    elif analytics is True:
        return None
    return 0


# ── Individual limit checks ────────────────────────────────────────────────

async def check_client_limit(user_id: int) -> bool:
    plan = await get_user_plan(user_id)
    max_c = plan["max_individual_clients"]
    if max_c is None:
        return True
    try:
        return await count_active_clients(user_id) < max_c
    except Exception as e:
        log.error("check_client_limit error: %s", e)
        return True


async def check_cohort_limit(user_id: int) -> bool:
    plan = await get_user_plan(user_id)
    max_c = plan["max_cohorts"]
    if max_c is None:
        return True
    try:
        return await count_cohorts(user_id) < max_c
    except Exception as e:
        log.error("check_cohort_limit error: %s", e)
        return True


async def check_cohort_member_limit(cohort_id: int, user_id: int) -> bool:
    plan = await get_user_plan(user_id)
    max_m = plan["max_cohort_members"]
    if max_m is None:
        return True
    try:
        return await count_cohort_members(cohort_id) < max_m
    except Exception as e:
        log.error("check_cohort_member_limit error: %s", e)
        return True


# ── Unified gate ───────────────────────────────────────────────────────────

async def check_plan_limit(
    user_id: int,
    action: str,
    cohort_id: int | None = None,
    lang: str = "ru",
) -> tuple[bool, str]:
    """Unified gate check before any plan-limited action.

    action: 'add_client' | 'add_cohort' | 'add_cohort_member' | 'use_pro_feature'
    Returns (allowed, error_message).
    """
    plan = await get_user_plan(user_id)
    try:
        if action == "add_client":
            max_c = plan["max_individual_clients"]
            if max_c is not None:
                if await count_active_clients(user_id) >= max_c:
                    return False, client_limit_msg(lang)

        elif action == "add_cohort":
            max_c = plan["max_cohorts"]
            if max_c is not None:
                if await count_cohorts(user_id) >= max_c:
                    return False, cohort_limit_msg(lang)

        elif action == "add_cohort_member":
            if cohort_id is not None:
                max_m = plan["max_cohort_members"]
                if max_m is not None:
                    if await count_cohort_members(cohort_id) >= max_m:
                        return False, cohort_member_limit_msg(lang)

        elif action == "use_pro_feature":
            if not plan.get("supervision") and not plan.get("export"):
                return False, feature_blocked_msg(lang)

    except Exception as e:
        log.error("check_plan_limit error user=%d action=%s: %s", user_id, action, e)

    return True, ""


# ── Message helpers (sync) ─────────────────────────────────────────────────

def feature_blocked_msg(lang: str = "ru") -> str:
    if lang == "ru":
        return "⚠️ Эта функция доступна только на тарифе Pro.\nВведите промокод: /promo"
    return "⚠️ This feature is available on the Pro plan only.\nEnter a promo code: /promo"


def client_limit_msg(lang: str = "ru") -> str:
    if lang == "ru":
        return "⚠️ На тарифе Start можно добавить максимум 5 клиентов.\nДля расширения введите промокод: /promo"
    return "⚠️ The Start plan allows up to 5 clients.\nEnter a promo code to expand: /promo"


def cohort_limit_msg(lang: str = "ru") -> str:
    if lang == "ru":
        return "⚠️ На тарифе Start доступно до 2 когорт.\nДля расширения введите промокод: /promo"
    return "⚠️ The Start plan allows up to 2 cohorts.\nEnter a promo code to expand: /promo"


def cohort_member_limit_msg(lang: str = "ru") -> str:
    if lang == "ru":
        return "⚠️ На тарифе Start когорта вмещает до 15 участников.\nДля расширения введите промокод: /promo"
    return "⚠️ The Start plan allows up to 15 members per cohort.\nEnter a promo code to expand: /promo"
