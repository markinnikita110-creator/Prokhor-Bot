---
name: Prokhor bot architecture
description: Key decisions for the Prokhor aiogram 3.x refactor into split-handler button UX
---

## Project structure
- `main.py` — entry point only; includes all routers, runs reminder_loop, calls init_db/migrate_db
- `handlers/` — 8 router modules (menu, clients, sessions, homework, notes, analytics, checkins, settings)
- `states/` — 4 FSM state files (client_states, session_states, homework_states, note_states)
- `keyboards.py` — all keyboard builders; exports frozensets like MENU_CLIENTS for text filters
- `translations.py` — single TEXTS dict; t(lang, key, **kwargs) helper
- `database.py` — all DB helpers

## Callback data format (all under 64 bytes)
- `m_clients`, `m_sessions`, `m_homework`, `m_analytics`, `m_checkins`, `m_settings`, `m_home`
- `cl_{page}` — client list page; `cc_{id}` — client card; `ca_{id}_{action}` — client action
- `arc_{page}` — archived list; `ac_{id}` — archived client card
- `sl_{page}` — session list; `sc_{id}` — session card; `sa_{id}_{action}` — session action
- `hw_add`, `hw_list`, `an_dash`, `an_alerts`, `ci_send`, `ci_auto`, `ci_recent`
- `setlang_en`, `setlang_ru`, `checkin_{client_id}_{score}`, `fsm_cancel`, `noop`
- `s_add`, `c_add`, `c_invite_pick`

## Client card action dispatch
Single handler for `ca_{id}_{action}` using `F.data.regexp(r"^ca_\d+_.+$")`.
Split: `callback.data.split("_", 2)` → [ca, id, action].

## FSM "from card" vs "from menu"
- From client card: set `client_id` + `client_name` in FSM data, jump directly to the input state
- From menu: start at the client_name state, then the input state
- Separate FSM classes: e.g., `ScheduleSessionFromCardForm` vs `ScheduleSessionForm`

## Bot injection
Use `bot: Bot` as a parameter in handlers (aiogram 3.x auto-injection). Never use a global BOT_REF.

## Menu button filtering
`keyboards.py` defines `MENU_CLIENTS = _all("btn_clients")` etc. as frozensets of all-language variants.
Handlers use `F.text.in_(MENU_CLIENTS)` to match regardless of user language.

## states/__init__.py must export everything
All FSM state classes from all 4 state files must be listed in `states/__init__.py` `__all__`.
Missing exports cause ImportError in handlers that import from `states`.

**Why:** aiogram 3.x dispatches FSM states globally across all included routers — a state set in one router is handled in another without issue. But the import must succeed.
