"""BOOKING: client-facing public card and self-booking flow."""

import logging
from datetime import date, datetime, timedelta, timezone as _tz

import aiosqlite
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from database import (
    DB_PATH, OFFSET_TO_IANA, format_offset, get_client_lang, get_user_lang,
    get_user_timezone, now_str, now_utc, to_user_tz, utc_to_local,
)
from keyboards import cancel_keyboard, timezone_keyboard
from states.booking_states import BookingClientForm
from translations import t

router = Router()
log = logging.getLogger(__name__)

BOT_USERNAME = ""


def set_bot_username_booking_client(username: str):
    global BOT_USERNAME
    BOT_USERNAME = username


# ── Slot computation ────────────────────────────────────────────────────────

def _minutes_to_hhmm(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _hhmm_to_minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def compute_available_slots(
    rules: list,
    exceptions: list,
    booked_utc: set,
    psych_tz_offset: int,
    horizon_days: int = 14,
) -> list[str]:
    """Return list of available slot UTC strings ('YYYY-MM-DD HH:MM').

    Uses integer UTC offset (minutes) for the psychologist's timezone.
    Slots are generated in psych local time, then converted to UTC.
    """
    now_utc_dt = datetime.now(_tz.utc).replace(tzinfo=None)
    today_local = (now_utc_dt + timedelta(minutes=psych_tz_offset)).date()

    # Build a set of fully blocked dates and partial blocks
    blocked_dates: set[str] = set()
    partial_blocks: list[tuple[str, int, int]] = []  # (date, start_min, end_min)
    for date_str, start_time, end_time in exceptions:
        if start_time is None:
            blocked_dates.add(date_str)
        else:
            partial_blocks.append((
                date_str,
                _hhmm_to_minutes(start_time),
                _hhmm_to_minutes(end_time) if end_time else 1440,
            ))

    # Build rules index by weekday
    rules_by_wd: dict[int, dict] = {}
    for weekday, start_time, end_time, duration_min, buffer_min in rules:
        rules_by_wd[weekday] = {
            "start": _hhmm_to_minutes(start_time),
            "end": _hhmm_to_minutes(end_time),
            "duration": duration_min,
            "buffer": buffer_min,
        }

    available: list[str] = []
    for day_offset in range(horizon_days):
        check_date = today_local + timedelta(days=day_offset)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in blocked_dates:
            continue

        wd = check_date.weekday()  # 0=Mon..6=Sun
        if wd not in rules_by_wd:
            continue

        rule = rules_by_wd[wd]
        step = rule["duration"] + rule["buffer"]
        if step <= 0:
            continue

        partial = [(s, e) for d, s, e in partial_blocks if d == date_str]

        slot_start = rule["start"]
        while slot_start + rule["duration"] <= rule["end"]:
            slot_end = slot_start + rule["duration"]

            # Check partial blocks
            blocked = any(
                not (slot_end <= bs or slot_start >= be)
                for bs, be in partial
            )
            if not blocked:
                # Convert to UTC
                slot_hhmm = _minutes_to_hhmm(slot_start)
                local_dt_str = f"{date_str} {slot_hhmm}"
                local_dt = datetime.strptime(local_dt_str, "%Y-%m-%d %H:%M")
                utc_dt = local_dt - timedelta(minutes=psych_tz_offset)
                utc_str = utc_dt.strftime("%Y-%m-%d %H:%M")

                # Skip past slots
                if utc_dt <= now_utc_dt:
                    slot_start += step
                    continue

                # Skip already booked
                if utc_str not in booked_utc:
                    available.append(utc_str)

            slot_start += step

    return available


def _slots_to_client_local(slots_utc: list[str], client_offset: int) -> list[tuple[str, str, str]]:
    """Convert UTC slot strings to client local time.
    Returns list of (client_date_str, client_time_str, utc_str).
    """
    result = []
    for utc_str in slots_utc:
        utc_dt = datetime.strptime(utc_str, "%Y-%m-%d %H:%M")
        local_dt = utc_dt + timedelta(minutes=client_offset)
        result.append((
            local_dt.strftime("%Y-%m-%d"),
            local_dt.strftime("%H:%M"),
            utc_str,
        ))
    return result


# ── DB helpers ──────────────────────────────────────────────────────────────

async def get_booking_profile_by_slug(slug: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT psych_id, display_name, bio, timezone, booking_enabled "
            "FROM booking_profile WHERE slug = ?", (slug,))
        return await cur.fetchone()


async def get_psych_tz_offset(tz_name: str) -> int:
    """Return UTC offset in minutes for a booking profile timezone."""
    from utils import parse_timezone
    parsed = parse_timezone(tz_name)
    if parsed:
        return parsed[1]
    return 0


async def get_booked_slots(psych_id: int) -> set[str]:
    """Return UTC slot strings that are taken (confirmed or pending psych approval).
    Declined/deleted sessions are excluded so their slots reappear as free."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT scheduled_at FROM sessions WHERE psychologist_id = ? "
            "AND (booking_status IN ('confirmed', 'pending_psych') OR booking_status IS NULL)",
            (psych_id,))
        return {row[0] for row in await cur.fetchall()}


async def get_client_tz_offset(telegram_id: int) -> tuple[str, int]:
    """Return (tz_name, offset_minutes) for a telegram user from any client record."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone, utc_offset FROM clients WHERE telegram_id = ? LIMIT 1",
            (telegram_id,))
        row = await cur.fetchone()
    if row and row[1] != 0:
        return (row[0] or "UTC", row[1])
    if row and row[0] and row[0] != "UTC":
        return (row[0], row[1])
    return ("UTC", 0)


async def _ensure_client(psych_id: int, telegram_id: int, full_name: str) -> str:
    """Ensure a client record exists for this psych/client pair. Return client_name."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT name FROM clients WHERE psychologist_id = ? AND telegram_id = ?",
            (psych_id, telegram_id))
        row = await cur.fetchone()
        if row:
            return row[0]
        # Create new client record; handle name collision with suffix
        base_name = (full_name or f"Client {telegram_id}")[:50]
        name = base_name
        suffix = 1
        while True:
            cur2 = await db.execute(
                "SELECT 1 FROM clients WHERE psychologist_id = ? AND name = ?",
                (psych_id, name))
            if not await cur2.fetchone():
                break
            name = f"{base_name} {suffix}"
            suffix += 1
        from database import make_token
        await db.execute(
            "INSERT INTO clients (psychologist_id, name, created_at, invite_token, telegram_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (psych_id, name, now_str(), make_token(), telegram_id))
        await db.commit()
        log.info("BOOKING: auto-created client name='%s' psych_id=%d tg=%d",
                 name, psych_id, telegram_id)
        return name


# ── Public booking card (called from menu.py /start handler) ───────────────

async def show_booking_card(message: Message, slug: str, state: FSMContext):
    """Entry point when a user opens /start book_{slug}."""
    await state.clear()
    uid = message.from_user.id
    profile = await get_booking_profile_by_slug(slug)

    if not profile:
        await message.answer(t("en", "booking_profile_not_found"))
        return

    psych_id, display_name, bio, timezone, booking_enabled = profile

    if not booking_enabled:
        await message.answer(t("en", "booking_unavailable"))
        return

    # Determine client language
    lang = await get_client_lang(uid) if True else "en"

    text = t(lang, "booking_card_text",
             display_name=display_name or "Specialist",
             bio=bio or "")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(lang, "btn_booking_book"),
            callback_data=f"bkc_start_{psych_id}",
        )
    ]])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    log.info("BOOKING: card shown slug=%s uid=%d", slug, uid)


# ── Client booking flow ─────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bkc_start_\d+$"))
async def bkc_start_cb(callback: CallbackQuery, state: FSMContext):
    """Client taps 'Book a Session' — check timezone, then show dates."""
    await state.clear()
    psych_id = int(callback.data.split("_")[2])
    uid = callback.from_user.id
    lang = await get_client_lang(uid)
    await callback.answer()

    tz_name, tz_offset = await get_client_tz_offset(uid)
    if tz_name == "UTC" and tz_offset == 0:
        # Ask for timezone first
        await state.update_data(psych_id=psych_id, lang=lang)
        await state.set_state(BookingClientForm.timezone)
        await callback.message.answer(t(lang, "ask_client_tz_booking"),
                                      reply_markup=timezone_keyboard(lang))
        return

    await _show_booking_dates(callback.message, psych_id, lang, tz_offset)


@router.callback_query(BookingClientForm.timezone, F.data.regexp(r"^tz_set_-?\d+$"))
async def bkc_tz_preset(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    psych_id = data["psych_id"]
    lang = data.get("lang", "en")
    offset_min = int(callback.data.split("_")[2])
    tz_name = OFFSET_TO_IANA.get(offset_min, format_offset(offset_min))
    await callback.answer()
    # Save timezone to all client records for this user
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET timezone = ?, utc_offset = ? WHERE telegram_id = ?",
            (tz_name, offset_min, callback.from_user.id))
        await db.commit()
    await state.clear()
    await _show_booking_dates(callback.message, psych_id, lang, offset_min)


@router.callback_query(BookingClientForm.timezone, F.data == "tz_custom")
async def bkc_tz_custom(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.set_state(BookingClientForm.timezone_custom)
    await callback.answer()
    await callback.message.answer(t(lang, "ask_timezone_custom"))


@router.message(BookingClientForm.timezone_custom)
async def bkc_tz_text(message: Message, state: FSMContext):
    from utils import parse_timezone
    data = await state.get_data()
    psych_id = data["psych_id"]
    lang = data.get("lang", "en")
    parsed = parse_timezone(message.text.strip())
    if not parsed:
        await message.answer(t(lang, "timezone_invalid"))
        return
    tz_name, offset_min = parsed
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clients SET timezone = ?, utc_offset = ? WHERE telegram_id = ?",
            (tz_name, offset_min, message.from_user.id))
        await db.commit()
    await state.clear()
    await _show_booking_dates(message, psych_id, lang, offset_min)


async def _show_booking_dates(target, psych_id: int, lang: str, client_offset: int):
    """Compute available slots and show date picker."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT weekday, start_time, end_time, session_duration_min, buffer_min "
            "FROM availability_rules WHERE psych_id = ?", (psych_id,))
        rules = await cur.fetchall()
        cur = await db.execute(
            "SELECT date, start_time, end_time FROM availability_exceptions "
            "WHERE psych_id = ? AND type = 'blocked'", (psych_id,))
        exceptions = await cur.fetchall()
        cur = await db.execute(
            "SELECT timezone FROM psychologists WHERE user_id = ?", (psych_id,))
        psych_row = await cur.fetchone()

    psych_tz_name = psych_row[0] if psych_row and psych_row[0] else "UTC"
    psych_offset = await get_psych_tz_offset(psych_tz_name)
    booked_utc = await get_booked_slots(psych_id)

    slots_utc = compute_available_slots(rules, exceptions, booked_utc, psych_offset)

    if not slots_utc:
        await target.answer(t(lang, "booking_no_slots"))
        return

    # Group by client-local date
    slots_local = _slots_to_client_local(slots_utc, client_offset)
    dates_seen: list[str] = []
    for client_date, _, _ in slots_local:
        if client_date not in dates_seen:
            dates_seen.append(client_date)

    rows = [[InlineKeyboardButton(
        text=client_date,
        callback_data=f"bkc_date_{psych_id}_{client_date.replace('-', '')}_{client_offset}"
    )] for client_date in dates_seen[:20]]  # cap at 20 dates

    text = t(lang, "booking_dates_title")
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await target.edit_text(text, reply_markup=kb)
    except Exception:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.regexp(r"^bkc_date_\d+_\d{8}_-?\d+$"))
async def bkc_date_cb(callback: CallbackQuery):
    """Client selects a date — show slots for that date."""
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    date_compact = parts[3]  # YYYYMMDD
    client_offset = int(parts[4])
    lang = await get_client_lang(callback.from_user.id)
    await callback.answer()

    client_date_str = f"{date_compact[:4]}-{date_compact[4:6]}-{date_compact[6:]}"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT weekday, start_time, end_time, session_duration_min, buffer_min "
            "FROM availability_rules WHERE psych_id = ?", (psych_id,))
        rules = await cur.fetchall()
        cur = await db.execute(
            "SELECT date, start_time, end_time FROM availability_exceptions "
            "WHERE psych_id = ? AND type = 'blocked'", (psych_id,))
        exceptions = await cur.fetchall()
        cur = await db.execute(
            "SELECT timezone FROM psychologists WHERE user_id = ?", (psych_id,))
        psych_row = await cur.fetchone()

    psych_tz_name = psych_row[0] if psych_row and psych_row[0] else "UTC"
    psych_offset = await get_psych_tz_offset(psych_tz_name)
    booked_utc = await get_booked_slots(psych_id)
    slots_utc = compute_available_slots(rules, exceptions, booked_utc, psych_offset)
    slots_local = _slots_to_client_local(slots_utc, client_offset)

    day_slots = [(time_str, utc_str)
                 for c_date, time_str, utc_str in slots_local
                 if c_date == client_date_str]

    if not day_slots:
        await callback.message.answer(t(lang, "booking_no_slots"))
        return

    rows = [[InlineKeyboardButton(
        text=time_str,
        callback_data=(
            f"bkc_slot_{psych_id}_"
            f"{utc_str.replace('-','').replace(' ','T').replace(':','')}_{client_offset}"
        )
    )] for time_str, utc_str in day_slots]

    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_booking_back_dates"),
        callback_data=f"bkc_back_dates_{psych_id}_{client_offset}")])

    text = t(lang, "booking_slots_title", date=client_date_str)
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.regexp(r"^bkc_slot_\d+_\d{8}T\d{4}_-?\d+$"))
async def bkc_slot_cb(callback: CallbackQuery):
    """Client selects a slot — show confirmation screen."""
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    slot_compact = parts[3]  # YYYYMMDDTHHmm
    client_offset = int(parts[4])
    lang = await get_client_lang(callback.from_user.id)
    await callback.answer()

    # Decode slot_compact → UTC string
    utc_str = f"{slot_compact[:4]}-{slot_compact[4:6]}-{slot_compact[6:8]} {slot_compact[9:11]}:{slot_compact[11:13]}"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone FROM clients WHERE telegram_id = ? LIMIT 1",
            (callback.from_user.id,))
        c_tz_row = await cur.fetchone()
    client_tz = c_tz_row[0] if c_tz_row else None
    display = to_user_tz(utc_str, client_tz, "%d.%m.%Y %H:%M")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT display_name FROM booking_profile WHERE psych_id = ?", (psych_id,))
        row = await cur.fetchone()
    display_name = row[0] if row else "Specialist"

    text = t(lang, "booking_confirm_text",
             datetime=display, name=display_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, "btn_booking_confirm"),
            callback_data=f"bkc_confirm_{psych_id}_{slot_compact}_{client_offset}")],
        [InlineKeyboardButton(
            text=t(lang, "btn_booking_back_slots"),
            callback_data=f"bkc_slot_back_{psych_id}_{slot_compact[:8]}_{client_offset}")],
    ])
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.regexp(r"^bkc_slot_back_\d+_\d{8}_-?\d+$"))
async def bkc_slot_back_cb(callback: CallbackQuery):
    """Back from confirm → slots list."""
    parts = callback.data.split("_")
    psych_id = int(parts[3])
    date_compact = parts[4]
    client_offset = int(parts[5])
    lang = await get_client_lang(callback.from_user.id)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    # Re-trigger date selection
    fake_cb_data = f"bkc_date_{psych_id}_{date_compact}_{client_offset}"
    # Build and send slots keyboard directly
    client_date_str = f"{date_compact[:4]}-{date_compact[4:6]}-{date_compact[6:]}"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT weekday, start_time, end_time, session_duration_min, buffer_min "
            "FROM availability_rules WHERE psych_id = ?", (psych_id,))
        rules = await cur.fetchall()
        cur = await db.execute(
            "SELECT date, start_time, end_time FROM availability_exceptions "
            "WHERE psych_id = ? AND type = 'blocked'", (psych_id,))
        exceptions = await cur.fetchall()
        cur = await db.execute(
            "SELECT timezone FROM psychologists WHERE user_id = ?", (psych_id,))
        psych_row = await cur.fetchone()

    psych_tz_name = psych_row[0] if psych_row and psych_row[0] else "UTC"
    psych_offset = await get_psych_tz_offset(psych_tz_name)
    booked_utc = await get_booked_slots(psych_id)
    slots_utc = compute_available_slots(rules, exceptions, booked_utc, psych_offset)
    slots_local = _slots_to_client_local(slots_utc, client_offset)
    day_slots = [(time_str, utc_str)
                 for c_date, time_str, utc_str in slots_local
                 if c_date == client_date_str]
    if not day_slots:
        await callback.message.answer(t(lang, "booking_no_slots"))
        return
    rows = [[InlineKeyboardButton(
        text=time_str,
        callback_data=(
            f"bkc_slot_{psych_id}_"
            f"{utc_str.replace('-','').replace(' ','T').replace(':','')}_{client_offset}"
        )
    )] for time_str, utc_str in day_slots]
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_booking_back_dates"),
        callback_data=f"bkc_back_dates_{psych_id}_{client_offset}")])
    text = t(lang, "booking_slots_title", date=client_date_str)
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.regexp(r"^bkc_back_dates_\d+_-?\d+$"))
async def bkc_back_dates_cb(callback: CallbackQuery):
    """Back from slots → dates picker."""
    parts = callback.data.split("_")
    psych_id = int(parts[3])
    client_offset = int(parts[4])
    lang = await get_client_lang(callback.from_user.id)
    await callback.answer()
    await _show_booking_dates(callback.message, psych_id, lang, client_offset)


@router.callback_query(F.data.regexp(r"^bkc_confirm_\d+_\d{8}T\d{4}_-?\d+$"))
async def bkc_confirm_cb(callback: CallbackQuery, bot: Bot):
    """Client requests booking — rate-limit, then create pending_psych session."""
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    slot_compact = parts[3]
    client_offset = int(parts[4])
    uid = callback.from_user.id
    lang = await get_client_lang(uid)
    await callback.answer()

    utc_str = f"{slot_compact[:4]}-{slot_compact[4:6]}-{slot_compact[6:8]} {slot_compact[9:11]}:{slot_compact[11:13]}"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT timezone FROM clients WHERE telegram_id = ? LIMIT 1", (uid,))
        c_tz_row = await cur.fetchone()
    client_tz = c_tz_row[0] if c_tz_row else None
    display = to_user_tz(utc_str, client_tz, "%d.%m.%Y %H:%M")

    # Rate limit: max 5 requests per client per 24h (across all psychologists)
    cutoff = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM booking_requests_log "
            "WHERE client_telegram_id = ? AND requested_at_utc >= ?",
            (uid, cutoff))
        (req_count,) = await cur.fetchone()
    if req_count >= 5:
        await callback.message.answer(t(lang, "booking_limit_reached"))
        return

    # Ensure client record exists
    full_name = " ".join(filter(None, [
        callback.from_user.first_name or "",
        callback.from_user.last_name or "",
    ])).strip() or f"Client {uid}"
    try:
        client_name = await _ensure_client(psych_id, uid, full_name)
    except Exception as e:
        log.error("BOOKING: _ensure_client error: %s", e)
        await callback.message.answer(t(lang, "booking_error"))
        return

    # Log the request (counts toward daily limit regardless of outcome)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO booking_requests_log "
            "(client_telegram_id, psych_id, requested_at_utc) VALUES (?, ?, ?)",
            (uid, psych_id, now_utc()))
        await db.commit()

    # INSERT with UNIQUE constraint — slot may already be pending or confirmed
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO sessions "
                "(psychologist_id, client_name, scheduled_at, topic, booking_status) "
                "VALUES (?, ?, ?, ?, 'pending_psych')",
                (psych_id, client_name, utc_str, "self-booked"))
            session_id = cur.lastrowid
            await db.commit()
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            await callback.message.answer(t(lang, "booking_slot_taken"))
            await _show_booking_dates(callback.message, psych_id, lang, client_offset)
        else:
            log.error("BOOKING: INSERT error: %s", e)
            await callback.message.answer(t(lang, "booking_error"))
        return

    # Get psych display name
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT display_name FROM booking_profile WHERE psych_id = ?", (psych_id,))
        row = await cur.fetchone()
    display_name = row[0] if row else "Specialist"

    # Tell client: awaiting psychologist confirmation
    try:
        await callback.message.edit_text(
            t(lang, "booking_pending_client", datetime=display, name=display_name),
            parse_mode="Markdown")
    except Exception:
        await callback.message.answer(
            t(lang, "booking_pending_client", datetime=display, name=display_name),
            parse_mode="Markdown")

    # Notify psychologist with Confirm / Reject buttons
    p_lang = await get_user_lang(psych_id)
    p_tz, _ = await get_user_timezone(psych_id)
    p_display = to_user_tz(utc_str, p_tz, "%d.%m.%Y %H:%M")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=t(p_lang, "btn_booking_approve"),
            callback_data=f"bkc_approve_{session_id}"),
        InlineKeyboardButton(
            text=t(p_lang, "btn_booking_reject"),
            callback_data=f"bkc_reject_{session_id}"),
    ]])
    try:
        await bot.send_message(
            psych_id,
            t(p_lang, "booking_psych_new_request",
              client=client_name, datetime=p_display),
            parse_mode="Markdown",
            reply_markup=kb)
    except Exception as e:
        log.warning("BOOKING: psych notify failed psych_id=%d: %s", psych_id, e)

    log.info("BOOKING: pending_psych session_id=%d psych_id=%d client=%s utc=%s",
             session_id, psych_id, client_name, utc_str)


# ── bkc_approve_{session_id} — psychologist confirms booking request ────────

@router.callback_query(F.data.regexp(r"^bkc_approve_\d+$"))
async def bkc_approve_cb(callback: CallbackQuery, bot: Bot):
    """Psychologist confirms a pending_psych booking request."""
    session_id = int(callback.data.split("_")[2])
    psych_id = callback.from_user.id
    p_lang = await get_user_lang(psych_id)
    await callback.answer()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at, booking_status FROM sessions "
            "WHERE id = ? AND psychologist_id = ?",
            (session_id, psych_id))
        row = await cur.fetchone()
        if not row or row[2] != "pending_psych":
            # Already handled (double tap or wrong session)
            return
        client_name, utc_str, _ = row
        cur = await db.execute(
            "SELECT telegram_id, timezone FROM clients "
            "WHERE psychologist_id = ? AND name = ?",
            (psych_id, client_name))
        client_row = await cur.fetchone()
        await db.execute(
            "UPDATE sessions SET booking_status = 'confirmed' WHERE id = ?",
            (session_id,))
        await db.commit()

    # Update psych's notification message (remove buttons)
    p_tz, _ = await get_user_timezone(psych_id)
    p_display = to_user_tz(utc_str, p_tz, "%d.%m.%Y %H:%M")
    try:
        await callback.message.edit_text(
            t(p_lang, "booking_psych_approved_notify",
              client=client_name, datetime=p_display),
            reply_markup=None)
    except Exception:
        pass

    # Notify client
    if client_row and client_row[0]:
        client_tg, client_tz = client_row
        c_lang = await get_client_lang(client_tg)
        c_display = to_user_tz(utc_str, client_tz, "%d.%m.%Y %H:%M")
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT display_name FROM booking_profile WHERE psych_id = ?", (psych_id,))
            bp_row = await cur.fetchone()
        display_name = bp_row[0] if bp_row else "Specialist"
        try:
            await bot.send_message(
                client_tg,
                t(c_lang, "booking_approved_client",
                  datetime=c_display, name=display_name),
                parse_mode="Markdown")
        except Exception as e:
            log.warning("BOOKING: approve client notify failed: %s", e)

    log.info("BOOKING: approved session_id=%d psych_id=%d", session_id, psych_id)


# ── bkc_reject_{session_id} — psychologist rejects booking request ──────────

@router.callback_query(F.data.regexp(r"^bkc_reject_\d+$"))
async def bkc_reject_cb(callback: CallbackQuery, bot: Bot):
    """Psychologist rejects a pending_psych booking request. Slot is freed."""
    session_id = int(callback.data.split("_")[2])
    psych_id = callback.from_user.id
    await callback.answer()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT client_name, scheduled_at, booking_status FROM sessions "
            "WHERE id = ? AND psychologist_id = ?",
            (session_id, psych_id))
        row = await cur.fetchone()
        if not row or row[2] != "pending_psych":
            return
        client_name, _, _ = row
        cur = await db.execute(
            "SELECT telegram_id, utc_offset FROM clients "
            "WHERE psychologist_id = ? AND name = ?",
            (psych_id, client_name))
        client_row = await cur.fetchone()
        # Delete rejected request — slot is freed for other clients
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()

    # Remove buttons from psych's notification message (keeps request text visible)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Notify client with "choose another time" button
    if client_row and client_row[0]:
        client_tg, client_offset = client_row
        c_lang = await get_client_lang(client_tg)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=t(c_lang, "btn_booking_try_again"),
                callback_data=f"bkc_back_dates_{psych_id}_{client_offset}")
        ]])
        try:
            await bot.send_message(
                client_tg,
                t(c_lang, "booking_declined_client"),
                reply_markup=kb)
        except Exception as e:
            log.warning("BOOKING: reject client notify failed: %s", e)

    log.info("BOOKING: rejected session_id=%d psych_id=%d", session_id, psych_id)
