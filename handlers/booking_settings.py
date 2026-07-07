"""BOOKING: psychologist-side booking profile setup and management."""

import logging
import re
from datetime import datetime

import aiosqlite
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from database import DB_PATH, get_user_lang, now_str
from states.booking_states import (
    BookingEditForm, BookingExceptionForm, BookingScheduleForm, BookingSetupForm,
)
from translations import t

router = Router()
log = logging.getLogger(__name__)

# weekday index → translation key
_DOW_KEYS = ["dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"]

BOT_USERNAME = ""


def set_bot_username_booking(username: str):
    global BOT_USERNAME
    BOT_USERNAME = username


# ── Slug helpers ────────────────────────────────────────────────────────────

_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z',
    'и':'i','й':'i','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh',
    'щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}


def _make_slug(display_name: str) -> str:
    s = display_name.lower()
    s = ''.join(_TRANSLIT.get(c, c) for c in s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')[:40] or 'psych'
    return s


async def _unique_slug(db, base_slug: str, exclude_psych_id: int | None = None) -> str:
    slug = base_slug
    suffix = 1
    while True:
        cur = await db.execute(
            "SELECT psych_id FROM booking_profile WHERE slug = ?", (slug,))
        row = await cur.fetchone()
        if not row or (exclude_psych_id and row[0] == exclude_psych_id):
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


# ── Profile card helpers ─────────────────────────────────────────────────────

async def _get_profile(psych_id: int):
    """Return (slug, display_name, bio, timezone, booking_enabled).

    timezone is always read from psychologists — the single source of truth.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT bp.slug, bp.display_name, bp.bio, "
            "       COALESCE(p.timezone, 'UTC'), bp.booking_enabled "
            "FROM booking_profile bp "
            "LEFT JOIN psychologists p ON p.user_id = bp.psych_id "
            "WHERE bp.psych_id = ?", (psych_id,))
        return await cur.fetchone()


def _profile_keyboard(psych_id: int, booking_enabled: int, lang: str) -> InlineKeyboardMarkup:
    toggle_key = "btn_booking_toggle_off" if booking_enabled else "btn_booking_toggle_on"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_booking_schedule"),
                              callback_data=f"bk_schedule_{psych_id}"),
         InlineKeyboardButton(text=t(lang, "btn_booking_exceptions"),
                              callback_data=f"bk_exceptions_{psych_id}")],
        [InlineKeyboardButton(text=t(lang, toggle_key),
                              callback_data=f"bk_toggle_{psych_id}"),
         InlineKeyboardButton(text=t(lang, "btn_booking_link"),
                              callback_data=f"bk_link_{psych_id}")],
        [InlineKeyboardButton(text=t(lang, "btn_booking_edit_name"),
                              callback_data=f"bk_edit_name_{psych_id}"),
         InlineKeyboardButton(text=t(lang, "btn_booking_edit_bio"),
                              callback_data=f"bk_edit_bio_{psych_id}")],
    ])


async def _send_profile_card(target, psych_id: int, lang: str, edit: bool = False):
    profile = await _get_profile(psych_id)
    if not profile:
        await target.answer(t(lang, "booking_no_profile"))
        return
    slug, display_name, bio, timezone, booking_enabled = profile
    link = f"https://t.me/{BOT_USERNAME}?start=book_{slug}"
    status_key = "booking_enabled_on" if booking_enabled else "booking_enabled_off"
    text = t(lang, "booking_profile_card",
             display_name=display_name or "—",
             bio=bio or "—",
             slug=slug,
             timezone=timezone,
             status=t(lang, status_key),
             link=link)
    kb = _profile_keyboard(psych_id, booking_enabled, lang)
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb, parse_mode="Markdown")
            return
        except Exception:
            pass
    await target.answer(text, reply_markup=kb, parse_mode="Markdown")


def _schedule_keyboard(rules_by_day: dict, psych_id: int, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for wd in range(7):
        day_name = t(lang, _DOW_KEYS[wd])
        if wd in rules_by_day:
            r = rules_by_day[wd]
            label = t(lang, "booking_day_configured",
                      day=day_name, start=r["start_time"], end=r["end_time"],
                      duration=r["session_duration_min"], buffer=r["buffer_min"])
        else:
            label = t(lang, "booking_day_none", day=day_name)
        rows.append([InlineKeyboardButton(
            text=label, callback_data=f"bk_day_{psych_id}_{wd}")])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data=f"bk_profile_{psych_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _day_action_keyboard(psych_id: int, weekday: int, has_rule: bool, lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        text=t(lang, "ask_booking_day_start", day=t(lang, _DOW_KEYS[weekday])),
        callback_data=f"bk_editday_{psych_id}_{weekday}")]]
    if has_rule:
        rows.append([InlineKeyboardButton(
            text=t(lang, "btn_booking_remove_day"),
            callback_data=f"bk_delday_{psych_id}_{weekday}")])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data=f"bk_schedule_{psych_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _exceptions_keyboard(exceptions: list, psych_id: int, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for ex_id, date, start_time, end_time in exceptions:
        if start_time:
            time_range = f"{start_time}–{end_time or '?'}"
        else:
            time_range = t(lang, "booking_exception_whole_day")
        label = t(lang, "booking_exception_row", date=date, time_range=time_range)
        rows.append([
            InlineKeyboardButton(text=label, callback_data="noop"),
            InlineKeyboardButton(text=t(lang, "btn_booking_del_ex"),
                                 callback_data=f"bk_delex_{psych_id}_{ex_id}"),
        ])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_booking_add_exception"),
        callback_data=f"bk_addex_{psych_id}")])
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_back"), callback_data=f"bk_profile_{psych_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _whole_day_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_booking_whole_day"),
                              callback_data="bk_ex_wholeday")],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])


# ── Entry point: st_booking callback and MENU_SET_BOOKING text ─────────────

@router.callback_query(F.data == "st_booking")
async def booking_settings_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await _booking_settings_screen(callback.message, callback.from_user.id, lang, edit=True)


async def _booking_settings_screen(message, psych_id: int, lang: str, edit: bool = False):
    from core.services.plans import get_user_plan
    plan = await get_user_plan(psych_id)
    if not plan.get("self_booking"):
        text = t(lang, "booking_pro_only")
        if edit:
            try:
                await message.edit_text(text)
                return
            except Exception:
                pass
        await message.answer(text)
        return

    profile = await _get_profile(psych_id)
    if not profile:
        text = t(lang, "booking_no_profile")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_booking_setup"),
                                  callback_data=f"bk_setup_{psych_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_main_menu"), callback_data="m_home")],
        ])
        if edit:
            try:
                await message.edit_text(text, reply_markup=kb)
                return
            except Exception:
                pass
        await message.answer(text, reply_markup=kb)
    else:
        await _send_profile_card(message, psych_id, lang, edit=edit)


# ── Setup FSM ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_setup_\d+$"))
async def bk_setup_start(callback: CallbackQuery, state: FSMContext):
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(psych_id=psych_id, lang=lang)
    await state.set_state(BookingSetupForm.display_name)
    await callback.message.answer(t(lang, "ask_booking_display_name"),
                                  reply_markup=cancel_keyboard(lang))


@router.message(BookingSetupForm.display_name)
async def bk_setup_got_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    await state.update_data(display_name=message.text.strip())
    await state.set_state(BookingSetupForm.bio)
    await message.answer(t(lang, "ask_booking_bio"), reply_markup=cancel_keyboard(lang))


@router.message(BookingSetupForm.bio)
async def bk_setup_got_bio(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    bio = message.text.strip()
    if len(bio) > 300:
        await message.answer(t(lang, "booking_bio_too_long", length=len(bio)),
                             reply_markup=cancel_keyboard(lang))
        return
    await state.update_data(bio=bio)
    data = await state.get_data()
    await _finish_setup(message, state, data, lang)


async def _finish_setup(target, state: FSMContext, data: dict, lang: str):
    """Finalise booking profile creation.

    Reads timezone from psychologists table (single source of truth) so the
    booking profile never stores a diverging copy.
    """
    psych_id = data["psych_id"]
    display_name = data["display_name"]
    bio = data["bio"]
    base_slug = _make_slug(display_name)
    async with aiosqlite.connect(DB_PATH) as db:
        # Read the psychologist's already-validated timezone
        cur = await db.execute(
            "SELECT timezone FROM psychologists WHERE user_id = ?", (psych_id,))
        tz_row = await cur.fetchone()
        tz_name = tz_row[0] if tz_row and tz_row[0] else "UTC"
        slug = await _unique_slug(db, base_slug, exclude_psych_id=psych_id)
        await db.execute(
            "INSERT OR REPLACE INTO booking_profile "
            "(psych_id, slug, display_name, bio, timezone, booking_enabled, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (psych_id, slug, display_name, bio, tz_name, now_str()))
        await db.commit()
    await state.clear()
    msg = t(lang, "booking_profile_saved")
    try:
        await target.answer(msg)
    except Exception:
        await target.message.answer(msg)
    log.info("BOOKING: profile created psych_id=%d slug=%s tz=%s", psych_id, slug, tz_name)


# ── Profile card callback ──────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_profile_\d+$"))
async def bk_profile_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await _send_profile_card(callback.message, psych_id, lang, edit=True)


# ── Toggle booking_enabled ─────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_toggle_\d+$"))
async def bk_toggle_cb(callback: CallbackQuery):
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT booking_enabled FROM booking_profile WHERE psych_id = ?", (psych_id,))
        row = await cur.fetchone()
        if not row:
            return
        new_val = 0 if row[0] else 1
        await db.execute(
            "UPDATE booking_profile SET booking_enabled = ? WHERE psych_id = ?",
            (new_val, psych_id))
        await db.commit()
    key = "booking_toggled_on" if new_val else "booking_toggled_off"
    await callback.message.answer(t(lang, key))
    await _send_profile_card(callback.message, psych_id, lang)
    log.info("BOOKING: toggle psych_id=%d enabled=%d", psych_id, new_val)


# ── Booking link ───────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_link_\d+$"))
async def bk_link_cb(callback: CallbackQuery):
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    profile = await _get_profile(psych_id)
    if not profile:
        return
    slug = profile[0]
    link = f"https://t.me/{BOT_USERNAME}?start=book_{slug}"
    await callback.message.answer(t(lang, "booking_link_msg", link=link),
                                  parse_mode="Markdown")


# ── Edit display_name ──────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_edit_name_\d+$"))
async def bk_edit_name_cb(callback: CallbackQuery, state: FSMContext):
    psych_id = int(callback.data.split("_")[3])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(psych_id=psych_id, lang=lang)
    await state.set_state(BookingEditForm.display_name)
    await callback.message.answer(t(lang, "ask_booking_display_name"),
                                  reply_markup=cancel_keyboard(lang))


@router.message(BookingEditForm.display_name)
async def bk_edit_name_got(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    psych_id = data["psych_id"]
    display_name = message.text.strip()
    base_slug = _make_slug(display_name)
    async with aiosqlite.connect(DB_PATH) as db:
        slug = await _unique_slug(db, base_slug, exclude_psych_id=psych_id)
        await db.execute(
            "UPDATE booking_profile SET display_name = ?, slug = ? WHERE psych_id = ?",
            (display_name, slug, psych_id))
        await db.commit()
    await state.clear()
    await _send_profile_card(message, psych_id, lang)


# ── Edit bio ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_edit_bio_\d+$"))
async def bk_edit_bio_cb(callback: CallbackQuery, state: FSMContext):
    psych_id = int(callback.data.split("_")[3])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(psych_id=psych_id, lang=lang)
    await state.set_state(BookingEditForm.bio)
    await callback.message.answer(t(lang, "ask_booking_bio"), reply_markup=cancel_keyboard(lang))


@router.message(BookingEditForm.bio)
async def bk_edit_bio_got(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    psych_id = data["psych_id"]
    bio = message.text.strip()
    if len(bio) > 300:
        await message.answer(t(lang, "booking_bio_too_long", length=len(bio)),
                             reply_markup=cancel_keyboard(lang))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE booking_profile SET bio = ? WHERE psych_id = ?", (bio, psych_id))
        await db.commit()
    await state.clear()
    await _send_profile_card(message, psych_id, lang)


# ── Weekly schedule ────────────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_schedule_\d+$"))
async def bk_schedule_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT weekday, start_time, end_time, session_duration_min, buffer_min "
            "FROM availability_rules WHERE psych_id = ?", (psych_id,))
        rows = await cur.fetchall()
    rules_by_day = {r[0]: {"start_time": r[1], "end_time": r[2],
                            "session_duration_min": r[3], "buffer_min": r[4]}
                    for r in rows}
    text = t(lang, "booking_schedule_title")
    kb = _schedule_keyboard(rules_by_day, psych_id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.regexp(r"^bk_day_\d+_\d$"))
async def bk_day_cb(callback: CallbackQuery):
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    weekday = int(parts[3])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT start_time, end_time, session_duration_min, buffer_min "
            "FROM availability_rules WHERE psych_id = ? AND weekday = ?",
            (psych_id, weekday))
        row = await cur.fetchone()
    has_rule = row is not None
    day_name = t(lang, _DOW_KEYS[weekday])
    if has_rule:
        text = t(lang, "booking_day_configured",
                 day=day_name, start=row[0], end=row[1],
                 duration=row[2], buffer=row[3])
    else:
        text = t(lang, "booking_day_none", day=day_name)
    kb = _day_action_keyboard(psych_id, weekday, has_rule, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.regexp(r"^bk_editday_\d+_\d$"))
async def bk_editday_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    weekday = int(parts[3])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(psych_id=psych_id, weekday=weekday, lang=lang)
    await state.set_state(BookingScheduleForm.start_time)
    day_name = t(lang, _DOW_KEYS[weekday])
    await callback.message.answer(t(lang, "ask_booking_day_start", day=day_name),
                                  reply_markup=cancel_keyboard(lang),
                                  parse_mode="Markdown")


def _parse_hhmm(s: str) -> tuple[int, int] | None:
    m = re.match(r"^(\d{1,2}):(\d{2})$", s.strip())
    if not m:
        return None
    h, mn = int(m.group(1)), int(m.group(2))
    if h > 23 or mn > 59:
        return None
    return h, mn


@router.message(BookingScheduleForm.start_time)
async def bk_sched_got_start(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    parsed = _parse_hhmm(message.text)
    if not parsed:
        await message.answer(t(lang, "booking_invalid_time"),
                             reply_markup=cancel_keyboard(lang))
        return
    await state.update_data(start_time=message.text.strip())
    await state.set_state(BookingScheduleForm.end_time)
    await message.answer(t(lang, "ask_booking_day_end"), reply_markup=cancel_keyboard(lang))


@router.message(BookingScheduleForm.end_time)
async def bk_sched_got_end(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    parsed = _parse_hhmm(message.text)
    if not parsed:
        await message.answer(t(lang, "booking_invalid_time"),
                             reply_markup=cancel_keyboard(lang))
        return
    start_parsed = _parse_hhmm(data["start_time"])
    if parsed <= start_parsed:
        await message.answer(t(lang, "booking_time_order"), reply_markup=cancel_keyboard(lang))
        return
    await state.update_data(end_time=message.text.strip())
    await state.set_state(BookingScheduleForm.duration)
    await message.answer(t(lang, "ask_booking_day_duration"), reply_markup=cancel_keyboard(lang))


@router.message(BookingScheduleForm.duration)
async def bk_sched_got_duration(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    try:
        dur = int(message.text.strip())
        if dur <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "booking_invalid_number"),
                             reply_markup=cancel_keyboard(lang))
        return
    await state.update_data(duration=dur)
    await state.set_state(BookingScheduleForm.buffer)
    await message.answer(t(lang, "ask_booking_day_buffer"), reply_markup=cancel_keyboard(lang))


@router.message(BookingScheduleForm.buffer)
async def bk_sched_got_buffer(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    psych_id = data["psych_id"]
    weekday = data["weekday"]
    try:
        buf = int(message.text.strip())
        if buf < 0:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "booking_invalid_number"),
                             reply_markup=cancel_keyboard(lang))
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM availability_rules WHERE psych_id = ? AND weekday = ?",
            (psych_id, weekday))
        await db.execute(
            "INSERT INTO availability_rules "
            "(psych_id, weekday, start_time, end_time, session_duration_min, buffer_min) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (psych_id, weekday, data["start_time"], data["end_time"], data["duration"], buf))
        await db.commit()
    await state.clear()
    day_name = t(lang, _DOW_KEYS[weekday])
    await message.answer(t(lang, "booking_day_saved", day=day_name))
    log.info("BOOKING: schedule saved psych_id=%d weekday=%d", psych_id, weekday)


@router.callback_query(F.data.regexp(r"^bk_delday_\d+_\d$"))
async def bk_delday_cb(callback: CallbackQuery):
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    weekday = int(parts[3])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM availability_rules WHERE psych_id = ? AND weekday = ?",
            (psych_id, weekday))
        await db.commit()
    day_name = t(lang, _DOW_KEYS[weekday])
    await callback.message.answer(t(lang, "booking_day_removed", day=day_name))
    log.info("BOOKING: rule deleted psych_id=%d weekday=%d", psych_id, weekday)


# ── Blocked date exceptions ────────────────────────────────────────────────

@router.callback_query(F.data.regexp(r"^bk_exceptions_\d+$"))
async def bk_exceptions_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, date, start_time, end_time FROM availability_exceptions "
            "WHERE psych_id = ? ORDER BY date", (psych_id,))
        exceptions = await cur.fetchall()
    if exceptions:
        items = "\n".join(
            t(lang, "booking_exception_row",
              date=row[1],
              time_range=(f"{row[2]}–{row[3] or '?'}" if row[2]
                          else t(lang, "booking_exception_whole_day")))
            for row in exceptions
        )
    else:
        items = t(lang, "booking_no_exceptions")
    text = t(lang, "booking_exceptions_title", items=items)
    kb = _exceptions_keyboard(exceptions, psych_id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.regexp(r"^bk_delex_\d+_\d+$"))
async def bk_delex_cb(callback: CallbackQuery):
    parts = callback.data.split("_")
    psych_id = int(parts[2])
    ex_id = int(parts[3])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM availability_exceptions WHERE id = ? AND psych_id = ?",
                         (ex_id, psych_id))
        await db.commit()
    # Re-show exceptions screen
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, date, start_time, end_time FROM availability_exceptions "
            "WHERE psych_id = ? ORDER BY date", (psych_id,))
        exceptions = await cur.fetchall()
    if exceptions:
        items = "\n".join(
            t(lang, "booking_exception_row",
              date=row[1],
              time_range=(f"{row[2]}–{row[3] or '?'}" if row[2]
                          else t(lang, "booking_exception_whole_day")))
            for row in exceptions
        )
    else:
        items = t(lang, "booking_no_exceptions")
    text = t(lang, "booking_exceptions_title", items=items)
    kb = _exceptions_keyboard(exceptions, psych_id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.regexp(r"^bk_addex_\d+$"))
async def bk_addex_start(callback: CallbackQuery, state: FSMContext):
    psych_id = int(callback.data.split("_")[2])
    lang = await get_user_lang(callback.from_user.id)
    await callback.answer()
    await state.update_data(psych_id=psych_id, lang=lang)
    await state.set_state(BookingExceptionForm.date)
    await callback.message.answer(t(lang, "ask_booking_ex_date"),
                                  reply_markup=cancel_keyboard(lang))


def _parse_date(s: str) -> str | None:
    """Return YYYY-MM-DD or None."""
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


@router.message(BookingExceptionForm.date)
async def bk_ex_got_date(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    date_str = _parse_date(message.text)
    if not date_str:
        await message.answer(t(lang, "booking_invalid_date"),
                             reply_markup=cancel_keyboard(lang))
        return
    await state.update_data(ex_date=date_str)
    await state.set_state(BookingExceptionForm.start_time)
    await message.answer(t(lang, "ask_booking_ex_start"),
                         reply_markup=_whole_day_keyboard(lang))


@router.callback_query(BookingExceptionForm.start_time, F.data == "bk_ex_wholeday")
async def bk_ex_whole_day(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    psych_id = data["psych_id"]
    date_str = data["ex_date"]
    await callback.answer()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO availability_exceptions (psych_id, date, start_time, end_time, type) "
            "VALUES (?, ?, NULL, NULL, 'blocked')", (psych_id, date_str))
        await db.commit()
    await state.clear()
    await callback.message.answer(t(lang, "booking_ex_saved", date=date_str))
    log.info("BOOKING: exception whole day psych_id=%d date=%s", psych_id, date_str)


@router.message(BookingExceptionForm.start_time)
async def bk_ex_got_start(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    parsed = _parse_hhmm(message.text)
    if not parsed:
        await message.answer(t(lang, "booking_invalid_time"),
                             reply_markup=_whole_day_keyboard(lang))
        return
    await state.update_data(ex_start=message.text.strip())
    await state.set_state(BookingExceptionForm.end_time)
    await message.answer(t(lang, "ask_booking_ex_end"), reply_markup=cancel_keyboard(lang))


@router.message(BookingExceptionForm.end_time)
async def bk_ex_got_end(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "en")
    psych_id = data["psych_id"]
    date_str = data["ex_date"]
    ex_start = data["ex_start"]
    parsed = _parse_hhmm(message.text)
    if not parsed:
        await message.answer(t(lang, "booking_invalid_time"),
                             reply_markup=cancel_keyboard(lang))
        return
    ex_end = message.text.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO availability_exceptions (psych_id, date, start_time, end_time, type) "
            "VALUES (?, ?, ?, ?, 'blocked')", (psych_id, date_str, ex_start, ex_end))
        await db.commit()
    await state.clear()
    await message.answer(t(lang, "booking_ex_saved", date=date_str))
    log.info("BOOKING: exception psych_id=%d date=%s %s–%s", psych_id, date_str, ex_start, ex_end)
