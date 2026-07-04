---
name: Timezone Migration
description: Full migration from synthetic "UTC+3" strings and utc_to_local()+strptime/strftime to to_user_tz() with proper IANA names.
---

## Rule
Display calls must use `to_user_tz(utc_dt_str, tz_name, fmt)` from `database.py`.
Storage calls keep using `local_to_utc(dt_str, offset_int)` with the integer offset.

**Why:** IANA names handle DST correctly; the old `utc_to_local(dt, offset_int)` was purely offset-arithmetic and would be wrong for any timezone observing DST.

## How to apply
- Any place that shows a datetime to a psychologist or client: use `to_user_tz()`.
- Any place that converts user input → UTC for storage: keep `local_to_utc()` with the integer offset.
- New timezone saves (preset buttons in menu.py, timezone.py, booking_settings.py, booking.py): use `OFFSET_TO_IANA.get(offset_min, format_offset(offset_min))` to get an IANA name.

## Key implementation details
- `to_user_tz()` in `database.py` has three-layer fallback: ZoneInfo(tz_name) → legacy "UTC±H" regex → Europe/Moscow.
- Defensive guard: if `tz_name` is an integer (accidental old `utc_offset` column value), it converts directly via `timedelta(minutes=tz_name)` without raising.
- `_tz_name(psych_id)` helper in `client_sessions.py` returns the IANA string for display; `_tz_offset(psych_id)` still exists for storage ops.
- `_slots_to_client_local()` in `booking.py` intentionally left with integer-offset arithmetic (slot picker embeds offset in callback_data; refactor would require threading tz_name through multiple round-trips).

## Client SELECT gotcha
When notifying clients about reschedules/cancellations, always query `timezone` (not `utc_offset`) so `to_user_tz` receives a string. Files fixed: `sessions.py` (reschedule_got_dt and reschedule_session_cmd), `booking.py` (approve handler).

## Backward compat
Existing DB rows with "UTC+3" format keep working via the regex fallback — no migration needed.
`get_user_timezone()` returns `(tz_name_str, offset_int)` tuple; callers should destructure as `tz_name, _ = await get_user_timezone(uid)` for display, `_, offset = ...` for storage.

## now_str() is UTC, not server-local
`now_str()` in `database.py` now explicitly returns `datetime.now(timezone.utc)` (not naive `datetime.now()`).
**Why:** it feeds `created_at`/`timestamp` columns (notes, checkins, supervision_cases, etc.) that get compared/displayed alongside genuinely-UTC scheduling columns; a naive local call is a footgun if the process ever runs on a non-UTC host.
**How to apply:** any new "recorded at" timestamp should use `now_str()` or `datetime.now(timezone.utc)` directly — never bare `datetime.now()`. When displaying these fields to a user, wrap with `to_user_tz(value, tz_name)` (get `tz_name` via `get_user_timezone(uid)`), same as scheduling fields.

## Known schema-mismatch pitfall
`psychologists` table columns are `user_id` (not `telegram_id`) and `utc_offset` (not `tz_offset`). A stale query in `main.py`'s recurring-session generator joined on `p.telegram_id`/`p.tz_offset` and silently broke the reminder loop every tick — check `PRAGMA table_info(psychologists)` if you see "no such column" errors mentioning psychologist fields.
