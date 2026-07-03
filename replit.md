# Prokhor — Telegram Assistant for Psychologists

A Telegram bot built with **aiogram 3.x** and **SQLite** (via aiosqlite) that helps psychologists manage clients, sessions, bookings, homework, cohorts, check-ins, analytics, and more.

## Stack

- **Language:** Python 3.11
- **Telegram framework:** aiogram 3.x
- **Database:** SQLite (`prokhor.db`) via aiosqlite
- **Scheduling:** APScheduler (reminders, backups)
- **FSM storage:** Custom SQLite-backed storage (`fsm_storage.py`) — survives restarts

## How to run

The workflow **Prokhor Bot** runs `python main.py`. It starts polling automatically.

**Required secret:**
- `BOT_TOKEN` — Telegram bot token from @BotFather

**Environment variable (already set):**
- `ADMIN_ID` — Telegram user ID of the bot admin (shared env)

## Project structure

```
main.py            — entry point, registers routers, starts polling + scheduler
database.py        — DB schema, migrations, helper queries
translations.py    — all user-facing strings (i18n)
keyboards.py       — all InlineKeyboard / ReplyKeyboard builders
handlers/          — one module per feature area
  admin_panel.py   — admin commands
  booking.py       — session booking flow
  clients.py       — client management
  cohorts.py       — group cohort sessions
  analytics.py     — usage analytics
  ... (and more)
fsm_storage.py     — SQLite-backed FSM storage for aiogram
backup_service.py  — scheduled DB backup to Telegram channel
documents/         — PDF documents (consent, privacy policy, terms)
```

## User preferences

<!-- Agent: add user preferences here as they are confirmed. -->
