import logging
import re as _re
from datetime import datetime, timedelta, timezone as _tz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_log = logging.getLogger(__name__)


def now_str() -> str:
    """Current UTC time string — used for display-only created_at/timestamp fields.

    Always UTC so the whole system has one internal clock; convert with
    `to_user_tz()` whenever a value is shown to a psychologist or client.
    """
    return datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M")


def now_utc() -> str:
    """Current UTC time string — used for all scheduling and reminder comparisons."""
    return datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M")


# ── Timezone helpers ───────────────────────────────────────────────────────

def local_to_utc(dt_str: str, utc_offset_minutes: int) -> str:
    """Convert 'YYYY-MM-DD HH:MM' in user's local time to UTC for storage."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(minutes=utc_offset_minutes)
    return utc_dt.strftime("%Y-%m-%d %H:%M")


def utc_to_local(dt_str: str, utc_offset_minutes: int) -> str:
    """Convert 'YYYY-MM-DD HH:MM' UTC stored value to user's local time for display."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    local_dt = dt + timedelta(minutes=utc_offset_minutes)
    return local_dt.strftime("%Y-%m-%d %H:%M")


def format_offset(utc_offset_minutes: int) -> str:
    """Format offset integer as 'UTC+3' or 'UTC-5:30'."""
    sign = "+" if utc_offset_minutes >= 0 else "-"
    total = abs(utc_offset_minutes)
    hours, mins = divmod(total, 60)
    if mins:
        return f"UTC{sign}{hours}:{mins:02d}"
    return f"UTC{sign}{hours}"


def to_user_tz(
    utc_dt_str: str,
    tz_name: str | None,
    fmt: str = "%d.%m.%Y %H:%M",
    *,
    user_id: int | None = None,
) -> str:
    """Convert a UTC datetime string (as stored in DB) to the user's local time.

    utc_dt_str — "YYYY-MM-DD HH:MM" in UTC, as stored everywhere in the DB.
    tz_name    — IANA name ("Europe/Moscow") from psychologists.timezone or
                 clients.timezone.  Legacy "UTC+3" offset strings are handled
                 via a regex fallback so existing records keep working without
                 a forced data migration.
    fmt        — strftime format; default matches app-wide display standard.
    user_id    — optional; included in the warning log when conversion fails.

    Never raises: on any parse failure returns utc_dt_str unchanged.
    When timezone cannot be resolved the returned string is suffixed with
    \" ⚠️ (UTC)\" so the user sees an explicit indication rather than silently
    wrong local time, and a WARNING is emitted to the log.
    """
    try:
        dt_utc = datetime.strptime(utc_dt_str, "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("UTC")
        )
    except (ValueError, Exception):
        return utc_dt_str  # unparseable — return as-is

    # Defensive guard: caller accidentally passed an integer offset instead of a
    # string (e.g. old utc_offset column value). Convert on the fly so the
    # function never raises TypeError.
    if isinstance(tz_name, int):
        return (dt_utc + timedelta(minutes=tz_name)).strftime(fmt)

    tz = tz_name or ""

    # 1. Proper IANA name ("UTC", "Europe/Moscow", "Asia/Kolkata", …)
    if tz:
        try:
            return dt_utc.astimezone(ZoneInfo(tz)).strftime(fmt)
        except (ZoneInfoNotFoundError, KeyError):
            pass

        # 2. Legacy "UTC+3" / "UTC+5:30" strings saved by old preset buttons
        m = _re.match(r"^UTC([+-])(\d{1,2})(?::(\d{2}))?$", tz)
        if m:
            sign = 1 if m.group(1) == "+" else -1
            hours = int(m.group(2))
            mins = int(m.group(3) or 0)
            offset_min = sign * (hours * 60 + mins)
            return (dt_utc + timedelta(minutes=offset_min)).strftime(fmt)

    # 3. Timezone missing or unrecognised — show UTC with an explicit warning.
    #    Do NOT silently guess Moscow time: the user sees the wrong time with no
    #    indication, which is worse than an honest "this is UTC, please fix it".
    _log.warning(
        "to_user_tz: cannot resolve timezone %r (user_id=%s) — displaying UTC. "
        "User should update their timezone setting.",
        tz_name, user_id if user_id is not None else "unknown",
    )
    return dt_utc.strftime(fmt) + " ⚠️ (UTC)"
