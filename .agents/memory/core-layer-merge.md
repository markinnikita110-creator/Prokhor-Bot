---
name: Core layer merge strategy
description: How to merge Prokhor refactor branches that have unrelated git histories; FSM security pattern for owner-checks at mutation endpoints.
---

## Merging branches with unrelated histories

`git merge --allow-unrelated-histories` creates mass conflicts when both sides touched the same large files. Better approach:
1. Identify new files from the incoming branch (no conflict) — copy them directly.
2. For changed files, take the integration-branch as base (it has the security work) and apply the other branch's extractions on top manually.
3. Commit the result as a manual merge commit with a detailed message explaining what each side contributed.

**Why:** The remote refactor branches (`origin/refactor/core-cohorts-base`, `origin/refactor/core-cohort-sessions`, `origin/refactor/core-reminders`) were created from different points and git considers them unrelated.

## Canonical function locations (avoid duplication)

- `get_cohort_name`, `get_active_members`, `seed_attendance_for_session` — defined in `core/db/cohorts_repository.py`.
- `core/db/cohort_sessions_repository.py` re-exports them via `from core.db.cohorts_repository import ...` — do NOT redefine them there.
- `verify_cohort_owner(cohort_id, uid) -> str | None` — defined in `core/db/cohorts_repository.py`; re-exported from `core/services/cohorts.py`.
- `generate_recurring_cohort_sessions` — defined in `core/db/cohort_sessions_repository.py`; imported in `main.py` from there.

## FSM owner-check pattern (security rule)

**Rule:** Every FSM completion handler that writes to the DB must re-verify ownership at the mutation point, even if an earlier FSM step already checked it.

**Why:** TOCTOU — user can transfer cohort ownership or lose access between the FSM start step and the final write step.

**How to apply:**
1. Store `cohort_id` in FSM state at the first step (where ownership is first checked).
2. In the terminal handler (got_value, clear, confirm, send): read `cohort_id = data["cohort_id"]`, then `if await verify_cohort_owner(cohort_id, uid) is None: await state.clear(); return`.
3. Applies to: `csdt_got_value`, `_finish_field_edit`, `cv2_ci_got_interval`, `cv2_broadcast_send`, `finalize_schedule`, `finalize_recurring_schedule`.

## integration-branch state after cohort-sessions merge

All three refactor branches now integrated:
- `core/db/cohorts_repository.py` — full CRUD + `verify_cohort_owner` (241 lines)
- `core/db/cohort_sessions_repository.py` — session CRUD + `generate_recurring_cohort_sessions`; re-exports helpers from cohorts_repository
- `core/services/cohorts.py` — cohort CRUD service layer
- `core/services/cohort_sessions.py` — `finalize_schedule`, `finalize_recurring_schedule` (both with owner-check)
- `core/services/reminders.py` — `notify_expiring_plans(bot)`, `send_individual_reminders(bot, now)`
- `handlers/cohorts.py` — pure Telegram handlers; no inline DB functions; 37 `verify_cohort_owner` calls
