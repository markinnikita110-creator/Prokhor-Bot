---
name: Prokhor bot architecture
description: Key decisions for the Prokhor aiogram 3.x split-handler button UX, menu hierarchy, cohort v2, supervision
---

## Project structure
- `main.py` — entry point; includes all routers, runs reminder_loop (individual + cohort sessions + cohort auto-checkins), calls init_db/migrate_db
- `handlers/` — router modules: menu, clients, sessions, homework, notes, analytics, checkins, settings, timezone, cohorts, supervision
- `states/` — FSM state files: client_states, session_states, homework_states, note_states, cohort_states, supervision_states, onboarding_states
- `keyboards.py` — all keyboard builders + MENU_* frozensets for reply-keyboard routing
- `translations.py` — single TEXTS dict; t(lang, key, **kwargs) helper
- `database.py` — all DB helpers

## Hierarchical ReplyKeyboardMarkup menu (added)
Main menu: 4 buttons (Individual | My Cohorts | Summary | Settings). Each opens a submenu reply keyboard. Back button (any language) returns to main menu.
- Individual: add client, client list, new note, schedule session, reminders
- My Cohorts: create cohort, cohort list (inline picker → cohort_action_keyboard)
- Summary: clients, cohorts (inline picker), statistics/analytics
- Settings: language, timezone, notifications stub

Builders: `main_menu_keyboard`, `individual_menu_keyboard`, `cohorts_menu_keyboard`, `summary_menu_keyboard`, `settings_menu_keyboard`. All in `keyboards.py`.

**Why:** Hierarchical menus are more discoverable than a flat 6-button row.

**How to apply:** New top-level feature → add `MENU_*` constant in `keyboards.py` via `_all("btn_key")`, add translation in both EN + RU, add handler in `handlers/menu.py`.

## MENU routing: no cross-imports between handler modules
`handlers/menu.py` imports only from `keyboards.py`, `states/`, and `database.py`. It never imports from other handler modules. To launch a foreign FSM, it sets the first FSM state directly; the owning router handles subsequent steps.

**Why:** Prevents circular imports (`handlers/cohorts.py` → `handlers/menu.py` → `handlers/cohorts.py`).

## Callback data format (all under 64 bytes)
Prefixes are strictly non-overlapping — verify that `startswith(prefix)` can't accidentally match a longer sibling.

- Legacy section nav: `m_clients`, `m_sessions`, `m_home`, etc.
- Client list/card: `cl_{page}`, `cc_{id}`, `ca_{id}_{action}`, `arc_{page}`, `ac_{id}`
- Session list/card: `sl_{page}`, `sc_{id}`, `sa_{id}_{action}`
- Cohort core: `cohort_join_{token}`, `cohort_type_{key}`
- Cohort session: `csch_*`, `csl_*`, `catt_*`
- Cohort v2 session list/detail (SESSIONS feature): `cv2_slist_{cid}` (list), `csd_{sid}` (detail), `csdt_*`/`cstp_*`/`cslk_*` (edit datetime/topic/link), `csdl_*`/`csdy_*`/`csdn_*` (delete session confirm/yes/no), `cspz_*` (pause/resume recurrence), `csrl_*`/`csry_*`/`csrn_*` (delete-recurrence-rule confirm/yes/no)
- Cohort v2 action: `cv2_pick_{cid}`, `cv2_mem_{cid}`, `cv2_sched_{cid}`, `cv2_att_{cid}`
- Cohort v2 checkins: `cv2_ci_{cid}`, `cv2_cistp_{cid}`, `cv2_cisum_{cid}`, `cv2_cisnd_{cid}`
- Cohort v2 notes: `cv2_notes_{cid}`, `cv2_nses_{sid}`, `cv2_nadd_{sid}`, `cv2_nsoap_{sid}`
- Cohort v2 broadcast: `cv2_bc_{cid}`, `cv2_bcsend`, `cv2_bccancel`
- Cohort v2 stats/archive: `cv2_stats_{cid}`, `cv2_arch_{cid}`, `cv2_arcy_{cid}`
- Cohort v2 back: `cv2_coh_list`
- Member checkin response: `cci_{cohort_id}_{member_tg}_{score}`
- Supervision: `sv_close_{case_id}`
- Other: `setlang_{lang}`, `checkin_{client_id}_{score}`, `fsm_cancel`, `noop`, `tz_set_{offset}`, `tz_custom`, `tz_skip`

## Cohort v2 features
- **Check-ins**: `cohort_checkin_configs` (config per cohort) + `cohort_checkins` (responses). Auto-send via `reminder_loop()` in `main.py` using interval_h. Member scores via `cci_*` callback handled in `handlers/cohorts.py`.
- **Session notes**: `cohort_session_notes` table. Plain note via `CohortSessionNoteForm` + 4-step SOAP via `CohortSOAPNoteForm`.
- **Broadcast**: `CohortBroadcastForm` — message text → preview confirm → send to all active members via `bot.send_message`.
- **Archive**: confirm prompt → `cv2_arcy_{cid}` sets `cohorts.status = 'archived'`. Archived cohorts excluded from auto-checkins.
- **Stats**: aggregate query (members, sessions, attendance %, check-in count/avg) — no extra tables.
- All handlers in `handlers/cohorts.py`.

## Supervision logbook
- Table: `supervision_cases` (alias, issue, hypothesis, intervention, outcome, status=open/closed)
- 5-step FSM: `SupervisionCaseForm`
- Commands: `/supervision_case`, `/supervision_logbook`, `/supervision_progress`
- Close callback: `sv_close_{case_id}`
- Handler: `handlers/supervision.py`; registered last in `handlers/__init__.py`

## Client card action dispatch
Single handler for `ca_{id}_{action}` using `F.data.regexp`. Split: `callback.data.split("_", 2)`.

## FSM "from card" vs "from menu"
Separate FSM classes: e.g. `ScheduleSessionFromCardForm` vs `ScheduleSessionForm`. From card: inject client_id/name into FSM data and skip to input state.

## Bot injection
Use `bot: Bot` parameter in handlers (aiogram 3.x auto-injects). Never use a global bot ref.

## states/__init__.py
All FSM state classes from all state files must be listed in `states/__init__.py` `__all__`. Missing exports cause ImportError.

## Individual client sessions (per-client session management)
- New module: `handlers/client_sessions.py` with `router` registered in `handlers/__init__.py` **before** `clients.router` to avoid prefix collision.
- Entry point: `ics_{client_id}` callback from client card "📅 Sessions" button (replaces old `ca_{id}_sched` one-shot button).
- Callback prefixes: `ics_` (list), `isd_` (detail), `isdt_/istp_/islk_` (edit dt/topic/link), `isdl_/isdy_` (delete ask/confirm), `ispz_` (pause/resume), `isrl_/isry_` (delete-rule ask/confirm), `isoa_` (add one-off), `isra_` (add recurring), `isrd_{n}/isrd_done` (weekday toggle).
- DB: `sessions` gained `topic TEXT`, `recurring INTEGER`, `days_of_week TEXT` columns; `clients` gained `recurring_paused INTEGER`. All added via `migrate_db()`.
- Recurring template: a `sessions` row with `recurring=1` is the rule; generated one-offs have `recurring=0`. `clients.recurring_paused` pauses generation. Daily generator: `generate_recurring_individual_sessions()` in `main.py`, called alongside the cohort generator in `reminder_loop()`.
- Individual menu: `btn_ind_schedule` row removed; `individual_menu_keyboard` is now 2 rows + Back.
- Client card back button from session list: `cc_{client_id}` (not `cl_{n}` which is page navigation).

## Recurring cohort sessions
- `cohort_sessions` has `recurring` (0/1) + `days_of_week` (CSV of Python weekday ints, Mon=0) columns; added via migration in `database.py migrate_db()`.
- Template-based generation: per cohort, the most recently created (`MAX(id)`) row with `recurring=1` supplies time/topic/link/days for generating future occurrences — there's no separate "schedule rule" table, the last recurring session row *is* the rule.
- `generate_recurring_cohort_sessions(cohort_id=None)` in `handlers/cohorts.py` fills a rolling 30-day horizon and is idempotent (skips dates that already have a session). Called once/day from `reminder_loop()` in `main.py` (gated by a module-level last-run-date variable) and once synchronously right after a new schedule is created, so the horizon isn't empty until the next daily tick.
- Recurring session creation auto-seeds `cohort_attendance` rows for active members (`_seed_attendance_for_session`); one-off sessions intentionally do not, to avoid changing existing one-off behavior.
- FSM callback prefixes `crsch_*`/`crday_*` are deliberately distinct from the one-off scheduling flow's `csch_*` prefixes to avoid FSM-state ambiguity between the two flows.
- `cohorts.recurring_paused` (0/1) lets a psychologist pause generation without deleting the rule; `generate_recurring_cohort_sessions` skips paused cohorts. Deleting the rule (vs pausing) clears `recurring=0, days_of_week=''` on all that cohort's `recurring=1` rows and resets `recurring_paused=0`, but keeps already-created sessions as plain one-offs.
- Manual session-number entry was removed from both scheduling entry points (`csch_coh_*`, `cv2_sched_*`) — the next session number is auto-computed as `max(existing)+1` so users never type it.
