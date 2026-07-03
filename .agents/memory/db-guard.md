---
name: db_guard self-healing schema
description: How db_guard.py works, its scope limits, and what to do when extending it
---

## Rule
`db_guard.py` runs `ensure_db_schema(conn)` synchronously in `main.py` inside `if __name__ == "__main__"`, before `asyncio.run(main())`. This is the only correct call site — it must precede the async event loop.

**Why:** The bot runs on UserLAnd/mobile where the process can be killed mid-upgrade, leaving the DB partially migrated. A sync guard before startup catches drift before any handler runs.

## How to apply
- Adding a new table or column to `database.py`? Mirror it in `DB_SCHEMA` in `db_guard.py` too — same constraints (UNIQUE, etc.) — so fresh installs get the full schema from the guard.
- `db_execute()` is a sync retry helper for sqlite3 connections only. The bot's runtime uses aiosqlite (async), so `db_execute` cannot be wired into handler paths without rewriting them. Use it only in sync startup scripts or one-off utilities.
- The in-memory `_schema_applied` flag prevents double-runs within one process. `db_execute` resets it before retrying so ensure_db_schema can re-run on OperationalError.

## UNIQUE constraints to keep in sync
These tables have UNIQUE constraints in both `database.py` and `db_guard.py` — keep them matched:
- `clients`: UNIQUE(psychologist_id, name)
- `auto_checkins`: UNIQUE(psychologist_id, client_name)
- `cohort_members`: UNIQUE(cohort_id, telegram_id)
- `cohort_attendance`: UNIQUE(session_id, member_id)
