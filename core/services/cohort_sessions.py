"""Cohort sessions service layer.

Contains scenario functions that span multiple DB steps and interact with
Telegram (FSMContext, message replies). CRUD primitives live in
core.db.cohort_sessions_repository; ownership verification in
core.db.cohorts_repository.
"""

import logging
from datetime import datetime, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database import local_to_utc
from core.db.users_repository import get_user_lang, get_user_timezone
from core.db.cohorts_repository import verify_cohort_owner
from core.db.cohort_sessions_repository import (
    create_cohort_session,
    generate_recurring_cohort_sessions,
    get_cohort_name,
    get_cohort_sessions,
    seed_attendance_for_session,
)
from translations import t

log = logging.getLogger(__name__)

# Weekday display-name keys (0=Mon … 6=Sun), mirrored in translations.py
_DOW_KEYS = ["dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"]


async def finalize_schedule(source, state: FSMContext) -> None:
    """COHORT_SESSION: persist a one-off session after the FSM is complete."""
    uid = source.from_user.id
    lang = await get_user_lang(uid)
    data = await state.get_data()
    cohort_id = data["cohort_id"]
    # Re-verify ownership at mutation point
    if await verify_cohort_owner(cohort_id, uid) is None:
        log.warning("SECURITY: finalize_schedule owner mismatch cohort_id=%d uid=%d", cohort_id, uid)
        await state.clear()
        return
    session_number = data["session_number"]
    scheduled_at_utc = data["scheduled_at_utc"]
    scheduled_at_local = data["scheduled_at_local"]
    topic = data.get("topic", "")
    link = data.get("link", "")
    session_id = await create_cohort_session(cohort_id, session_number, scheduled_at_utc, topic, link)
    cohort_name = await get_cohort_name(cohort_id)
    topic_display = topic if topic else t(lang, "cs_no_topic")
    date_display = datetime.strptime(scheduled_at_local, "%Y-%m-%d %H:%M").strftime("%d.%m %H:%M")
    await state.clear()
    reply = t(lang, "cs_created", num=session_number, cohort=cohort_name,
              date=date_display, topic=topic_display)
    if isinstance(source, CallbackQuery):
        await source.answer()
        await source.message.answer(reply)
    else:
        await source.answer(reply)
    log.info("COHORT_SESSION: created session_id=%d cohort_id=%d num=%d by user_id=%d",
             session_id, cohort_id, session_number, uid)


async def finalize_recurring_schedule(source, state: FSMContext) -> None:
    """RECURRING: create the first occurrence as the recurring template, then
    immediately backfill the rest of the 30-day horizon for this cohort."""
    uid = source.from_user.id
    lang = await get_user_lang(uid)
    data = await state.get_data()
    cohort_id = data["cohort_id"]
    # Re-verify ownership at mutation point
    if await verify_cohort_owner(cohort_id, uid) is None:
        log.warning("SECURITY: finalize_recurring_schedule owner mismatch cohort_id=%d uid=%d",
                    cohort_id, uid)
        await state.clear()
        return
    days = sorted(data["days"])
    days_csv = ",".join(str(d) for d in days)
    time_local = data["time_local"]
    topic = data.get("topic", "")
    link = data.get("link", "")

    existing = await get_cohort_sessions(cohort_id)
    next_num = max((row[1] for row in existing), default=0) + 1

    # Find the soonest date (today or later) matching one of the picked weekdays.
    # NOTE: uses UTC "today" as the base day — close enough for scheduling purposes,
    # and consistent with how the daily generator advances through the horizon.
    today = datetime.utcnow().date()
    first_date = today
    for _ in range(7):
        if first_date.weekday() in days:
            break
        first_date += timedelta(days=1)

    _, p_offset = await get_user_timezone(uid)
    local_dt_str = f"{first_date.strftime('%Y-%m-%d')} {time_local}"
    scheduled_at_utc = local_to_utc(local_dt_str, p_offset)

    session_id = await create_cohort_session(
        cohort_id, next_num, scheduled_at_utc, topic, link,
        recurring=1, days_of_week=days_csv,
    )
    await seed_attendance_for_session(cohort_id, session_id)

    # Backfill the remaining occurrences in the 30-day horizon right away.
    await generate_recurring_cohort_sessions(cohort_id=cohort_id)

    cohort_name = await get_cohort_name(cohort_id)
    days_display = ", ".join(t(lang, _DOW_KEYS[d]) for d in days)
    await state.clear()
    reply = t(lang, "cs_recurring_created", cohort=cohort_name, days=days_display, time=time_local)
    if isinstance(source, CallbackQuery):
        await source.answer()
        await source.message.answer(reply)
    else:
        await source.answer(reply)
    log.info("RECURRING: created template session_id=%d cohort_id=%d days=%s by user_id=%d",
             session_id, cohort_id, days_csv, uid)
