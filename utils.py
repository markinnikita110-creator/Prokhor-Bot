"""Shared utility helpers used across handler modules."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytz

from database import OFFSET_TO_IANA
from translations import t


def parse_timezone(arg: str) -> tuple[str, int] | None:
    """Parse a timezone argument into (tz_name, utc_offset_minutes) or None.

    Accepted formats:
      +3   -5   +12          — whole-hour offsets
      +5:30  -3:30  +05:30   — hour+minute offsets
      UTC                     — explicit UTC
      Europe/Moscow           — IANA timezone name (validated via ZoneInfo)

    Offset inputs (+3, +5:30, …) are mapped to an IANA name via OFFSET_TO_IANA
    where available, so the DB always receives a proper IANA identifier rather
    than a synthetic "UTC+3" string.  IANA name inputs are validated through
    ZoneInfo before being accepted; invalid names are rejected.
    """
    arg = arg.strip()

    # Whole-hour: +3  -5  +12
    m = re.match(r"^([+-])(\d{1,2})$", arg)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hours = int(m.group(2))
        if hours > 14:
            return None
        offset_min = sign * hours * 60
        iana = OFFSET_TO_IANA.get(offset_min, f"UTC{m.group(1)}{hours}")
        return (iana, offset_min)

    # Hour+minute: +5:30  -3:30  +05:30
    m = re.match(r"^([+-])(\d{1,2}):(\d{2})$", arg)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hours, mins = int(m.group(2)), int(m.group(3))
        if hours > 14 or mins >= 60:
            return None
        offset_min = sign * (hours * 60 + mins)
        iana = OFFSET_TO_IANA.get(offset_min, f"UTC{m.group(1)}{hours}:{m.group(3)}")
        return (iana, offset_min)

    # Explicit UTC
    if arg.upper() == "UTC":
        return ("UTC", 0)

    # Named IANA timezone — validate with ZoneInfo first, then compute offset via pytz
    try:
        ZoneInfo(arg)  # raises ZoneInfoNotFoundError if invalid
        tz = pytz.timezone(arg)
        aware_dt = tz.localize(datetime.now())
        offset_td = aware_dt.utcoffset()
        offset_mins = int(offset_td.total_seconds() // 60)
        return (arg, offset_mins)
    except (ZoneInfoNotFoundError, pytz.UnknownTimeZoneError, Exception):
        pass

    return None


def engagement_label(avg: float, lang: str) -> str:
    if avg >= 7:
        return t(lang, "good_stability")
    elif avg >= 4:
        return t(lang, "moderate")
    return t(lang, "risk_zone")


def smart_flags(scores: list, lang: str) -> list:
    flags = []
    real = [s for s in scores if s > 0]
    if len(real) >= 3:
        if sum(real[-3:]) / 3 < 4:
            flags.append(t(lang, "flag_risk"))
        if real[-3] > real[-2] > real[-1]:
            flags.append(t(lang, "flag_negative"))
    return flags


def chunks(lst: list, size: int):
    """Yield successive chunks of `size` from `lst`."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
