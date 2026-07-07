"""Tariff plans — thin compatibility shim.

All logic has moved to:
  core/db/plans_repository.py  — SQL layer
  core/services/plans.py       — business rules

This file re-exports the public surface so any import path that was not yet
updated continues to work.
"""

from core.services.plans import (  # noqa: F401
    PLANS,
    check_client_limit,
    check_cohort_limit,
    check_cohort_member_limit,
    check_plan_limit,
    client_limit_msg,
    cohort_limit_msg,
    cohort_member_limit_msg,
    feature_blocked_msg,
    get_analytics_days_limit,
    get_user_plan,
)
