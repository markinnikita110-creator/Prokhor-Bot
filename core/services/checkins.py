"""Check-ins service layer.

No escalation/keyword-alert logic exists for check-in responses (see Этап 0
audit — this was discussed but never implemented). No plan-limit rules
either. Auto check-ins are configured via `auto_checkins` but are only
dispatched manually (via the /run_auto_checkins command) — there is no
scheduler wiring here, and this module intentionally does not add one
(pure relocation only). This is a thin pass-through re-export so handlers
have a single stable import point.
"""

from core.db.checkins_repository import (
    get_all_scores,
    get_all_scores_ordered,
    get_auto_checkin_client_names,
    get_auto_checkins_for_psych,
    get_last_n_checkins,
    get_last_n_positive_checkins,
    get_max_checkin_timestamp,
    get_positive_checkins_timestamped,
    get_positive_checkins_timestamped_ordered,
    get_positive_scores,
    get_recent_checkins_for_psych,
    insert_auto_checkin,
    insert_manual_checkin,
    update_auto_checkin_last_sent,
    upsert_auto_checkin_config,
)

__all__ = [
    "get_all_scores",
    "get_all_scores_ordered",
    "get_auto_checkin_client_names",
    "get_auto_checkins_for_psych",
    "get_last_n_checkins",
    "get_last_n_positive_checkins",
    "get_max_checkin_timestamp",
    "get_positive_checkins_timestamped",
    "get_positive_checkins_timestamped_ordered",
    "get_positive_scores",
    "get_recent_checkins_for_psych",
    "insert_auto_checkin",
    "insert_manual_checkin",
    "update_auto_checkin_last_sent",
    "upsert_auto_checkin_config",
]
