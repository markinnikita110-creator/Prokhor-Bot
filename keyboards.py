"""All keyboard builders for the Prokhor bot."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from translations import TEXTS, t

PAGE_SIZE = 8

# ── Common timezone presets (offset_minutes, display_label) ───────────────
COMMON_TZ_OFFSETS: list[tuple[int, str]] = [
    (-600, "UTC−10"), (-540, "UTC−9"), (-480, "UTC−8"), (-420, "UTC−7"),
    (-360, "UTC−6"),  (-300, "UTC−5"), (-240, "UTC−4"), (-180, "UTC−3"),
    (-120, "UTC−2"),  (-60,  "UTC−1"), (0,    "UTC"),   (60,   "UTC+1"),
    (120,  "UTC+2"),  (180,  "UTC+3"), (240,  "UTC+4"), (300,  "UTC+5"),
    (330,  "UTC+5:30"),(360, "UTC+6"), (420,  "UTC+7"), (480,  "UTC+8"),
    (540,  "UTC+9"),  (600,  "UTC+10"),(660,  "UTC+11"),(720,  "UTC+12"),
]


# ── Language-agnostic sets for menu button text filters ────────────────────

def _all(key: str) -> frozenset:
    return frozenset(d[key] for d in TEXTS.values() if key in d)


# MENU: top-level main menu buttons
MENU_INDIVIDUAL   = _all("btn_menu_individual")
MENU_COHORTS_BTN  = _all("btn_menu_cohorts")
MENU_SUMMARY      = _all("btn_menu_summary")
MENU_SETTINGS_BTN = _all("btn_menu_settings")
MENU_BACK         = _all("btn_menu_back")

# MENU: Individual submenu buttons
MENU_IND_ADD_CLIENT  = _all("btn_ind_add_client")
MENU_IND_CLIENT_LIST = _all("btn_ind_client_list")
MENU_IND_NEW_NOTE    = _all("btn_ind_new_note")
MENU_IND_SCHEDULE    = _all("btn_ind_schedule")
MENU_IND_REMINDERS   = _all("btn_ind_reminders")

# MENU: Cohorts submenu buttons
MENU_COH_CREATE = _all("btn_coh_create")
MENU_COH_LIST   = _all("btn_coh_list")

# MENU: Summary submenu buttons
MENU_SUM_CLIENTS = _all("btn_sum_clients")
MENU_SUM_COHORTS = _all("btn_sum_cohorts")
MENU_SUM_STATS   = _all("btn_sum_stats")

# MENU: Settings submenu buttons
MENU_SET_LANGUAGE = _all("btn_set_language")
MENU_SET_TIMEZONE = _all("btn_set_timezone")
MENU_SET_NOTIFS   = _all("btn_set_notifs")

# Legacy button sets (still used by inline "Back" callbacks in other handlers)
MENU_CLIENTS   = _all("btn_clients")
MENU_SESSIONS  = _all("btn_sessions")
MENU_HOMEWORK  = _all("btn_homework")
MENU_ANALYTICS = _all("btn_analytics")
MENU_CHECKINS  = _all("btn_checkins")
MENU_SETTINGS  = _all("btn_settings")


# ── MENU: Hierarchical reply keyboards ────────────────────────────────────

def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # MENU: 4-button top-level menu
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_menu_individual")),
             KeyboardButton(text=t(lang, "btn_menu_cohorts"))],
            [KeyboardButton(text=t(lang, "btn_menu_summary")),
             KeyboardButton(text=t(lang, "btn_menu_settings"))],
        ],
        resize_keyboard=True,
    )


def individual_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # MENU: Individual clients submenu
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_ind_add_client")),
             KeyboardButton(text=t(lang, "btn_ind_client_list"))],
            [KeyboardButton(text=t(lang, "btn_ind_new_note")),
             KeyboardButton(text=t(lang, "btn_ind_reminders"))],
            [KeyboardButton(text=t(lang, "btn_menu_back"))],
        ],
        resize_keyboard=True,
    )


def cohorts_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # MENU: Cohorts submenu
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_coh_create")),
             KeyboardButton(text=t(lang, "btn_coh_list"))],
            [KeyboardButton(text=t(lang, "btn_menu_back"))],
        ],
        resize_keyboard=True,
    )


def summary_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # MENU: Summary submenu
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_sum_clients")),
             KeyboardButton(text=t(lang, "btn_sum_cohorts"))],
            [KeyboardButton(text=t(lang, "btn_sum_stats")),
             KeyboardButton(text=t(lang, "btn_menu_back"))],
        ],
        resize_keyboard=True,
    )


def settings_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # MENU: Settings submenu
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_set_language")),
             KeyboardButton(text=t(lang, "btn_set_timezone"))],
            [KeyboardButton(text=t(lang, "btn_set_notifs")),
             KeyboardButton(text=t(lang, "btn_menu_back"))],
        ],
        resize_keyboard=True,
    )


# ── Navigation row (reused inside inline keyboards) ────────────────────────

def _nav_row(back_cb: str, lang: str) -> list:
    return [
        InlineKeyboardButton(text=t(lang, "btn_back"),      callback_data=back_cb),
        InlineKeyboardButton(text=t(lang, "btn_main_menu"), callback_data="m_home"),
    ]


# ── Timezone selection ─────────────────────────────────────────────────────

def timezone_keyboard(lang: str, show_skip: bool = False) -> InlineKeyboardMarkup:
    """Preset timezone buttons (3 per row) + optional custom/skip buttons."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for offset_min, label in COMMON_TZ_OFFSETS:
        row.append(InlineKeyboardButton(
            text=label, callback_data=f"tz_set_{offset_min}"
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(
        text=t(lang, "btn_tz_custom"), callback_data="tz_custom"
    )])
    if show_skip:
        rows.append([InlineKeyboardButton(
            text=t(lang, "btn_skip"), callback_data="tz_skip"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Language selection ─────────────────────────────────────────────────────

def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
    ]])


# ── Clients section ────────────────────────────────────────────────────────

def clients_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_add_client"),      callback_data="c_add")],
        [InlineKeyboardButton(text=t(lang, "btn_client_list"),     callback_data="cl_0")],
        [InlineKeyboardButton(text=t(lang, "btn_invite_client"),   callback_data="c_invite_pick")],
        [InlineKeyboardButton(text=t(lang, "btn_archived_clients"),callback_data="arc_0")],
        [InlineKeyboardButton(text=t(lang, "btn_main_menu"),       callback_data="m_home")],
    ])


def client_list_keyboard(clients: list, page: int, lang: str) -> InlineKeyboardMarkup:
    """clients: list of (id, name) tuples."""
    total_pages = max(1, (len(clients) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_clients = clients[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    rows = [[InlineKeyboardButton(text=name, callback_data=f"cc_{cid}")]
            for cid, name in page_clients]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"cl_{page-1}"))
    nav.append(InlineKeyboardButton(
        text=t(lang, "page_indicator", page=page+1, total=total_pages),
        callback_data="noop"))
    if (page + 1) * PAGE_SIZE < len(clients):
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"cl_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append(_nav_row("m_clients", lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def client_card_keyboard(client_id: int, is_archived: bool, lang: str) -> InlineKeyboardMarkup:
    arch_cb   = f"ca_{client_id}_unarc" if is_archived else f"ca_{client_id}_arch"
    arch_text = t(lang, "btn_unarchive") if is_archived else t(lang, "btn_archive")
    rows = [
        [InlineKeyboardButton(text=t(lang, "btn_add_note"),    callback_data=f"ca_{client_id}_note"),
         InlineKeyboardButton(text=t(lang, "btn_soap_note"),   callback_data=f"ca_{client_id}_soap")],
        [InlineKeyboardButton(text=t(lang, "btn_assign_hw"),   callback_data=f"ca_{client_id}_hw"),
         InlineKeyboardButton(text=t(lang, "btn_send_ci"),     callback_data=f"ca_{client_id}_ci")],
        [InlineKeyboardButton(text=t(lang, "btn_client_sessions"), callback_data=f"ics_{client_id}"),
         InlineKeyboardButton(text=t(lang, "btn_timeline"),        callback_data=f"ca_{client_id}_tl")],
        [InlineKeyboardButton(text=t(lang, "btn_tags"),        callback_data=f"ca_{client_id}_tag"),
         InlineKeyboardButton(text=t(lang, "btn_engagement"),  callback_data=f"ca_{client_id}_eng")],
        [InlineKeyboardButton(text=t(lang, "btn_export"),      callback_data=f"ca_{client_id}_exp"),
         InlineKeyboardButton(text=arch_text,                  callback_data=arch_cb)],
        [InlineKeyboardButton(text=t(lang, "btn_invite_link"), callback_data=f"ca_{client_id}_inv")],
        _nav_row("cl_0", lang),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def archived_list_keyboard(clients: list, page: int, lang: str) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(clients) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_clients = clients[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    rows = [[InlineKeyboardButton(text=name, callback_data=f"ac_{cid}")]
            for cid, name in page_clients]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"arc_{page-1}"))
    nav.append(InlineKeyboardButton(
        text=t(lang, "page_indicator", page=page+1, total=total_pages),
        callback_data="noop"))
    if (page + 1) * PAGE_SIZE < len(clients):
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"arc_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append(_nav_row("m_clients", lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Sessions section ───────────────────────────────────────────────────────

def sessions_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_schedule_session"),  callback_data="s_add")],
        [InlineKeyboardButton(text=t(lang, "btn_upcoming_sessions"), callback_data="sl_0")],
        [InlineKeyboardButton(text=t(lang, "btn_main_menu"),         callback_data="m_home")],
    ])


def session_list_keyboard(sessions: list, page: int, lang: str) -> InlineKeyboardMarkup:
    """sessions: list of (id, client_name, scheduled_at)."""
    total_pages = max(1, (len(sessions) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_sessions = sessions[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    rows = [[InlineKeyboardButton(
                text=f"{name} · {date}",
                callback_data=f"sc_{sid}"
             )] for sid, name, date in page_sessions]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=t(lang, "btn_prev"), callback_data=f"sl_{page-1}"))
    nav.append(InlineKeyboardButton(
        text=t(lang, "page_indicator", page=page+1, total=total_pages),
        callback_data="noop"))
    if (page + 1) * PAGE_SIZE < len(sessions):
        nav.append(InlineKeyboardButton(text=t(lang, "btn_next"), callback_data=f"sl_{page+1}"))
    if nav:
        rows.append(nav)

    rows.append(_nav_row("m_sessions", lang))
    return InlineKeyboardMarkup(inline_keyboard=rows)


def session_card_keyboard(session_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_reschedule"),     callback_data=f"sa_{session_id}_rsc"),
         InlineKeyboardButton(text=t(lang, "btn_cancel_session"), callback_data=f"sa_{session_id}_can")],
        _nav_row("sl_0", lang),
    ])


# ── Homework section ───────────────────────────────────────────────────────

def homework_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_assign_homework"), callback_data="hw_add")],
        [InlineKeyboardButton(text=t(lang, "btn_active_homework"), callback_data="hw_list")],
        [InlineKeyboardButton(text=t(lang, "btn_main_menu"),       callback_data="m_home")],
    ])


# ── Analytics section ──────────────────────────────────────────────────────

def analytics_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_dashboard"), callback_data="an_dash")],
        [InlineKeyboardButton(text=t(lang, "btn_alerts"),    callback_data="an_alerts")],
        [InlineKeyboardButton(text=t(lang, "btn_main_menu"), callback_data="m_home")],
    ])


# ── Check-ins section ──────────────────────────────────────────────────────

def checkins_section_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_send_checkin"),    callback_data="ci_send")],
        [InlineKeyboardButton(text=t(lang, "btn_auto_checkins"),   callback_data="ci_auto")],
        [InlineKeyboardButton(text=t(lang, "btn_recent_checkins"), callback_data="ci_recent")],
        [InlineKeyboardButton(text=t(lang, "btn_main_menu"),       callback_data="m_home")],
    ])


def checkin_score_keyboard(client_id: int) -> InlineKeyboardMarkup:
    labels = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    row1 = [InlineKeyboardButton(text=labels[i], callback_data=f"checkin_{client_id}_{i+1}") for i in range(5)]
    row2 = [InlineKeyboardButton(text=labels[i], callback_data=f"checkin_{client_id}_{i+1}") for i in range(5, 10)]
    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


# ── Settings section ───────────────────────────────────────────────────────

def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    tariff_label = "💰 Тариф" if lang == "ru" else "💰 My Plan"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_language"), callback_data="st_lang")],
        [InlineKeyboardButton(text=t(lang, "btn_timezone"), callback_data="st_tz")],
        [InlineKeyboardButton(text=tariff_label,            callback_data="st_tariff")],
        [InlineKeyboardButton(text=t(lang, "btn_about"),    callback_data="st_about")],
        [InlineKeyboardButton(text=t(lang, "btn_main_menu"),callback_data="m_home")],
    ])


def tariff_keyboard(lang: str, is_pro: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if not is_pro:
        buttons.append([InlineKeyboardButton(
            text=t(lang, "btn_tariff_upgrade"),
            callback_data="st_tariff_upgrade",
        )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "btn_tariff_compare"),
        callback_data="st_tariff_compare",
    )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "btn_tariff_history"),
        callback_data="st_tariff_history",
    )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "btn_tariff_howto"),
        callback_data="st_tariff_howto",
    )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "btn_tariff_back"),
        callback_data="m_settings",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Role selection (dual-role users) ──────────────────────────────────────

def role_select_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_role_psychologist"),
                              callback_data="role_psych")],
        [InlineKeyboardButton(text=t(lang, "btn_role_client"),
                              callback_data="role_client")],
    ])


# ── COHORT: type selection ─────────────────────────────────────────────────

def cohort_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_cohort_type_course"),
                              callback_data="cohort_type_course")],
        [InlineKeyboardButton(text=t(lang, "btn_cohort_type_group"),
                              callback_data="cohort_type_group")],
        [InlineKeyboardButton(text=t(lang, "btn_cohort_type_supervision"),
                              callback_data="cohort_type_supervision")],
    ])


# ── COHORT_V2: Members screen keyboard ────────────────────────────────────

def cohort_members_keyboard(cohort_id: int, lang: str) -> InlineKeyboardMarkup:
    """COHORT_V2: Action buttons shown below the members list."""
    cid = cohort_id
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cv2_btn_add_member"), callback_data=f"cv2_addmem_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_btn_invite"),     callback_data=f"cv2_invite_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_back"),           callback_data=f"cv2_pick_{cid}")],
    ])


# ── COHORT_V2: Cohort action keyboard (inline — shown after cohort pick) ──

def cohort_action_keyboard(cohort_id: int, lang: str) -> InlineKeyboardMarkup:
    """COHORT_V2: Full action menu for a specific cohort."""
    cid = cohort_id
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cv2_members"),    callback_data=f"cv2_mem_{cid}"),
         InlineKeyboardButton(text=t(lang, "cv2_sessions"),   callback_data=f"cv2_slist_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_attendance"), callback_data=f"cv2_att_{cid}"),
         InlineKeyboardButton(text=t(lang, "cv2_checkins"),   callback_data=f"cv2_ci_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_notes"),      callback_data=f"cv2_notes_{cid}"),
         InlineKeyboardButton(text=t(lang, "cv2_broadcast"),  callback_data=f"cv2_bc_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_stats"),      callback_data=f"cv2_stats_{cid}"),
         InlineKeyboardButton(text=t(lang, "cv2_archive"),    callback_data=f"cv2_arch_{cid}")],
        [InlineKeyboardButton(text=t(lang, "cv2_back"),       callback_data="cv2_coh_list")],
    ])


# ── RECURRING: weekday multi-select keyboard for recurring session setup ──

_DOW_KEYS = ["dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"]


def cohort_recurring_days_keyboard(selected, lang: str) -> InlineKeyboardMarkup:
    """RECURRING: toggle keyboard for picking weekdays (0=Mon..6=Sun)."""
    rows = []
    row = []
    for i, key in enumerate(_DOW_KEYS):
        mark = "✅ " if i in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{t(lang, key)}", callback_data=f"crday_{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang, "cs_recurring_days_done"), callback_data="crday_done")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── SESSIONS: browsable session list + detail/action view for a cohort ────

def cohort_session_list_keyboard(session_rows, cohort_id, lang: str) -> InlineKeyboardMarkup:
    """SESSIONS: one button per session (opens the detail/action view),
    plus shortcuts to add a one-off session or set up a recurring one."""
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"csd_{sid}")]
        for sid, label in session_rows
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "cs2_btn_add_oneoff"),
                                       callback_data=f"cv2_sched_{cohort_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "cs2_btn_add_recurring"),
                                       callback_data=f"cv2_rsched_{cohort_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "cv2_back"), callback_data=f"cv2_pick_{cohort_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cohort_session_detail_keyboard(session_id, cohort_id, recurring: bool, paused: bool,
                                    lang: str) -> InlineKeyboardMarkup:
    """SESSIONS: edit/delete actions for one session, plus recurrence
    pause/resume + delete-rule actions when the session is part of a schedule."""
    rows = [
        [InlineKeyboardButton(text=t(lang, "cs2_btn_edit_dt"), callback_data=f"csdt_{session_id}"),
         InlineKeyboardButton(text=t(lang, "cs2_btn_edit_topic"), callback_data=f"cstp_{session_id}")],
        [InlineKeyboardButton(text=t(lang, "cs2_btn_edit_link"), callback_data=f"cslk_{session_id}"),
         InlineKeyboardButton(text=t(lang, "cs2_btn_delete"), callback_data=f"csdl_{session_id}")],
    ]
    if recurring:
        pause_label = t(lang, "cs2_btn_resume") if paused else t(lang, "cs2_btn_pause")
        rows.append([InlineKeyboardButton(text=pause_label, callback_data=f"cspz_{session_id}")])
        rows.append([InlineKeyboardButton(text=t(lang, "cs2_btn_delete_rule"),
                                           callback_data=f"csrl_{session_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "cs2_btn_back_list"),
                                       callback_data=f"cv2_slist_{cohort_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cohort_confirm_keyboard(yes_key: str, no_key: str, yes_cb: str, no_cb: str,
                             lang: str) -> InlineKeyboardMarkup:
    """SESSIONS: generic yes/no confirmation row for destructive actions."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, yes_key), callback_data=yes_cb),
        InlineKeyboardButton(text=t(lang, no_key), callback_data=no_cb),
    ]])


def cohort_clear_field_keyboard(clear_cb: str, lang: str) -> InlineKeyboardMarkup:
    """SESSIONS: while editing topic/link, offer a Clear button plus cancel."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "cs2_btn_clear"), callback_data=clear_cb)],
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")],
    ])


# ── INDIVIDUAL_SESSION: keyboards ────────────────────────────────────────

def client_session_list_keyboard(session_rows, client_id: int,
                                 has_recurring: bool, lang: str) -> InlineKeyboardMarkup:
    """INDIVIDUAL_SESSION: one button per upcoming session + add actions + back."""
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"isd_{sid}")]
        for label, sid in session_rows
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "is_btn_add_oneoff"),
                                       callback_data=f"isoa_{client_id}")])
    if not has_recurring:
        rows.append([InlineKeyboardButton(text=t(lang, "is_btn_add_recurring"),
                                           callback_data=f"isra_{client_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"),
                                       callback_data=f"cc_{client_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def client_session_detail_keyboard(session_id: int, client_id: int,
                                    recurring: bool, paused: bool,
                                    lang: str) -> InlineKeyboardMarkup:
    """INDIVIDUAL_SESSION: edit/delete actions for one session + recurrence controls."""
    rows = [
        [InlineKeyboardButton(text=t(lang, "is_btn_edit_dt"),    callback_data=f"isdt_{session_id}"),
         InlineKeyboardButton(text=t(lang, "is_btn_edit_topic"), callback_data=f"istp_{session_id}")],
        [InlineKeyboardButton(text=t(lang, "is_btn_edit_link"),  callback_data=f"islk_{session_id}"),
         InlineKeyboardButton(text=t(lang, "is_btn_delete"),     callback_data=f"isdl_{session_id}")],
    ]
    if recurring:
        pause_label = t(lang, "is_btn_resume") if paused else t(lang, "is_btn_pause")
        rows.append([InlineKeyboardButton(text=pause_label, callback_data=f"ispz_{session_id}")])
        rows.append([InlineKeyboardButton(text=t(lang, "is_btn_delete_rule"),
                                           callback_data=f"isrl_{session_id}")])
    rows.append([InlineKeyboardButton(text=t(lang, "is_btn_back_list"),
                                       callback_data=f"ics_{client_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def client_ind_recurring_days_keyboard(selected, lang: str) -> InlineKeyboardMarkup:
    """INDIVIDUAL_SESSION: weekday toggle picker for recurring session setup."""
    rows = []
    row = []
    for i, key in enumerate(_DOW_KEYS):
        mark = "✅ " if i in selected else ""
        row.append(InlineKeyboardButton(text=f"{mark}{t(lang, key)}", callback_data=f"isrd_{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t(lang, "cs_recurring_days_done"), callback_data="isrd_done")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── FSM cancel ────────────────────────────────────────────────────────────

def cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="fsm_cancel"),
    ]])
