"""Cohorts service layer — base cohort domain.

Re-exports all repository functions and wraps plan-limit business rules
so handlers have a single stable import point for the cohort domain.

Explicitly OUT of scope for this layer (future domains):
- cohort_sessions scheduling and recurring generation
- cohort check-in / broadcast features
- supervision cases
"""

from core.db.cohorts_repository import (
    add_member,
    archive_cohort,
    create_cohort,
    get_active_members,
    get_attendance_for_session,
    get_cohort_by_token,
    get_cohort_invite_token,
    get_cohort_name,
    get_cohort_status,
    get_cohorts_for_psych,
    get_member_count,
    get_next_manual_id,
    is_member,
    is_recurring_paused,
    list_all_cohorts_with_member_count,
    seed_attendance_for_session,
    set_recurring_paused,
    upsert_attendance,
    verify_cohort_owner,
)

__all__ = [
    # Cohort CRUD
    "create_cohort",
    "get_cohort_by_token",
    "get_cohorts_for_psych",
    "get_cohort_name",
    "get_cohort_invite_token",
    "get_cohort_status",
    "verify_cohort_owner",
    "archive_cohort",
    "is_recurring_paused",
    "set_recurring_paused",
    # Member CRUD
    "get_member_count",
    "is_member",
    "add_member",
    "get_active_members",
    "get_next_manual_id",
    # Attendance
    "upsert_attendance",
    "get_attendance_for_session",
    "seed_attendance_for_session",
    # Admin
    "list_all_cohorts_with_member_count",
    # Plan limit business rules
    "check_add_cohort",
    "check_add_cohort_member",
]


# ── Plan limit business rules ─────────────────────────────────────────────

async def check_add_cohort(user_id: int, lang: str = "ru") -> tuple[bool, str]:
    """Check whether this psychologist can create another cohort under their plan.

    Returns (allowed, error_message). error_message is empty when allowed.
    """
    from plan_limits import check_plan_limit
    return await check_plan_limit(user_id, "add_cohort", lang=lang)


async def check_add_cohort_member(
    user_id: int, cohort_id: int, lang: str = "ru"
) -> tuple[bool, str]:
    """Check whether another member can be added to this cohort under the plan.

    Returns (allowed, error_message). error_message is empty when allowed.
    """
    from plan_limits import check_plan_limit
    return await check_plan_limit(user_id, "add_cohort_member", cohort_id=cohort_id, lang=lang)
