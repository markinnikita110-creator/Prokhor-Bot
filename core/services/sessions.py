"""Sessions service layer.

Pure relocation of raw SQL that lived scattered across handlers/sessions.py,
handlers/client_sessions.py, handlers/booking.py, handlers/clients.py,
handlers/analytics.py, handlers/legal.py, handlers/admin_panel.py. No
business-rule logic exists separately from the handlers for this domain
(same pattern as checkins/notes/homework), so this is a thin pass-through
re-export giving handlers a single stable import point.

Explicitly OUT of scope for this relocation (left untouched, per user
instruction):
- main.py `reminder_loop` and `generate_recurring_individual_sessions` —
  still use raw SQL directly against `sessions`, not this module.
- `cohort_sessions` table (handlers/cohorts.py) — a fully separate table,
  no overlap with `sessions`.
- `handlers/booking_settings.py` — only touches booking_profile /
  availability_rules / availability_exceptions, never `sessions` directly.
- The `individual_sessions` table reference in handlers/clients.py
  (`_fetch_client_data`) — this table does not exist anywhere in the
  schema; the query is wrapped in a bare try/except that silently
  swallows the resulting error, so that code path is dead. Flagged to the
  user during Этап 0 audit, intentionally not fixed here.
"""

from core.db.sessions_repository import (
    confirm_booking,
    confirm_reschedule,
    count_all_sessions,
    count_sessions_for_psych,
    count_sessions_in_range,
    count_sessions_since,
    delete_recurring_sessions_for_client,
    delete_session,
    get_all_session_times,
    get_booked_slots_raw,
    get_last_session_time,
    get_next_session,
    get_session_card,
    get_session_client_and_time,
    get_session_for_booking_decision,
    get_session_for_reschedule_confirm,
    get_session_full,
    get_session_psych_and_client,
    get_sessions_for_client,
    get_sessions_for_export,
    get_upcoming_sessions,
    insert_oneoff_session,
    insert_pending_booking_session,
    insert_recurring_session,
    insert_session,
    propose_reschedule,
    session_exists_at,
    update_session_datetime,
    update_session_link,
    update_session_topic,
)

__all__ = [
    "confirm_booking",
    "confirm_reschedule",
    "count_all_sessions",
    "count_sessions_for_psych",
    "count_sessions_in_range",
    "count_sessions_since",
    "delete_recurring_sessions_for_client",
    "delete_session",
    "get_all_session_times",
    "get_booked_slots_raw",
    "get_last_session_time",
    "get_next_session",
    "get_session_card",
    "get_session_client_and_time",
    "get_session_for_booking_decision",
    "get_session_for_reschedule_confirm",
    "get_session_full",
    "get_session_psych_and_client",
    "get_sessions_for_client",
    "get_sessions_for_export",
    "get_upcoming_sessions",
    "insert_oneoff_session",
    "insert_pending_booking_session",
    "insert_recurring_session",
    "insert_session",
    "propose_reschedule",
    "session_exists_at",
    "update_session_datetime",
    "update_session_link",
    "update_session_topic",
]
