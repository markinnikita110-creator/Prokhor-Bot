"""Individual session reminders and plan-expiry notifications.

Extracted from main.py — pure business-logic for one reminder pass.
The caller (main.py reminder_loop) owns the periodic while/sleep scheduling.

Explicitly OUT of scope:
- Cohort session reminders (cohort_sessions table) — separate future domain.
- Cohort auto check-ins (cohort_checkin_configs)   — separate future domain.
- generate_recurring_individual_sessions            — session generation,
  not a reminder; stays in main.py for now.

Original fixes preserved verbatim (audit §2):
  F1 — UTC time: `now` is datetime.utcnow() computed by reminder_loop
       and passed in; not recomputed here.
  F2 — Independent try/except around every bot.send_message call
       (psych and client wrapped separately).
  F3 — Reminder flags set AFTER both send attempts, outside any
       try/except, so a failed send never causes duplicate reminders.
  F4 — plan_expiring_tomorrow text via t(lang, …), not hardcoded.
  F5 — to_user_tz() with IANA timezone name for both psych and client.
"""

import logging
from datetime import datetime, timedelta

from core.db.clients_repository import get_client_lang, get_client_timezone
from core.db.plans_repository import fetch_expiring_plans
from core.services.sessions import (
    get_sessions_pending_reminders,
    mark_reminded_24h,
    mark_reminded_1h,
)
from database import get_user_lang, get_user_timezone, to_user_tz
from translations import t

log = logging.getLogger(__name__)


async def send_individual_reminders(bot, now: datetime) -> None:
    """One pass: check all confirmed individual sessions, send 24h/1h reminders.

    `now` must be datetime.utcnow() — caller is responsible for supplying a
    fresh UTC value so the entire reminder_loop tick uses a single consistent
    clock reading.
    """
    sessions = await get_sessions_pending_reminders()

    for sid, psych_id, client_name, scheduled_at_str, link, r24, r1h, client_tg in sessions:
        try:
            session_dt = datetime.strptime(scheduled_at_str, "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        delta = session_dt - now
        p_lang = await get_user_lang(psych_id)
        p_tz, _ = await get_user_timezone(psych_id)
        p_display = to_user_tz(scheduled_at_str, p_tz, "%H:%M")
        link_line = t(p_lang, "session_link_line", link=link) if link else ""

        # ── 24-hour reminder ───────────────────────────────────────────
        if not r24 and timedelta(hours=23) < delta <= timedelta(hours=25):
            # F2-psych: independent try/except — a blocked psych never
            # prevents the client message or the flag update.
            try:
                await bot.send_message(
                    psych_id,
                    t(p_lang, "reminder_psych_24h",
                      client=client_name, time=p_display) + link_line,
                )
            except Exception as e:
                log.warning("reminder 24h psych_id=%d sid=%d: %s", psych_id, sid, e)

            # F2-client: independent try/except — a blocked/missing client
            # chat never prevents the flag from being set.
            if client_tg:
                try:
                    c_lang = await get_client_lang(client_tg)
                    c_tz, _ = await get_client_timezone(client_tg)
                    c_display = to_user_tz(scheduled_at_str, c_tz, "%H:%M")
                    c_link = t(c_lang, "session_link_line", link=link) if link else ""
                    await bot.send_message(
                        client_tg,
                        t(c_lang, "reminder_client_24h", time=c_display) + c_link,
                    )
                except Exception as e:
                    log.warning("reminder 24h client_tg=%d sid=%d: %s", client_tg, sid, e)

            # F3: flag set after both attempts, outside any try/except —
            # even if both sends failed the flag is written to avoid spam.
            await mark_reminded_24h(sid)

        # ── 1-hour reminder ────────────────────────────────────────────
        elif not r1h and timedelta(minutes=50) < delta <= timedelta(minutes=70):
            # F2-psych
            try:
                await bot.send_message(
                    psych_id,
                    t(p_lang, "reminder_psych_1h",
                      client=client_name, time=p_display) + link_line,
                )
            except Exception as e:
                log.warning("reminder 1h psych_id=%d sid=%d: %s", psych_id, sid, e)

            # F2-client
            if client_tg:
                try:
                    c_lang = await get_client_lang(client_tg)
                    c_tz, _ = await get_client_timezone(client_tg)
                    c_display = to_user_tz(scheduled_at_str, c_tz, "%H:%M")
                    c_link = t(c_lang, "session_link_line", link=link) if link else ""
                    await bot.send_message(
                        client_tg,
                        t(c_lang, "reminder_client_1h", time=c_display) + c_link,
                    )
                except Exception as e:
                    log.warning("reminder 1h client_tg=%d sid=%d: %s", client_tg, sid, e)

            # F3: flag after both attempts
            await mark_reminded_1h(sid)


async def notify_expiring_plans(bot) -> None:
    """Send a reminder to every user whose paid plan expires tomorrow (UTC).

    Uses datetime.utcnow() throughout — consistent with how reminder_loop
    handles session scheduling.  expires_at values written before this fix
    used local server time, but the window is a full calendar day so the
    notification fires correctly even with a moderate timezone offset.

    Tariff SQL now lives in core/db/plans_repository.fetch_expiring_plans.
    """
    now = datetime.utcnow()
    # Window: calendar day starting tomorrow (UTC midnight → midnight+1)
    window_start = (now + timedelta(days=1)).strftime("%Y-%m-%d 00:00")
    window_end   = (now + timedelta(days=2)).strftime("%Y-%m-%d 00:00")

    rows = await fetch_expiring_plans(window_start, window_end)

    notified = 0
    for user_id, plan, expires_at in rows:
        try:
            # F4: t() with the user's own language — no hardcoded RU strings
            lang = await get_user_lang(user_id)
            p_tz, _ = await get_user_timezone(user_id)
            # F5: to_user_tz() with IANA name — honest ⚠️(UTC) if unknown
            date_display = to_user_tz(expires_at, p_tz, "%d.%m.%Y")
            await bot.send_message(
                user_id,
                t(lang, "plan_expiring_tomorrow", plan=plan, date=date_display),
            )
            notified += 1
        except Exception as e:
            log.warning("notify_expiring_plans user_id=%d: %s", user_id, e)

    if notified:
        log.info("notify_expiring_plans: notified %d user(s)", notified)
