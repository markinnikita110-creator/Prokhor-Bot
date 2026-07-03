# Prokhor

Telegram assistant for psychologists and coaches — manages clients, sessions, homework, notes, SOAP notes, analytics, check-ins, reminders, and exports, with full localization (EN/RU).

## Run & Operate

- **Workflow:** `Prokhor Bot` → `python main.py`
- **Required secret:** `BOT_TOKEN` — Telegram bot token from BotFather
- Database: SQLite, auto-created at startup via `database.py` (`init_db` + `migrate_db`)

## Stack

- Python 3.11, aiogram 3.x, aiosqlite
- FSM: aiogram MemoryStorage
- DB: SQLite (file-based, no external service needed)
- Localization: `translations.py` (EN/RU)

## Where things live

- `main.py` — entry point, bot setup, reminder loop, polling
- `database.py` — DB path, schema init/migration, helpers
- `handlers/` — one module per feature (clients, sessions, homework, notes, analytics, etc.)
- `keyboards.py` — shared inline keyboard builders
- `translations.py` — all user-facing strings (EN/RU)
- `documents/` — PDF files served to users (consent, privacy policy, terms)

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Files containing regex patterns should be written with `WriteFile`, not `Edit`, to avoid backslash truncation.
- Button UX uses split handlers and FSM injection — see `.agents/memory/prokhor-architecture.md`.
