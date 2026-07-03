TEXTS = {
    "en": {
        # ── Psychologist welcome ───────────────────────────────────────────
        "welcome": "👋 Hi! Prokhor is here — your assistant for client management and session notes. Let's get to work!",
        "language_select": "🌍 Choose your preferred language:",
        "language_saved": "✅ Language saved!",

        # ── Client management ─────────────────────────────────────────────
        "client_added": "✅ **{name}** has been added! I'll help you keep their card organised.",
        "client_not_found": "😕 I couldn't find a client named «{name}». Check the spelling?",
        "no_clients": "No clients yet 😊 Shall we add the first one?",
        "clients_title": "👤 Your clients:",
        "clients_status_title": "📋 Client connection status:",
        "connected": "connected ✅",
        "not_connected": "not connected yet",
        "client_archived": "📦 **{name}** moved to archive. You can restore them anytime.",
        "client_already_archived": "**{name}** is already in the archive.",
        "client_unarchived": "♻️ **{name}** is back in your active list!",
        "client_not_archived": "**{name}** isn't in the archive.",
        "archived_title": "📦 Archived clients:",
        "no_archived": "The archive is empty — all clients are active 🎉",

        # ── Notes ─────────────────────────────────────────────────────────
        "note_saved": "📝 Note saved for **{client}**.",
        "notes_title": "📝 Notes for **{client}**:",
        "no_notes": "No notes yet for {client}. Add the first one?",
        "summary_text": "👤 Client: **{client}**\n📝 Notes: {count}",
        "summary_last": "\n🕐 Last updated:\n{last}",
        "soap_saved": "📋 SOAP note saved for **{client}**:\n\n{text}",
        "soap_s": "Starting a SOAP note for **{client}**.\n\n*S — Subjective:* Share what the client said — their own words, mood, and concerns:",
        "soap_o": "*O — Objective:* Your observations — behaviour, body language, test results:",
        "soap_a": "*A — Assessment:* Your clinical impression and working hypothesis:",
        "soap_p": "*P — Plan:* Next steps, homework, or focus for the next session:",

        # ── Check-ins ─────────────────────────────────────────────────────
        "checkin_saved": "💬 Check-in saved for **{client}**: {score}/10",
        "checkins_title": "💬 Check-ins for **{client}**:",
        "no_checkins": "No check-ins yet for {client}. Send the first one?",
        "checkin_request_sent": "📤 Check-in request sent to **{client}**.",
        "auto_checkin_enabled": "⚙️ Auto check-in enabled for **{client}** every {interval} minutes.",
        "no_auto_checkins": "No auto check-ins configured yet.",
        "auto_checkins_done": "✅ Auto check-ins sent to {count} client(s).",

        # ── Engagement ────────────────────────────────────────────────────
        "engagement_text": "👤 **{client}**\n📝 Notes: {notes}\n💬 Check-ins: {checkins}\n📊 Avg score: {avg}\n\n{label}",
        "good_stability": "🟢 Good stability",
        "moderate": "🟡 Some fluctuations — worth keeping an eye on",
        "risk_zone": "🔴 Risk zone — consider reaching out",
        "no_checkin_data": "No check-in data yet",
        "flag_risk": "⚠️ Risk zone detected: emotional stability is trending low",
        "flag_negative": "⚠️ Negative trend detected — a proactive check-in might help",

        # ── Reminders ─────────────────────────────────────────────────────
        "reminder_set": "⏰ Reminder set for **{client}** in {minutes} minutes.",
        "no_reminders": "No reminders set yet.",
        "reminders_title": "⏰ Active reminders:",

        # ── Sessions ──────────────────────────────────────────────────────
        "session_scheduled": "📅 Session with **{client}** scheduled for **{date}** ({tz_info}).\nI'll remind you 24h and 1h before — and the client too.",
        "tz_info": "your time, {offset}",
        "timezone_usage": "🕐 Current timezone: {current}\n\nChange it with:\n/timezone +3\n/timezone -5\n/timezone +05:30\n/timezone Europe/Moscow",
        "timezone_invalid": "⚠️ I don't recognise that timezone. Try:\n/timezone +3\n/timezone Europe/Moscow\n/timezone -05:30",
        "timezone_saved": "✅ Timezone saved: {tz} ({offset}).",
        "onboarding_welcome": "👋 Welcome to Prokhor!\n\nLet's start with your language:",
        "ask_timezone_onboarding": "🕐 Almost there! Choose your timezone so session times show up correctly:",
        "ask_timezone_settings": "🕐 Choose your timezone:",
        "ask_timezone_custom": (
            "Enter your timezone:\n\n"
            "Examples:\n"
            "  +3   -5   +05:30\n"
            "  Europe/Moscow   America/New_York"
        ),
        "btn_tz_custom": "✏️ Enter manually",
        "btn_skip":      "⏭ Skip for now",
        "btn_timezone":  "🕐 Timezone",
        "tz_skipped": "Timezone set to UTC for now — change it any time in ⚙️ Settings.",
        "sessions_title": "📅 Upcoming sessions:",
        "no_sessions": "No upcoming sessions yet. Time to schedule one?",
        "session_row": "#{id} · {client} · {date}",
        "session_cancelled": "❌ Session #{id} cancelled.",
        "session_not_found": "😕 Session not found.",
        "session_rescheduled": "✅ Session #{id} rescheduled to {date}.",
        "session_cancelled_notify": "⚠️ Your session on {date} has been cancelled. Your specialist will be in touch.",
        "session_rescheduled_notify": "🔄 Your session has been moved to {date}. See you then!",
        "reminder_psych_24h": "🔔 Heads up! Session with **{client}** is tomorrow at {time}.",
        "reminder_psych_1h": "🔔 In 1 hour — session with **{client}** at {time}. All set?",
        "reminder_client_24h": "⏰ Reminder:\nYour session with your specialist is **tomorrow at {time}**. See you soon!",
        "reminder_client_1h": "⏰ Reminder:\nYour session starts **in 1 hour** (at {time}). Get comfortable 🙂",
        "session_link_line": "\n🔗 Session link:\n{link}",

        # ── Dashboard ─────────────────────────────────────────────────────
        "dashboard_title": "📈 Dashboard overview:",
        "dashboard_row": "👤 **{name}**\n📝 {notes} notes · 💬 {checkins} check-ins · Avg: {avg}\n{status}",
        "no_data": "No data yet",

        # ── Homework ──────────────────────────────────────────────────────
        "homework_sent": "📚 Homework sent to **{client}**!",
        "homework_saved_offline": "📚 Homework saved for **{client}** — it'll be delivered once they connect.",
        "homeworks_title": "📚 Homework for **{client}**:",
        "no_homework": "No homework assigned to {client} yet.",
        "new_homework_client": "📚 Your specialist has sent you new homework:\n\n{text}",

        # ── Invite ────────────────────────────────────────────────────────
        "invite_link": "🔗 Invite link for **{client}**:\n{link}",
        "invite_invalid": "😕 This invite link seems to be invalid or expired.",
        "client_info": "👤 **{client}**\nConnected: {connected}\n{tg_line}",
        "tg_id_line": "Telegram ID: {tid}",
        "tg_not_connected": "Telegram: not connected yet",

        # ── Timeline ──────────────────────────────────────────────────────
        "timeline_title": "📈 Timeline for **{client}**:",
        "no_timeline": "Nothing here yet — history will build up over time.",
        "timeline_note": "📝 Note: {text}",
        "timeline_checkin": "💬 Check-in: {score}/10",
        "timeline_homework": "📚 Homework: {text}",
        "timeline_session": "📅 Session",

        # ── Alerts ────────────────────────────────────────────────────────
        "alerts_title": "⚠️ Alerts:",
        "no_alerts": "✅ All good — no alerts at the moment.",
        "alert_low_score": "⚠️ {client}: average score is below 4",
        "alert_no_checkin": "⚠️ {client}: no check-ins for 10+ days",
        "alert_no_session": "⚠️ {client}: no sessions for 30+ days",

        # ── Tags ──────────────────────────────────────────────────────────
        "tag_added": "🏷 Tag «{tag}» added to **{client}**.",
        "find_title": "🏷 Clients tagged «{tag}»:",
        "no_clients_tag": "No clients found with tag «{tag}».",

        # ── Export ────────────────────────────────────────────────────────
        "export_filename":       "export_{client}.txt",
        "export_csv_filename":   "export_{client}.csv",
        "export_all_filename":   "export_all_clients.txt",
        "export_select_format":  "📤 How would you like to export the data?",
        "export_done":           "✅ Here's your export for **{name}** — ready to download!",
        "export_all_done":       "✅ All {count} clients exported successfully.",
        "export_all_no_clients": "No active clients to export yet.",
        "btn_export_txt":        "📄 TXT (readable)",
        "btn_export_csv":        "📊 CSV (Excel / Sheets)",
        "btn_back_to_card":      "⬅️ Back to card",

        # ── Client-side ───────────────────────────────────────────────────
        "client_connected": "🎉 You're now connected to **{specialist}**!\n\nHere's what you can do:\n/my_homeworks — view your homework\n/checkin_history — your recent check-ins",
        "client_menu": "👋 Welcome to Prokhor!\n\nHere's what you can do:\n/my_homeworks — view your homework\n/checkin_history — your recent check-ins",
        "not_a_client": "You're not connected as a client yet. Use your invite link to get started.",
        "checkin_question": "Hey! How are you feeling today? 😊",
        "checkin_thanks": "💙 Got it — thank you for sharing. Your response has been saved.",
        "checkin_submitted": "📊 **{client}** just sent a check-in: {score}/10",
        "my_homeworks_title": "📚 Your homework:",
        "no_my_homeworks": "No homework assigned yet — check back soon!",
        "my_checkins_title": "📊 Your recent check-ins:",
        "no_my_checkins": "No check-ins recorded yet.",
        "client_not_connected_tg": "This client hasn't connected to Telegram yet.",

        # ── Dual role / self-invite protection ────────────────────────────
        "self_invite_error": "⚠️ You can't use your own invite link.",
        "dual_role_select": "You have two roles here. Which would you like to open?",
        "btn_role_psychologist": "🧠 Psychologist mode",
        "btn_role_client": "👤 My client profile",
        "switch_no_dual_role": "You only have one role. Use /start to open your interface.",
        "client_role_reset": "Client profile disconnected. You're now in psychologist mode.",
        "client_role_not_found": "No active client profile found to disconnect.",

        # ── Errors / usage ────────────────────────────────────────────────
        "score_invalid": "Please enter a whole number between 1 and 10.",
        "minutes_invalid": "Please enter a positive whole number for minutes.",
        "interval_invalid": "Please enter a positive whole number for the interval.",
        "date_invalid": "That doesn't look right. Please use the format: YYYY-MM-DD HH:MM",
        "id_invalid": "Session ID must be a positive number.",

        # ── Main menu button labels ───────────────────────────────────────
        "btn_clients":   "👤 Clients",
        "btn_sessions":  "📅 Sessions",
        "btn_homework":  "📚 Homework",
        "btn_analytics": "📊 Analytics",
        "btn_checkins":  "🔔 Check-ins",
        "btn_settings":  "⚙️ Settings",

        # ── Navigation ────────────────────────────────────────────────────
        "btn_back":      "⬅️ Back",
        "btn_main_menu": "🏠 Main Menu",
        "btn_prev":      "⬅️ Prev",
        "btn_next":      "Next ➡️",
        "btn_cancel":    "✖️ Cancel",

        # ── Section sub-buttons ───────────────────────────────────────────
        "btn_add_client":       "➕ Add Client",
        "btn_client_list":      "📋 Client List",
        "btn_invite_client":    "🔗 Invite Client",
        "btn_archived_clients": "📦 Archive",
        "btn_schedule_session": "➕ Schedule Session",
        "btn_upcoming_sessions":"📋 Upcoming Sessions",
        "btn_assign_homework":  "➕ Assign Homework",
        "btn_active_homework":  "📋 Active Homework",
        "btn_dashboard":        "📈 Dashboard",
        "btn_alerts":           "⚠️ Alerts",
        "btn_send_checkin":     "➕ Send Check-in",
        "btn_auto_checkins":    "⚙️ Auto Check-ins",
        "btn_recent_checkins":  "📋 Recent Check-ins",
        "btn_language":         "🌍 Language",
        "btn_about":            "ℹ️ About",

        # ── Client card action buttons ────────────────────────────────────
        "btn_add_note":      "📝 Note",
        "btn_soap_note":     "📋 SOAP",
        "btn_assign_hw":     "📚 Homework",
        "btn_send_ci":       "💬 Check-in",
        "btn_sched_session": "📅 Session",
        "btn_timeline":      "📈 Timeline",
        "btn_tags":          "🏷 Tags",
        "btn_engagement":    "📊 Engagement",
        "btn_export":        "📤 Export",
        "btn_archive":       "📦 Archive",
        "btn_unarchive":     "♻️ Restore",
        "btn_invite_link":   "🔗 Invite Link",
        "btn_card_more":     "⋯ More",
        "note_type_prompt":  "Choose note type:",

        # ── Session card buttons ──────────────────────────────────────────
        "btn_reschedule":    "✏️ Reschedule",
        "btn_cancel_session":"❌ Cancel",

        # ── Section titles ────────────────────────────────────────────────
        "section_clients":   "👤 Clients",
        "section_sessions":  "📅 Sessions",
        "section_homework":  "📚 Homework",
        "section_analytics": "📊 Analytics",
        "section_checkins":  "🔔 Check-ins",
        "section_settings":  "⚙️ Settings",

        # ── FSM prompts ───────────────────────────────────────────────────
        "ask_client_name":       "What's the client's name?",
        "ask_note_text":         "Type your note — I'll save it right away:",
        "ask_homework_text":     "What's the homework assignment?",
        "ask_session_datetime":  "When's the session? Enter date and time in your timezone (YYYY-MM-DD HH:MM):",
        "ask_reschedule_datetime":"New date and time in your timezone (YYYY-MM-DD HH:MM):",
        "ask_tag":               "Enter a tag:",
        "ask_checkin_client":    "Which client should receive the check-in?",
        "ask_auto_client":       "Enter the client's name:",
        "ask_auto_interval":     "How often (in minutes) should the auto check-in be sent?",
        "fsm_cancelled":         "No problem — cancelled! 👌",

        # ── Client card ───────────────────────────────────────────────────
        "client_card":    "👤 **{name}**\n\n📝 Notes: {notes}  ·  💬 Check-ins: {checkins}  ·  Avg: {avg}\n📅 Next session: {session}",
        "no_next_session":"Not scheduled yet",
        "page_indicator": "{page} / {total}",

        # ── Homework list ─────────────────────────────────────────────────
        "homework_list_title": "📚 Active homework:",
        "no_active_homework":  "No active homework right now.",

        # ── Check-in recent ───────────────────────────────────────────────
        "recent_checkins_title": "💬 Recent check-ins (last 10):",
        "no_recent_checkins":    "No check-ins yet — send the first one!",

        # ── About ─────────────────────────────────────────────────────────
        "about_text": (
            "🤖 *Prokhor* — your assistant for psychologists and coaches.\n\n"
            "Version 2.0\n\n"
            "I help you manage clients, plan sessions, assign homework, "
            "take notes (including SOAP), track check-ins, and export data — "
            "all in one place, with full EN/RU support.\n\n"
            "Questions? Reach out to the administrator."
        ),

        # ── Cohorts ───────────────────────────────────────────────────────
        "cohort_ask_name":              "What would you like to name this cohort?",
        "cohort_ask_description":       "Add a short description (or tap Skip):",
        "cohort_ask_max":               "Maximum number of participants? (Send a number, or anything to use the default of 12):",
        "cohort_ask_type":              "What type of cohort is this?",
        "cohort_created":               "🎉 Cohort created: <b>{name}</b>\n\nType: {type}\nMax participants: {max}\n\n🔗 Invite link:\n{link}",
        "cohort_list_title":            "👥 Your cohorts:",
        "no_cohorts":                   "No cohorts yet 😊 Create your first one with /cohort_create.",
        "cohort_list_row":              "• {name} ({count}/{max} members)",
        "cohort_join_prompt":           "You've been invited to join <b>{name}</b>!\n\nTap the button below to confirm.",
        "cohort_join_confirm":          "🎉 Welcome to <b>{name}</b>!",
        "cohort_already_member":        "You're already a member of this cohort.",
        "cohort_is_leader":             "You're the leader of this cohort.",
        "cohort_invalid_token":         "😕 This invite link seems to be invalid or expired.",
        "cohort_full":                  "This cohort is full — no more spots available.",
        "btn_cohort_join":              "✅ Join cohort",
        "btn_cohort_skip_desc":         "⏭ Skip",
        "btn_cohort_type_course":       "📚 Course",
        "btn_cohort_type_group":        "👥 Group",
        "btn_cohort_type_supervision":  "🔍 Supervision",

        # ── Cohort sessions ───────────────────────────────────────────────
        "cs_pick_cohort_schedule":  "Which cohort should this session be scheduled for?",
        "cs_pick_cohort_list":      "Which cohort's sessions would you like to see?",
        "cs_ask_session_num":       "What's the session number?",
        "cs_ask_datetime":          "Date and time in your timezone (YYYY-MM-DD HH:MM):",
        "cs_ask_topic":             "Session topic? (or tap Skip):",
        "cs_ask_link":              "Session link? (or tap Skip):",
        "cs_skip":                  "⏭ Skip",
        "cs_created":               "✅ Session #{num} scheduled!\nCohort: {cohort}\n📅 {date}\n📋 Topic: {topic}",
        "cs_no_topic":              "—",
        "cs_list_title":            "📅 Sessions — {cohort}:",
        "no_cs":                    "No sessions scheduled yet. Use /cohort_schedule to add one.",
        "cs_row":                   "#{num} — {date} — {topic} [{status}]",
        "cs_status_scheduled":      "scheduled",
        "cs_status_completed":      "completed",
        "cs_status_cancelled":      "cancelled",
        "cs_att_pick_cohort":       "Which cohort?",
        "cs_att_pick_session":      "Which session?",
        "cs_att_title":             "✅ Attendance — Session #{num} ({cohort}):",
        "cs_att_no_members":        "This cohort has no members yet.",
        "cs_att_no_sessions":       "No sessions found for this cohort.",
        "cs_att_saved":             "✅ Saved!",
        "cs_reminder_24h":          "🔔 Tomorrow at {time} — cohort session #{num} ({cohort}){link_line}",
        "cs_reminder_1h":           "🔔 In 1 hour at {time} — cohort session #{num} ({cohort}){link_line}",
        "cs_reminder_psych_24h":    "🔔 Cohort session #{num} ({cohort}) is **tomorrow at {time}**. Members have been notified.{link_line}",
        "cs_reminder_psych_1h":     "🔔 Cohort session #{num} ({cohort}) starts **in 1 hour** ({time}). Members have been notified.{link_line}",
        "cs_link_line":             "\n🔗 {link}",

        # ── SESSIONS: browsable session list + detail/action view ──────────
        "cv2_sessions":             "📅 Sessions",
        "cs2_list_title":           "📅 Sessions — «{cohort}» (next {days} days):",
        "cs2_list_empty":           "No sessions in the next {days} days for «{cohort}». Schedule one?",
        "cs2_btn_add_oneoff":       "➕ One-off session",
        "cs2_btn_add_recurring":    "🔁 Set up recurring",
        "cs2_btn_back_list":        "⬅️ Back to list",
        "cs2_not_found":            "This session wasn't found — it may have been deleted.",
        "cs2_detail_header":       "📋 Session #{num} — {cohort}",
        "cs2_detail_date":         "📅 {date}",
        "cs2_detail_topic":        "📝 Topic: {topic}",
        "cs2_detail_link":         "🔗 Link: {link}",
        "cs2_detail_recurring":    "🔁 Repeats: {days}",
        "cs2_detail_paused":       "⏸ Paused — no new sessions are being generated",
        "cs2_no_link":             "—",
        "cs2_btn_edit_dt":          "✏️ Date / time",
        "cs2_btn_edit_topic":       "📝 Topic",
        "cs2_btn_edit_link":        "🔗 Link",
        "cs2_btn_delete":           "🗑 Delete",
        "cs2_btn_pause":            "⏸ Pause recurrence",
        "cs2_btn_resume":           "▶️ Resume recurrence",
        "cs2_btn_delete_rule":      "🚫 Delete recurrence rule",
        "cs2_btn_clear":            "🗑 Clear",
        "cs2_ask_datetime_new":     "New date and time in your timezone (YYYY-MM-DD HH:MM):",
        "cs2_ask_topic_new":        "New topic — or tap Clear to remove it:",
        "cs2_ask_link_new":         "New link — or tap Clear to remove it:",
        "cs2_updated_dt":           "✅ Date and time updated.",
        "cs2_updated_topic":        "✅ Topic updated.",
        "cs2_updated_link":         "✅ Link updated.",
        "cs2_delete_confirm":       "Delete session #{num} on {date}?\nAttendance records for this session will also be removed.",
        "cs2_delete_yes":           "🗑 Yes, delete",
        "cs2_delete_no":            "❌ Cancel",
        "cs2_deleted_ok":           "✅ Session #{num} deleted.",
        "cs2_paused_ok":            "⏸ Recurrence paused for «{cohort}». No new sessions will be created until you resume.",
        "cs2_resumed_ok":           "▶️ Recurrence resumed for «{cohort}». Sessions will keep generating.",
        "cs2_delrule_confirm":      "Delete the recurrence rule for «{cohort}»?\nScheduled sessions stay, but no new ones will be created.",
        "cs2_delrule_yes":          "🚫 Delete rule",
        "cs2_delrule_no":           "❌ Cancel",
        "cs2_delrule_ok":           "✅ Recurrence rule deleted for «{cohort}».",

        # ── RECURRING: recurring cohort sessions ───────────────────────────
        "dow_mon": "Mon", "dow_tue": "Tue", "dow_wed": "Wed", "dow_thu": "Thu",
        "dow_fri": "Fri", "dow_sat": "Sat", "dow_sun": "Sun",
        "cs_recurring_pick_cohort":  "Which cohort should this recurring session apply to?",
        "cs_recurring_ask_days":    "Pick the weekdays this session should repeat on, then tap Done:",
        "cs_recurring_days_done":  "✅ Done",
        "cs_recurring_days_empty": "Please select at least one weekday.",
        "cs_recurring_ask_time":   "What time should the session be? (Your timezone, HH:MM):",
        "cs_recurring_created":    "✅ Recurring session set up!\nCohort: {cohort}\nDays: {days}\n🕐 {time}\nSessions for the next 30 days have been scheduled automatically.",
        "cs_recurring_intro":     "🔁 Set up a recurring cohort session",

        # ── MENU: hierarchical reply keyboard ─────────────────────────────
        "btn_menu_individual":   "👤 Individual",
        "btn_menu_cohorts":      "👥 My Cohorts",
        "btn_menu_summary":      "📊 Summary",
        "btn_menu_settings":     "⚙️ Settings",
        "btn_menu_back":         "⬅️ Back",
        # Individual submenu
        "btn_ind_add_client":    "➕ Add Client",
        "btn_ind_client_list":   "📋 Client List",
        "btn_ind_new_note":      "📝 New Note",
        "btn_ind_schedule":      "📅 Schedule Session",
        "btn_ind_reminders":     "⏰ Reminders",
        # Cohorts submenu
        "btn_coh_create":        "➕ Create Cohort",
        "btn_coh_list":          "📋 Cohort List",
        # Summary submenu
        "btn_sum_clients":       "👤 Clients",
        "btn_sum_cohorts":       "👥 Cohorts",
        "btn_sum_stats":         "📈 Statistics",
        # Settings submenu
        "btn_set_language":      "🌍 Language",
        "btn_set_timezone":      "🕐 Timezone",
        "btn_set_tariff":        "💰 My Plan",
        "btn_set_notifs":        "🔔 Notifications",
        # Section headers
        "section_individual":    "👤 Individual:",
        "section_cohorts_menu":  "👥 My Cohorts:",
        "section_summary":       "📊 Summary:",
        "section_settings_menu": "⚙️ Settings:",

        # ── COHORT_V2: cohort action menu labels ───────────────────────────
        "cv2_members":    "👥 Members",
        "cv2_schedule":   "📅 Sessions",
        "cv2_attendance": "✅ Attendance",
        "cv2_checkins":   "📊 Check-ins",
        "cv2_notes":      "📝 Notes",
        "cv2_broadcast":  "📢 Broadcast",
        "cv2_stats":      "📊 Stats",
        "cv2_archive":    "📦 Archive",
        "cv2_recurring":  "🔁 Recurring",
        "cv2_back":       "⬅️ Back",
        "cohort_action_title": "📋 {name}:",

        # Members list
        "cv2_members_title":      "👥 Members of «{cohort}» — {count}:",
        "cv2_member_row_tg":      "• {name}  [TG {tg_id}]",
        "cv2_member_row_manual":  "• {name}  👤",
        "cv2_no_members":         "No members yet 😊",
        "cv2_members_empty_note": "Add someone manually or share the invite link so clients can join themselves.",
        "cv2_btn_add_member":     "➕ Add manually",
        "cv2_btn_invite":         "🔗 Invite link",
        "cv2_add_member_ask":     "What's the new member's name?",
        "cv2_member_added":       "✅ **{name}** added to the cohort!",
        "cv2_invite_text":        "🔗 Invite link for «{cohort}»:\n\n{link}\n\nShare this with your clients — they tap it in Telegram and join automatically.",

        # Broadcast
        "cv2_broadcast_ask":        "Write the message to send to all {count} member(s) of «{cohort}»:",
        "cv2_broadcast_preview":    "📣 Preview:\n\n{text}\n\nSend to {count} member(s)?",
        "cv2_broadcast_send":       "✅ Send",
        "cv2_broadcast_cancel":     "❌ Cancel",
        "cv2_broadcast_done":       "✅ Sent to {sent} of {total} member(s).",
        "cv2_broadcast_no_members": "No active members to send to.",

        # Archive
        "cv2_archive_confirm":  "Archive cohort «{cohort}»?\nReminders will stop for all members.",
        "cv2_archive_yes":      "📦 Archive",
        "cv2_archive_no":       "❌ Cancel",
        "cv2_archived_ok":      "✅ Cohort «{cohort}» has been archived.",
        "cv2_already_archived": "This cohort is already in the archive.",

        # Stats
        "cv2_stats_title":          "📊 Stats — {cohort}:",
        "cv2_stats_members":        "👥 Members: {count}",
        "cv2_stats_sessions":       "📅 Sessions: {total} ({completed} completed)",
        "cv2_stats_attendance_pct": "📋 Avg attendance: {pct}%",
        "cv2_stats_checkins":       "💬 Check-in responses: {count}",
        "cv2_stats_avg_score":      "📊 Avg score: {avg}/10",

        # Check-ins
        "cv2_checkin_options_title": "💬 Check-ins for «{cohort}»:",
        "cv2_checkin_btn_setup":     "⚙️ Set up auto check-in",
        "cv2_checkin_btn_summary":   "📊 View responses",
        "cv2_checkin_btn_send_now":  "📤 Send now",
        "cv2_checkin_ask_question":  "What question should be sent to all members?",
        "cv2_checkin_ask_interval":  "How often (in hours) should it be sent? (e.g. 24 for daily):",
        "cv2_checkin_saved":         "✅ Auto check-in configured!\nQuestion: {q}\nFrequency: every {h}h",
        "cv2_checkin_sent":          "✅ Check-in sent to {count} member(s).",
        "cv2_checkin_summary_title": "📊 Check-in summary — {cohort}:",
        "cv2_checkin_row":           "• {name}: {count} response(s), avg {avg}/10",
        "cv2_no_checkin_data":       "No check-in data yet.",
        "cv2_checkin_member_thanks": "💙 Your response has been recorded — thank you!",

        # Session notes
        "cv2_notes_pick_session": "Which session would you like to view or add notes to?",
        "cv2_notes_title":        "📝 Notes — Session #{num}:",
        "cv2_note_row":           "📝 {text}",
        "cv2_soap_row":           "📋 SOAP:\n{text}",
        "cv2_notes_empty":        "No notes for this session yet. Add the first one?",
        "cv2_note_btn_add":       "➕ Add note",
        "cv2_note_btn_soap":      "📋 SOAP note",
        "cv2_note_ask":           "Type your note for Session #{num}:",
        "cv2_note_saved":         "✅ Note saved!",
        "cv2_soap_s":             "SOAP — Session #{num}.\n\n*S — Subjective:* Client's own words, mood, concerns:",
        "cv2_soap_o":             "*O — Objective:* Your observations, behaviour, test results:",
        "cv2_soap_a":             "*A — Assessment:* Clinical impression and working hypothesis:",
        "cv2_soap_p":             "*P — Plan:* Next steps, homework, or focus:",
        "cv2_soap_saved":         "✅ SOAP note saved for Session #{num}.",

        # Notifications stub
        "notifs_not_implemented": "🔔 Notification settings are coming soon — stay tuned!",

        # ── INDIVIDUAL_SESSION: per-client session management ──────────────
        "btn_client_sessions":    "📅 Sessions",
        "is_sessions_title":      "📅 Sessions — {client}:",
        "is_sessions_empty":      "No upcoming sessions for {client}. Schedule one?",
        "is_btn_add_oneoff":      "➕ One-off session",
        "is_btn_add_recurring":   "🔁 Set up recurring",
        "is_btn_back_list":       "⬅️ Back to list",
        "is_not_found":           "Session not found — it may have been deleted.",
        "is_detail_header":       "📋 {client}",
        "is_detail_date":         "📅 {date}",
        "is_detail_topic":        "📝 Topic: {topic}",
        "is_detail_link":         "🔗 Link: {link}",
        "is_detail_recurring":    "🔁 Repeats: {days}",
        "is_detail_paused":       "⏸ Recurrence paused",
        "is_btn_edit_dt":         "✏️ Date / time",
        "is_btn_edit_topic":      "📝 Topic",
        "is_btn_edit_link":       "🔗 Link",
        "is_btn_delete":          "🗑 Delete",
        "is_btn_pause":           "⏸ Pause recurrence",
        "is_btn_resume":          "▶️ Resume recurrence",
        "is_btn_delete_rule":     "🚫 Delete recurrence rule",
        "is_btn_clear":           "🗑 Clear",
        "is_ask_datetime":        "Date and time in your timezone (YYYY-MM-DD HH:MM):",
        "is_ask_datetime_new":    "New date and time (YYYY-MM-DD HH:MM):",
        "is_ask_topic_new":       "New topic (or tap Skip):",
        "is_ask_link_new":        "New link (or tap Skip / Clear):",
        "is_updated_dt":          "✅ Date and time updated.",
        "is_updated_topic":       "✅ Topic updated.",
        "is_updated_link":        "✅ Link updated.",
        "is_delete_confirm":      "Delete session on {date}?",
        "is_delete_yes":          "🗑 Yes, delete",
        "is_delete_no":           "❌ Cancel",
        "is_deleted_ok":          "✅ Session deleted.",
        "is_paused_ok":           "⏸ Recurrence paused for {client}.",
        "is_resumed_ok":          "▶️ Recurrence resumed for {client}.",
        "is_delrule_confirm":     "Delete the recurrence rule for {client}?\nScheduled sessions stay, but no new ones will be created.",
        "is_delrule_yes":         "🚫 Delete rule",
        "is_delrule_no":          "❌ Cancel",
        "is_delrule_ok":          "✅ Recurrence rule deleted.",
        "is_recurring_ask_days":  "Pick the weekdays this session repeats on, then tap Done:",
        "is_recurring_days_empty":"Please select at least one weekday.",
        "is_recurring_ask_time":  "What time should the session be? (Your timezone, HH:MM):",
        "is_recurring_created":   "✅ Recurring session set up!\nClient: {client}\nDays: {days}\n🕐 {time}\nSessions for the next 30 days have been scheduled automatically.",
        "is_session_created":     "📅 Session scheduled for **{client}** on {date}. I'll remind you both in advance!",
        "err_invalid_datetime":   "That format doesn't look right. Please use YYYY-MM-DD HH:MM (e.g. 2025-03-15 14:30).",
        "err_invalid_time":       "That format doesn't look right. Please use HH:MM (e.g. 14:30).",

        # Supervision
        "sup_case_alias":       "Enter a client alias (no real names, please):",
        "sup_case_issue":       "What's the presenting issue — why did the client come?",
        "sup_case_hypothesis":  "What's your working hypothesis?",
        "sup_case_intervention":"What intervention did you use or plan to use?",
        "sup_case_outcome":     "What outcome do you expect or observe?",
        "sup_case_saved":       "✅ Supervision case saved: **{alias}**",
        "sup_logbook_title":    "📓 Supervision logbook — {count} case(s):",
        "sup_logbook_row":      "#{id} {alias} [{status}] — {date}",
        "sup_logbook_empty":    "No supervision cases yet. Use /supervision_case to add the first one.",
        "sup_progress_title":   "📂 Open supervision cases:",
        "sup_progress_row":     "#{id} **{alias}**\nIssue: {issue}\nHypothesis: {hyp}\nIntervention: {interv}\nOutcome: {outcome}",
        "sup_progress_empty":   "No open supervision cases — all clear 🎉",
        "sup_close_btn":        "✅ Close case",
        "sup_case_closed":      "✅ Case #{id} closed.",
        "sup_case_not_found":   "Case not found.",

        # ── Tariff screen ──────────────────────────────────────────────────
        "tariff_screen_start": (
            "📦 Your plan: *Start* (free)\n\n"
            "What's included:\n"
            "• Up to 5 individual clients\n"
            "• Up to 2 groups/cohorts\n"
            "• Up to 15 members per cohort\n"
            "• Check-ins and reminders\n"
            "• Analytics for the last 30 days\n"
            "• ❌ Export\n"
            "• ❌ Supervision logbook\n\n"
            "✨ Upgrade to Pro and work without limits."
        ),
        "tariff_screen_pro": (
            "💎 Your plan: *Pro*{expires}\n\n"
            "Everything in Start, plus:\n"
            "• Unlimited individual clients\n"
            "• Up to 10 cohorts\n"
            "• Up to 50 members per cohort\n"
            "• Full analytics history\n"
            "• ✅ Export of notes and sessions\n"
            "• ✅ Supervision logbook\n\n"
            "Thank you for supporting the project! 🙌"
        ),
        "tariff_compare": (
            "📊 *Plan comparison*\n\n"
            "┌─────────────────┬────────┬──────┐\n"
            "│ Feature         │ Start  │  Pro │\n"
            "├─────────────────┼────────┼──────┤\n"
            "│ Clients         │  5     │  ∞   │\n"
            "│ Cohorts         │  2     │  10  │\n"
            "│ Members/cohort  │  15    │  50  │\n"
            "│ Analytics       │ 30 d   │  ∞   │\n"
            "│ Export          │  ❌    │  ✅  │\n"
            "│ Supervision     │  ❌    │  ✅  │\n"
            "│ Check-ins       │  ✅    │  ✅  │\n"
            "└─────────────────┴────────┴──────┘\n\n"
            "To activate Pro, enter a promo code: /promo"
        ),
        "tariff_howto": (
            "❓ *How does it work?*\n\n"
            "Prokhor has two plans:\n\n"
            "🟢 *Start* — free, always. Great for getting started "
            "and working with a small client base.\n\n"
            "💎 *Pro* — activated via a promo code. Removes all limits "
            "and unlocks export and the supervision logbook.\n\n"
            "To get a promo code, contact your administrator "
            "or check the bot's main channel.\n\n"
            "To enter a promo code: /promo"
        ),
        "tariff_history_empty": (
            "📜 No plan changes recorded yet.\n\n"
            "Your current plan: *{plan}*"
        ),
        "tariff_already_pro": "💎 You're already on Pro — enjoy working without limits!",
        # Reminder sent the day before a paid plan expires (notify_expiring_plans)
        "plan_expiring_tomorrow": "⏰ Reminder: your {plan} plan expires tomorrow ({date}). Use /promo to renew.",
        "btn_tariff_upgrade":  "💎 Upgrade to PRO",
        "btn_tariff_compare":  "📊 Compare plans",
        "btn_tariff_history":  "📜 Payment history",
        "btn_tariff_howto":    "❓ How does this work?",
        "btn_tariff_back":     "⬅️ Back",

        # ── Self-booking: psychologist settings ───────────────────────────
        "btn_set_booking":           "📅 Client Booking",
        "section_booking":           "📅 Client Booking",
        "booking_pro_only":          "⚠️ Client self-booking is available on the Pro plan only.\nEnter a promo code: /promo",
        "booking_no_profile":        "You haven't set up your booking profile yet.",
        "btn_booking_setup":         "🛠 Set Up Booking Profile",
        "ask_booking_display_name":  "👤 What name should clients see on your booking page?\n(e.g. your full name or professional name):",
        "ask_booking_bio":           "📝 Write a short bio for clients (up to 300 characters).\nThis appears on your booking page:",
        "booking_bio_too_long":      "⚠️ Bio is too long ({length} chars). Please keep it under 300 characters:",
        "ask_booking_timezone":      "🕐 Choose your working timezone — slots will be generated in this timezone:",
        "booking_profile_saved":     "✅ Booking profile created! Now configure your weekly schedule.",
        "booking_profile_card":      (
            "📅 *Your Booking Profile*\n\n"
            "👤 Name: {display_name}\n"
            "📝 Bio: {bio}\n"
            "🔗 Slug: `{slug}`\n"
            "🕐 Timezone: {timezone}\n"
            "Status: {status}\n\n"
            "Booking link:\n`{link}`"
        ),
        "booking_enabled_on":        "🟢 Accepting bookings",
        "booking_enabled_off":       "🔴 Booking paused",
        "booking_toggled_on":        "✅ Booking enabled — clients can now book sessions.",
        "booking_toggled_off":       "❌ Booking paused — your link shows 'not accepting bookings'.",
        "btn_booking_toggle_on":     "▶️ Enable Booking",
        "btn_booking_toggle_off":    "⏸ Pause Booking",
        "btn_booking_schedule":      "📋 Weekly Schedule",
        "btn_booking_exceptions":    "🚫 Blocked Dates",
        "btn_booking_link":          "🔗 Booking Link",
        "btn_booking_edit_name":     "✏️ Edit Name",
        "btn_booking_edit_bio":      "✏️ Edit Bio",
        "btn_booking_edit_tz":       "🕐 Change Timezone",
        "booking_link_msg":          "🔗 Your booking link:\n\n`{link}`\n\nShare this with clients so they can book sessions.",
        "booking_schedule_title":    "📋 *Weekly Schedule*\n\nTap a day to configure it:",
        "booking_day_configured":    "✅ {day}: {start}–{end} ({duration} min + {buffer} min break)",
        "booking_day_none":          "➖ {day}: not configured",
        "ask_booking_day_start":     "⏰ *{day}*\nEnter start of working hours (HH:MM, e.g. 10:00):",
        "ask_booking_day_end":       "Enter end of working hours (HH:MM, e.g. 18:00):",
        "ask_booking_day_duration":  "Enter session duration in minutes (e.g. 50):",
        "ask_booking_day_buffer":    "Enter break between sessions in minutes (0 = no break):",
        "booking_day_saved":         "✅ Schedule saved for {day}.",
        "booking_day_removed":       "🗑 Schedule removed for {day}.",
        "booking_invalid_time":      "⚠️ Invalid format. Enter as HH:MM (e.g. 10:00):",
        "booking_invalid_number":    "⚠️ Please enter a whole number:",
        "booking_time_order":        "⚠️ End time must be after start time. Re-enter end time:",
        "btn_booking_remove_day":    "🗑 Remove This Day",
        "booking_exceptions_title":  "🚫 *Blocked Dates*\n\n{items}",
        "booking_no_exceptions":     "No blocked dates configured.",
        "booking_exception_row":     "• {date} {time_range}",
        "booking_exception_whole_day": "(whole day)",
        "ask_booking_ex_date":       "Enter the date to block (DD.MM.YYYY or YYYY-MM-DD):",
        "ask_booking_ex_start":      "Enter block start time (HH:MM), or tap 'Whole Day':",
        "ask_booking_ex_end":        "Enter block end time (HH:MM):",
        "booking_ex_saved":          "✅ Date blocked: {date}.",
        "booking_invalid_date":      "⚠️ Invalid date. Enter as DD.MM.YYYY or YYYY-MM-DD:",
        "btn_booking_add_exception": "➕ Add Blocked Date",
        "btn_booking_whole_day":     "🚫 Whole Day",
        "btn_booking_del_ex":        "🗑 Remove",

        # ── Self-booking: client-facing ───────────────────────────────────
        "booking_card_text":         "👤 *{display_name}*\n\n{bio}",
        "btn_booking_book":          "📅 Book a Session",
        "booking_unavailable":       "⚠️ This specialist is not accepting bookings right now. Please try again later.",
        "booking_profile_not_found": "😕 Booking page not found. The link may be outdated.",
        "ask_client_tz_booking":     "🕐 To show available slots in your local time, please choose your timezone:",
        "booking_no_slots":          "😕 No available slots in the next 14 days. Please check back later.",
        "booking_dates_title":       "📅 Choose a date:",
        "booking_slots_title":       "🕐 Slots on {date} (your time):",
        "booking_confirm_text":      "✅ *Confirm booking*\n\n📅 {datetime} (your time)\n👤 {name}\n\nBook this session?",
        "btn_booking_confirm":       "✅ Confirm",
        "btn_booking_back_dates":    "⬅️ Other dates",
        "btn_booking_back_slots":    "⬅️ Other times",
        "booking_success":           "🎉 Session booked!\n\n📅 *{datetime}* (your time)\n👤 {name}\n\nYou'll get reminders 24h and 1h before your session.",
        "booking_slot_taken":        "⚠️ This slot was just taken. Please choose another time.",
        "booking_error":             "⚠️ Something went wrong. Please try again.",
        "booking_psych_notify":      (
            "📅 *New self-booking!*\n\n"
            "Client: {client}\n"
            "Date: {datetime} (your time)\n\n"
            "ℹ️ Booked by the client via self-booking link."
        ),
    },

    "ru": {
        # ── Приветствие психолога ─────────────────────────────────────────
        "welcome": "👋 Привет! Прохор на связи — твой ассистент для ведения клиентов и сессионных заметок. Начнём?",
        "language_select": "🌍 Выбери язык интерфейса:",
        "language_saved": "✅ Язык сохранён!",

        # ── Управление клиентами ──────────────────────────────────────────
        "client_added": "✅ Клиент **{name}** добавлен! Теперь я помогу вести его карточку.",
        "client_not_found": "😕 Клиент «{name}» не найден. Проверь написание?",
        "no_clients": "Клиентов пока нет 😊 Добавим первого?",
        "clients_title": "👤 Твои клиенты:",
        "clients_status_title": "📋 Статус подключения клиентов:",
        "connected": "подключён ✅",
        "not_connected": "ещё не подключён",
        "client_archived": "📦 **{name}** перемещён в архив. Можно восстановить в любой момент.",
        "client_already_archived": "**{name}** уже находится в архиве.",
        "client_unarchived": "♻️ **{name}** снова в активном списке!",
        "client_not_archived": "**{name}** не находится в архиве.",
        "archived_title": "📦 Архивные клиенты:",
        "no_archived": "Архив пуст — все клиенты активны 🎉",

        # ── Заметки ───────────────────────────────────────────────────────
        "note_saved": "📝 Заметка для **{client}** сохранена.",
        "notes_title": "📝 Заметки по **{client}**:",
        "no_notes": "Для {client} заметок пока нет. Добавим первую?",
        "summary_text": "👤 Клиент: **{client}**\n📝 Заметок: {count}",
        "summary_last": "\n🕐 Последнее обновление:\n{last}",
        "soap_saved": "📋 SOAP-заметка для **{client}** сохранена:\n\n{text}",
        "soap_s": "Начинаем SOAP-заметку по **{client}**.\n\n*S — Субъективное:* Слова клиента — его ощущения, жалобы, настроение:",
        "soap_o": "*O — Объективное:* Твои наблюдения — поведение, реакции, результаты тестов:",
        "soap_a": "*A — Оценка:* Клиническое впечатление и рабочая гипотеза:",
        "soap_p": "*P — План:* Следующие шаги, домашнее задание, фокус на следующей сессии:",

        # ── Чек-ины ───────────────────────────────────────────────────────
        "checkin_saved": "💬 Чек-ин для **{client}** сохранён: {score}/10",
        "checkins_title": "💬 Чек-ины по **{client}**:",
        "no_checkins": "Для {client} чек-инов пока нет. Отправим первый?",
        "checkin_request_sent": "📤 Запрос чек-ина отправлен **{client}**.",
        "auto_checkin_enabled": "⚙️ Авточек-ин для **{client}** включён: каждые {interval} минут.",
        "no_auto_checkins": "Авточек-ины пока не настроены.",
        "auto_checkins_done": "✅ Авточек-ины отправлены {count} клиент(у/ам).",

        # ── Вовлечённость ─────────────────────────────────────────────────
        "engagement_text": "👤 **{client}**\n📝 Заметок: {notes}\n💬 Чек-инов: {checkins}\n📊 Средний балл: {avg}\n\n{label}",
        "good_stability": "🟢 Хорошая стабильность",
        "moderate": "🟡 Небольшие колебания — стоит понаблюдать",
        "risk_zone": "🔴 Зона риска — возможно, стоит выйти на связь",
        "no_checkin_data": "Данных чек-инов пока нет",
        "flag_risk": "⚠️ Обнаружена зона риска: тренд эмоциональной стабильности снижается",
        "flag_negative": "⚠️ Выявлен негативный тренд — возможно, стоит провести проактивный чек-ин",

        # ── Напоминания ───────────────────────────────────────────────────
        "reminder_set": "⏰ Напоминание для **{client}** установлено через {minutes} минут.",
        "no_reminders": "Напоминаний пока нет.",
        "reminders_title": "⏰ Активные напоминания:",

        # ── Сессии ────────────────────────────────────────────────────────
        "session_scheduled": "📅 Сессия с **{client}** запланирована на **{date}** ({tz_info}).\nНапомню тебе и клиенту за 24ч и за 1ч.",
        "tz_info": "твоё время, {offset}",
        "timezone_usage": "🕐 Текущий часовой пояс: {current}\n\nИзменить:\n/timezone +3\n/timezone -5\n/timezone +05:30\n/timezone Europe/Moscow",
        "timezone_invalid": "⚠️ Такой часовой пояс не распознан. Попробуй:\n/timezone +3\n/timezone Europe/Moscow\n/timezone -05:30",
        "timezone_saved": "✅ Часовой пояс сохранён: {tz} ({offset}).",
        "onboarding_welcome": "👋 Добро пожаловать в Прохор!\n\nДля начала выберем язык:",
        "ask_timezone_onboarding": "🕐 Почти готово! Выбери часовой пояс, чтобы время сессий отображалось правильно:",
        "ask_timezone_settings": "🕐 Выбери свой часовой пояс:",
        "ask_timezone_custom": (
            "Введи часовой пояс:\n\n"
            "Примеры:\n"
            "  +3   -5   +05:30\n"
            "  Europe/Moscow   America/New_York"
        ),
        "btn_tz_custom": "✏️ Ввести вручную",
        "btn_skip":      "⏭ Пропустить",
        "btn_timezone":  "🕐 Часовой пояс",
        "tz_skipped": "Часовой пояс пока UTC — можно изменить в ⚙️ Настройках.",
        "sessions_title": "📅 Предстоящие сессии:",
        "no_sessions": "Предстоящих сессий пока нет. Запланируем?",
        "session_row": "#{id} · {client} · {date}",
        "session_cancelled": "❌ Сессия #{id} отменена.",
        "session_not_found": "😕 Сессия не найдена.",
        "session_rescheduled": "✅ Сессия #{id} перенесена на {date}.",
        "session_cancelled_notify": "⚠️ Твоя сессия {date} отменена. Специалист свяжется с тобой.",
        "session_rescheduled_notify": "🔄 Твоя сессия перенесена на {date}. До встречи!",
        "reminder_psych_24h": "🔔 Напоминание! Сессия с **{client}** — завтра в {time}.",
        "reminder_psych_1h": "🔔 Через 1 час — сессия с **{client}** в {time}. Всё готово?",
        "reminder_client_24h": "⏰ Напоминание:\nЗавтра в {time} у тебя сессия со специалистом. До встречи!",
        "reminder_client_1h": "⏰ Напоминание:\nТвоя сессия начнётся через 1 час — в {time}. Устраивайся поудобнее 🙂",
        "session_link_line": "\n🔗 Ссылка на сессию:\n{link}",

        # ── Дашборд ───────────────────────────────────────────────────────
        "dashboard_title": "📈 Обзор клиентов:",
        "dashboard_row": "👤 **{name}**\n📝 {notes} заметок · 💬 {checkins} чек-инов · Ср. балл: {avg}\n{status}",
        "no_data": "Данных пока нет",

        # ── Домашние задания ──────────────────────────────────────────────
        "homework_sent": "📚 Задание отправлено **{client}**!",
        "homework_saved_offline": "📚 Задание сохранено для **{client}** — будет доставлено после подключения.",
        "homeworks_title": "📚 Задания для **{client}**:",
        "no_homework": "Для {client} заданий пока нет.",
        "new_homework_client": "📚 Твой специалист прислал новое задание:\n\n{text}",

        # ── Приглашение ───────────────────────────────────────────────────
        "invite_link": "🔗 Ссылка-приглашение для **{client}**:\n{link}",
        "invite_invalid": "😕 Эта ссылка недействительна или устарела.",
        "client_info": "👤 **{client}**\nПодключён: {connected}\n{tg_line}",
        "tg_id_line": "Telegram ID: {tid}",
        "tg_not_connected": "Telegram: ещё не подключён",

        # ── Хронология ───────────────────────────────────────────────────
        "timeline_title": "📈 Хронология **{client}**:",
        "no_timeline": "История пока пуста — она будет заполняться со временем.",
        "timeline_note": "📝 Заметка: {text}",
        "timeline_checkin": "💬 Чек-ин: {score}/10",
        "timeline_homework": "📚 Задание: {text}",
        "timeline_session": "📅 Сессия",

        # ── Предупреждения ────────────────────────────────────────────────
        "alerts_title": "⚠️ Предупреждения:",
        "no_alerts": "✅ Всё в порядке — предупреждений нет.",
        "alert_low_score": "⚠️ {client}: средний балл ниже 4",
        "alert_no_checkin": "⚠️ {client}: нет чек-инов уже 10+ дней",
        "alert_no_session": "⚠️ {client}: нет сессий уже 30+ дней",

        # ── Теги ─────────────────────────────────────────────────────────
        "tag_added": "🏷 Тег «{tag}» добавлен для **{client}**.",
        "find_title": "🏷 Клиенты с тегом «{tag}»:",
        "no_clients_tag": "Клиентов с тегом «{tag}» не найдено.",

        # ── Экспорт ───────────────────────────────────────────────────────
        "export_filename":       "экспорт_{client}.txt",
        "export_csv_filename":   "экспорт_{client}.csv",
        "export_all_filename":   "экспорт_все_клиенты.txt",
        "export_select_format":  "📤 Как хочешь экспортировать данные?",
        "export_done":           "✅ Готово! Вот экспорт по **{name}** — скачай файл ниже.",
        "export_all_done":       "✅ Все {count} клиентов успешно экспортированы.",
        "export_all_no_clients": "Нет активных клиентов для экспорта.",
        "btn_export_txt":        "📄 TXT (читаемый)",
        "btn_export_csv":        "📊 CSV (Excel / Sheets)",
        "btn_back_to_card":      "⬅️ Назад к карточке",

        # ── Клиентская сторона ────────────────────────────────────────────
        "client_connected": "🎉 Ты подключён к специалисту **{specialist}**!\n\nДоступные команды:\n/my_homeworks — посмотреть задания\n/checkin_history — история чек-инов",
        "client_menu": "👋 Привет! Я Прохор, ассистент твоего специалиста.\n\nДоступные команды:\n/my_homeworks — посмотреть задания\n/checkin_history — история чек-инов",
        "not_a_client": "Ты ещё не подключён как клиент. Используй ссылку-приглашение от специалиста.",
        "checkin_question": "Привет! Как ты себя чувствуешь сегодня? 😊",
        "checkin_thanks": "💙 Спасибо, что поделился — ответ сохранён.",
        "checkin_submitted": "📊 **{client}** прислал чек-ин: {score}/10",
        "my_homeworks_title": "📚 Твои задания:",
        "no_my_homeworks": "Заданий пока нет — скоро появятся!",
        "my_checkins_title": "📊 Твои последние чек-ины:",
        "no_my_checkins": "Чек-инов пока нет.",
        "client_not_connected_tg": "Клиент ещё не подключился через Telegram.",

        # ── Двойная роль / защита от самоприглашения ──────────────────────
        "self_invite_error": "⚠️ Нельзя использовать собственную ссылку-приглашение.",
        "dual_role_select": "У тебя две роли. Какой интерфейс открыть?",
        "btn_role_psychologist": "🧠 Режим психолога",
        "btn_role_client": "👤 Мой профиль клиента",
        "switch_no_dual_role": "У тебя только одна роль. Используй /start для открытия интерфейса.",
        "client_role_reset": "Профиль клиента отключён. Активен режим психолога.",
        "client_role_not_found": "Активный профиль клиента для отключения не найден.",

        # ── Ошибки / использование ────────────────────────────────────────
        "score_invalid": "Введи целое число от 1 до 10.",
        "minutes_invalid": "Введи положительное целое число для минут.",
        "interval_invalid": "Введи положительное целое число для интервала.",
        "date_invalid": "Не совсем верный формат. Используй: ГГГГ-ММ-ДД ЧЧ:ММ",
        "id_invalid": "ID сессии должен быть положительным числом.",

        # ── Кнопки главного меню ──────────────────────────────────────────
        "btn_clients":   "👤 Клиенты",
        "btn_sessions":  "📅 Сессии",
        "btn_homework":  "📚 Задания",
        "btn_analytics": "📊 Аналитика",
        "btn_checkins":  "🔔 Чек-ины",
        "btn_settings":  "⚙️ Настройки",

        # ── Навигация ─────────────────────────────────────────────────────
        "btn_back":      "⬅️ Назад",
        "btn_main_menu": "🏠 Главное меню",
        "btn_prev":      "⬅️ Пред",
        "btn_next":      "След ➡️",
        "btn_cancel":    "✖️ Отмена",

        # ── Кнопки разделов ───────────────────────────────────────────────
        "btn_add_client":       "➕ Добавить клиента",
        "btn_client_list":      "📋 Список клиентов",
        "btn_invite_client":    "🔗 Пригласить клиента",
        "btn_archived_clients": "📦 Архив",
        "btn_schedule_session": "➕ Запланировать сессию",
        "btn_upcoming_sessions":"📋 Предстоящие сессии",
        "btn_assign_homework":  "➕ Задать задание",
        "btn_active_homework":  "📋 Активные задания",
        "btn_dashboard":        "📈 Обзор",
        "btn_alerts":           "⚠️ Предупреждения",
        "btn_send_checkin":     "➕ Отправить чек-ин",
        "btn_auto_checkins":    "⚙️ Авточек-ины",
        "btn_recent_checkins":  "📋 Последние чек-ины",
        "btn_language":         "🌍 Язык",
        "btn_about":            "ℹ️ О боте",

        # ── Кнопки карточки клиента ───────────────────────────────────────
        "btn_add_note":      "📝 Заметка",
        "btn_soap_note":     "📋 SOAP",
        "btn_assign_hw":     "📚 Задание",
        "btn_send_ci":       "💬 Чек-ин",
        "btn_sched_session": "📅 Сессия",
        "btn_timeline":      "📈 Хронология",
        "btn_tags":          "🏷 Теги",
        "btn_engagement":    "📊 Вовлечённость",
        "btn_export":        "📤 Экспорт",
        "btn_archive":       "📦 Архивировать",
        "btn_unarchive":     "♻️ Восстановить",
        "btn_invite_link":   "🔗 Ссылка-приглашение",
        "btn_card_more":     "⋯ Ещё",
        "note_type_prompt":  "Выберите тип заметки:",

        # ── Кнопки карточки сессии ────────────────────────────────────────
        "btn_reschedule":    "✏️ Перенести",
        "btn_cancel_session":"❌ Отменить",

        # ── Заголовки разделов ────────────────────────────────────────────
        "section_clients":   "👤 Клиенты",
        "section_sessions":  "📅 Сессии",
        "section_homework":  "📚 Задания",
        "section_analytics": "📊 Аналитика",
        "section_checkins":  "🔔 Чек-ины",
        "section_settings":  "⚙️ Настройки",

        # ── Подсказки FSM ─────────────────────────────────────────────────
        "ask_client_name":       "Как зовут клиента?",
        "ask_note_text":         "Напиши заметку — сохраню сразу:",
        "ask_homework_text":     "Что будет в задании?",
        "ask_session_datetime":  "Когда сессия? Введи дату и время в твоём часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "ask_reschedule_datetime":"Новая дата и время в твоём часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "ask_tag":               "Введи тег:",
        "ask_checkin_client":    "Кому отправить чек-ин?",
        "ask_auto_client":       "Введи имя клиента:",
        "ask_auto_interval":     "Как часто отправлять (в минутах)?",
        "fsm_cancelled":         "Хорошо, отменяю 👌",

        # ── Карточка клиента ─────────────────────────────────────────────
        "client_card":    "👤 **{name}**\n\n📝 Заметок: {notes}  ·  💬 Чек-инов: {checkins}  ·  Ср. балл: {avg}\n📅 Следующая сессия: {session}",
        "no_next_session":"Не запланирована",
        "page_indicator": "{page} / {total}",

        # ── Список заданий ────────────────────────────────────────────────
        "homework_list_title": "📚 Активные задания:",
        "no_active_homework":  "Активных заданий пока нет.",

        # ── Последние чек-ины ─────────────────────────────────────────────
        "recent_checkins_title": "💬 Последние чек-ины (10 шт.):",
        "no_recent_checkins":    "Чек-инов пока нет — отправим первый?",

        # ── О боте ───────────────────────────────────────────────────────
        "about_text": (
            "🤖 *Прохор* — ассистент для психологов и коучей.\n\n"
            "Версия 2.0\n\n"
            "Помогаю вести клиентов, планировать сессии, задавать домашние задания, "
            "делать заметки (включая SOAP), отслеживать чек-ины и экспортировать данные — "
            "всё в одном месте, с поддержкой русского и английского.\n\n"
            "Вопросы? Обращайся к администратору."
        ),

        # ── Когорты ───────────────────────────────────────────────────────
        "cohort_ask_name":              "Как назовём когорту?",
        "cohort_ask_description":       "Добавь описание (или нажми Пропустить):",
        "cohort_ask_max":               "Максимальное количество участников? (Введи число или что угодно для значения по умолчанию — 12):",
        "cohort_ask_type":              "Какой тип когорты?",
        "cohort_created":               "🎉 Когорта создана: <b>{name}</b>\n\nТип: {type}\nМакс. участников: {max}\n\n🔗 Ссылка-приглашение:\n{link}",
        "cohort_list_title":            "👥 Твои когорты:",
        "no_cohorts":                   "Когорт пока нет 😊 Создай первую с помощью /cohort_create.",
        "cohort_list_row":              "• {name} ({count}/{max} участников)",
        "cohort_join_prompt":           "Тебя пригласили в когорту <b>{name}</b>!\n\nНажми кнопку ниже, чтобы подтвердить.",
        "cohort_join_confirm":          "🎉 Добро пожаловать в <b>{name}</b>!",
        "cohort_already_member":        "Ты уже участник этой когорты.",
        "cohort_is_leader":             "Ты являешься ведущим этой когорты.",
        "cohort_invalid_token":         "😕 Эта ссылка недействительна или устарела.",
        "cohort_full":                  "Когорта заполнена — свободных мест нет.",
        "btn_cohort_join":              "✅ Вступить в когорту",
        "btn_cohort_skip_desc":         "⏭ Пропустить",
        "btn_cohort_type_course":       "📚 Курс",
        "btn_cohort_type_group":        "👥 Группа",
        "btn_cohort_type_supervision":  "🔍 Супервизия",

        # ── Сессии когорты ────────────────────────────────────────────────
        "cs_pick_cohort_schedule":  "Для какой когорты запланировать сессию?",
        "cs_pick_cohort_list":      "Сессии какой когорты посмотреть?",
        "cs_ask_session_num":       "Номер сессии?",
        "cs_ask_datetime":          "Дата и время в твоём часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "cs_ask_topic":             "Тема сессии? (или нажми Пропустить):",
        "cs_ask_link":              "Ссылка на сессию? (или нажми Пропустить):",
        "cs_skip":                  "⏭ Пропустить",
        "cs_created":               "✅ Сессия #{num} запланирована!\nКогорта: {cohort}\n📅 {date}\n📋 Тема: {topic}",
        "cs_no_topic":              "—",
        "cs_list_title":            "📅 Сессии — {cohort}:",
        "no_cs":                    "Сессий пока нет. Добавь первую с помощью /cohort_schedule.",
        "cs_row":                   "#{num} — {date} — {topic} [{status}]",
        "cs_status_scheduled":      "запланирована",
        "cs_status_completed":      "завершена",
        "cs_status_cancelled":      "отменена",
        "cs_att_pick_cohort":       "Какую когорту?",
        "cs_att_pick_session":      "Какую сессию?",
        "cs_att_title":             "✅ Посещаемость — Сессия #{num} ({cohort}):",
        "cs_att_no_members":        "В этой когорте пока нет участников.",
        "cs_att_no_sessions":       "Сессий в этой когорте не найдено.",
        "cs_att_saved":             "✅ Сохранено!",
        "cs_reminder_24h":          "🔔 Завтра в {time} — сессия когорты #{num} ({cohort}){link_line}",
        "cs_reminder_1h":           "🔔 Через час в {time} — сессия когорты #{num} ({cohort}){link_line}",
        "cs_reminder_psych_24h":    "🔔 Сессия когорты #{num} ({cohort}) — **завтра в {time}**. Участники уведомлены.{link_line}",
        "cs_reminder_psych_1h":     "🔔 Сессия когорты #{num} ({cohort}) начнётся **через час** ({time}). Участники уведомлены.{link_line}",
        "cs_link_line":             "\n🔗 {link}",

        # ── SESSIONS: список сессий и детальный экран с действиями ──────────
        "cv2_sessions":             "📅 Сессии",
        "cs2_list_title":           "📅 Сессии — «{cohort}» (ближайшие {days} дней):",
        "cs2_list_empty":           "Сессий в ближайшие {days} дней для «{cohort}» нет. Запланируем?",
        "cs2_btn_add_oneoff":       "➕ Разовая сессия",
        "cs2_btn_add_recurring":    "🔁 Настроить повтор",
        "cs2_btn_back_list":        "⬅️ К списку",
        "cs2_not_found":            "Сессия не найдена — возможно, уже удалена.",
        "cs2_detail_header":       "📋 Сессия #{num} — {cohort}",
        "cs2_detail_date":         "📅 {date}",
        "cs2_detail_topic":        "📝 Тема: {topic}",
        "cs2_detail_link":         "🔗 Ссылка: {link}",
        "cs2_detail_recurring":    "🔁 Повторяется: {days}",
        "cs2_detail_paused":       "⏸ На паузе — новые сессии не создаются",
        "cs2_no_link":             "—",
        "cs2_btn_edit_dt":          "✏️ Дата / время",
        "cs2_btn_edit_topic":       "📝 Тема",
        "cs2_btn_edit_link":        "🔗 Ссылка",
        "cs2_btn_delete":           "🗑 Удалить",
        "cs2_btn_pause":            "⏸ Приостановить повтор",
        "cs2_btn_resume":           "▶️ Возобновить повтор",
        "cs2_btn_delete_rule":      "🚫 Удалить правило повтора",
        "cs2_btn_clear":            "🗑 Очистить",
        "cs2_ask_datetime_new":     "Новые дата и время в твоём часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "cs2_ask_topic_new":        "Новая тема — или нажми Очистить, чтобы убрать:",
        "cs2_ask_link_new":         "Новая ссылка — или нажми Очистить, чтобы убрать:",
        "cs2_updated_dt":           "✅ Дата и время обновлены.",
        "cs2_updated_topic":        "✅ Тема обновлена.",
        "cs2_updated_link":         "✅ Ссылка обновлена.",
        "cs2_delete_confirm":       "Удалить сессию #{num} от {date}?\nЗаписи посещаемости тоже будут удалены.",
        "cs2_delete_yes":           "🗑 Да, удалить",
        "cs2_delete_no":            "❌ Отмена",
        "cs2_deleted_ok":           "✅ Сессия #{num} удалена.",
        "cs2_paused_ok":            "⏸ Повтор для «{cohort}» приостановлен. Новые сессии не будут создаваться до возобновления.",
        "cs2_resumed_ok":           "▶️ Повтор для «{cohort}» возобновлён. Сессии продолжат генерироваться.",
        "cs2_delrule_confirm":      "Удалить правило повтора для «{cohort}»?\nУже запланированные сессии останутся, новые создаваться не будут.",
        "cs2_delrule_yes":          "🚫 Удалить правило",
        "cs2_delrule_no":           "❌ Отмена",
        "cs2_delrule_ok":           "✅ Правило повтора для «{cohort}» удалено.",

        # ── RECURRING: повторяющиеся сессии когорты ────────────────────────
        "dow_mon": "Пн", "dow_tue": "Вт", "dow_wed": "Ср", "dow_thu": "Чт",
        "dow_fri": "Пт", "dow_sat": "Сб", "dow_sun": "Вс",
        "cs_recurring_pick_cohort":  "Для какой когорты настроить повторяющуюся сессию?",
        "cs_recurring_ask_days":    "Выбери дни недели, затем нажми Готово:",
        "cs_recurring_days_done":  "✅ Готово",
        "cs_recurring_days_empty": "Выбери хотя бы один день недели.",
        "cs_recurring_ask_time":   "В какое время? (Твой часовой пояс, ЧЧ:ММ):",
        "cs_recurring_created":    "✅ Повторяющаяся сессия настроена!\nКогорта: {cohort}\nДни: {days}\n🕐 {time}\nСессии на ближайшие 30 дней уже запланированы автоматически.",
        "cs_recurring_intro":     "🔁 Настроить повторяющуюся сессию когорты",

        # ── MENU: иерархическая клавиатура ────────────────────────────────
        "btn_menu_individual":   "👤 Индивидуальные",
        "btn_menu_cohorts":      "👥 Мои когорты",
        "btn_menu_summary":      "📊 Сводка",
        "btn_menu_settings":     "⚙️ Настройки",
        "btn_menu_back":         "⬅️ Назад",
        # Подменю «Индивидуальные»
        "btn_ind_add_client":    "➕ Добавить клиента",
        "btn_ind_client_list":   "📋 Список клиентов",
        "btn_ind_new_note":      "📝 Новая заметка",
        "btn_ind_schedule":      "📅 Запланировать сессию",
        "btn_ind_reminders":     "⏰ Напоминания",
        # Подменю «Когорты»
        "btn_coh_create":        "➕ Создать когорту",
        "btn_coh_list":          "📋 Список когорт",
        # Подменю «Сводка»
        "btn_sum_clients":       "👤 Клиенты",
        "btn_sum_cohorts":       "👥 Когорты",
        "btn_sum_stats":         "📈 Статистика",
        # Подменю «Настройки»
        "btn_set_language":      "🌍 Язык",
        "btn_set_timezone":      "🕐 Часовой пояс",
        "btn_set_tariff":        "💰 Тариф",
        "btn_set_notifs":        "🔔 Уведомления",
        # Заголовки разделов
        "section_individual":    "👤 Индивидуальные:",
        "section_cohorts_menu":  "👥 Мои когорты:",
        "section_summary":       "📊 Сводка:",
        "section_settings_menu": "⚙️ Настройки:",

        # ── COHORT_V2: кнопки меню когорты ────────────────────────────────
        "cv2_members":    "👥 Участники",
        "cv2_schedule":   "📅 Сессии",
        "cv2_attendance": "✅ Посещаемость",
        "cv2_checkins":   "📊 Чек-ины",
        "cv2_notes":      "📝 Заметки",
        "cv2_broadcast":  "📢 Рассылка",
        "cv2_stats":      "📊 Статистика",
        "cv2_archive":    "📦 Архивировать",
        "cv2_recurring":  "🔁 Повторяющиеся",
        "cv2_back":       "⬅️ Назад",
        "cohort_action_title": "📋 {name}:",

        # Список участников
        "cv2_members_title":      "👥 Участники «{cohort}» — {count}:",
        "cv2_member_row_tg":      "• {name}  [TG {tg_id}]",
        "cv2_member_row_manual":  "• {name}  👤",
        "cv2_no_members":         "Участников пока нет 😊",
        "cv2_members_empty_note": "Добавь вручную или поделись ссылкой-приглашением — клиенты вступят сами.",
        "cv2_btn_add_member":     "➕ Добавить вручную",
        "cv2_btn_invite":         "🔗 Ссылка-приглашение",
        "cv2_add_member_ask":     "Как зовут нового участника?",
        "cv2_member_added":       "✅ **{name}** добавлен в когорту!",
        "cv2_invite_text":        "🔗 Ссылка-приглашение для «{cohort}»:\n\n{link}\n\nОтправь её клиентам — они нажмут в Telegram и автоматически вступят в группу.",

        # Рассылка
        "cv2_broadcast_ask":        "Напиши сообщение для {count} участников «{cohort}»:",
        "cv2_broadcast_preview":    "📣 Предпросмотр:\n\n{text}\n\nОтправить {count} участникам?",
        "cv2_broadcast_send":       "✅ Отправить",
        "cv2_broadcast_cancel":     "❌ Отмена",
        "cv2_broadcast_done":       "✅ Отправлено {sent} из {total} участников.",
        "cv2_broadcast_no_members": "Нет активных участников для рассылки.",

        # Архивация
        "cv2_archive_confirm":  "Архивировать когорту «{cohort}»?\nНапоминания для всех участников будут отключены.",
        "cv2_archive_yes":      "📦 Архивировать",
        "cv2_archive_no":       "❌ Отмена",
        "cv2_archived_ok":      "✅ Когорта «{cohort}» успешно архивирована.",
        "cv2_already_archived": "Эта когорта уже в архиве.",

        # Статистика
        "cv2_stats_title":          "📊 Статистика — {cohort}:",
        "cv2_stats_members":        "👥 Участников: {count}",
        "cv2_stats_sessions":       "📅 Сессий: {total} ({completed} завершено)",
        "cv2_stats_attendance_pct": "📋 Средняя посещаемость: {pct}%",
        "cv2_stats_checkins":       "💬 Ответов на чек-ины: {count}",
        "cv2_stats_avg_score":      "📊 Средний балл: {avg}/10",

        # Чек-ины
        "cv2_checkin_options_title": "💬 Чек-ины для «{cohort}»:",
        "cv2_checkin_btn_setup":     "⚙️ Настроить авточек-ин",
        "cv2_checkin_btn_summary":   "📊 Посмотреть ответы",
        "cv2_checkin_btn_send_now":  "📤 Отправить сейчас",
        "cv2_checkin_ask_question":  "Какой вопрос отправить всем участникам?",
        "cv2_checkin_ask_interval":  "Как часто (в часах) отправлять? (например, 24 — ежедневно):",
        "cv2_checkin_saved":         "✅ Авточек-ин настроен!\nВопрос: {q}\nПериодичность: каждые {h}ч",
        "cv2_checkin_sent":          "✅ Чек-ин отправлен {count} участникам.",
        "cv2_checkin_summary_title": "📊 Сводка чек-инов — {cohort}:",
        "cv2_checkin_row":           "• {name}: {count} ответ(ов), средний балл {avg}/10",
        "cv2_no_checkin_data":       "Данных чек-инов пока нет.",
        "cv2_checkin_member_thanks": "💙 Ответ сохранён — спасибо!",

        # Заметки по сессии
        "cv2_notes_pick_session": "К какой сессии добавить или посмотреть заметки?",
        "cv2_notes_title":        "📝 Заметки — Сессия #{num}:",
        "cv2_note_row":           "📝 {text}",
        "cv2_soap_row":           "📋 SOAP:\n{text}",
        "cv2_notes_empty":        "Для этой сессии заметок пока нет. Добавим первую?",
        "cv2_note_btn_add":       "➕ Добавить заметку",
        "cv2_note_btn_soap":      "📋 SOAP-заметка",
        "cv2_note_ask":           "Напиши заметку для Сессии #{num}:",
        "cv2_note_saved":         "✅ Заметка сохранена!",
        "cv2_soap_s":             "SOAP — Сессия #{num}.\n\n*S — Субъективное:* Слова клиента, настроение, жалобы:",
        "cv2_soap_o":             "*O — Объективное:* Твои наблюдения, поведение, тесты:",
        "cv2_soap_a":             "*A — Оценка:* Клиническое впечатление, гипотеза:",
        "cv2_soap_p":             "*P — План:* Следующие шаги, задание, фокус:",
        "cv2_soap_saved":         "✅ SOAP-заметка для Сессии #{num} сохранена.",

        # Уведомления (заглушка)
        "notifs_not_implemented": "🔔 Настройки уведомлений появятся в ближайшем обновлении — следи за новостями!",

        # ── INDIVIDUAL_SESSION: управление сессиями клиента ────────────────
        "btn_client_sessions":    "📅 Сессии",
        "is_sessions_title":      "📅 Сессии — {client}:",
        "is_sessions_empty":      "Предстоящих сессий для {client} нет. Запланируем?",
        "is_btn_add_oneoff":      "➕ Разовая сессия",
        "is_btn_add_recurring":   "🔁 Настроить повтор",
        "is_btn_back_list":       "⬅️ К списку",
        "is_not_found":           "Сессия не найдена — возможно, уже удалена.",
        "is_detail_header":       "📋 {client}",
        "is_detail_date":         "📅 {date}",
        "is_detail_topic":        "📝 Тема: {topic}",
        "is_detail_link":         "🔗 Ссылка: {link}",
        "is_detail_recurring":    "🔁 Повтор: {days}",
        "is_detail_paused":       "⏸ Повтор приостановлен",
        "is_btn_edit_dt":         "✏️ Дата / время",
        "is_btn_edit_topic":      "📝 Тема",
        "is_btn_edit_link":       "🔗 Ссылка",
        "is_btn_delete":          "🗑 Удалить",
        "is_btn_pause":           "⏸ Приостановить повтор",
        "is_btn_resume":          "▶️ Возобновить повтор",
        "is_btn_delete_rule":     "🚫 Удалить правило повтора",
        "is_btn_clear":           "🗑 Очистить",
        "is_ask_datetime":        "Дата и время в твоём часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "is_ask_datetime_new":    "Новые дата и время (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "is_ask_topic_new":       "Новая тема (или пропусти):",
        "is_ask_link_new":        "Новая ссылка (или пропусти / очисти):",
        "is_updated_dt":          "✅ Дата и время обновлены.",
        "is_updated_topic":       "✅ Тема обновлена.",
        "is_updated_link":        "✅ Ссылка обновлена.",
        "is_delete_confirm":      "Удалить сессию {date}?",
        "is_delete_yes":          "🗑 Да, удалить",
        "is_delete_no":           "❌ Отмена",
        "is_deleted_ok":          "✅ Сессия удалена.",
        "is_paused_ok":           "⏸ Повтор для {client} приостановлен.",
        "is_resumed_ok":          "▶️ Повтор для {client} возобновлён.",
        "is_delrule_confirm":     "Удалить правило повтора для {client}?\nУже запланированные сессии останутся, новые создаваться не будут.",
        "is_delrule_yes":         "🚫 Удалить правило",
        "is_delrule_no":          "❌ Отмена",
        "is_delrule_ok":          "✅ Правило повтора удалено.",
        "is_recurring_ask_days":  "Выбери дни недели, затем нажми Готово:",
        "is_recurring_days_empty":"Выбери хотя бы один день недели.",
        "is_recurring_ask_time":  "В какое время? (Твой часовой пояс, ЧЧ:ММ):",
        "is_recurring_created":   "✅ Повтор настроен!\nКлиент: {client}\nДни: {days}\n🕐 {time}\nСессии на ближайшие 30 дней уже запланированы автоматически.",
        "is_session_created":     "📅 Сессия для **{client}** запланирована на {date}. Напомню вам обоим заранее!",
        "err_invalid_datetime":   "Формат не распознан. Используй ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-03-15 14:30).",
        "err_invalid_time":       "Формат не распознан. Используй ЧЧ:ММ (например, 14:30).",

        # Супервизия
        "sup_case_alias":       "Введи псевдоним клиента (без реального имени):",
        "sup_case_issue":       "С каким запросом пришёл клиент?",
        "sup_case_hypothesis":  "Какова твоя рабочая гипотеза?",
        "sup_case_intervention":"Какую интервенцию использовал(а) или планируешь?",
        "sup_case_outcome":     "Какой ожидаемый или наблюдаемый результат?",
        "sup_case_saved":       "✅ Случай супервизии сохранён: **{alias}**",
        "sup_logbook_title":    "📓 Журнал супервизии — {count} случай(ев):",
        "sup_logbook_row":      "#{id} {alias} [{status}] — {date}",
        "sup_logbook_empty":    "Случаев супервизии пока нет. Добавь первый с помощью /supervision_case.",
        "sup_progress_title":   "📂 Открытые случаи супервизии:",
        "sup_progress_row":     "#{id} **{alias}**\nЗапрос: {issue}\nГипотеза: {hyp}\nИнтервенция: {interv}\nРезультат: {outcome}",
        "sup_progress_empty":   "Открытых случаев нет — всё завершено 🎉",
        "sup_close_btn":        "✅ Закрыть случай",
        "sup_case_closed":      "✅ Случай #{id} закрыт.",
        "sup_case_not_found":   "Случай не найден.",

        # ── Экран тарифа ───────────────────────────────────────────────────
        "tariff_screen_start": (
            "📦 Ваш тариф: *Start* (бесплатно)\n\n"
            "Что включено:\n"
            "• До 5 индивидуальных клиентов\n"
            "• До 2 групп/когорт\n"
            "• До 15 участников в когорте\n"
            "• Чек-ины и напоминания\n"
            "• Аналитика за последние 30 дней\n"
            "• ❌ Экспорт\n"
            "• ❌ Журнал супервизии\n\n"
            "✨ Перейдите на Pro и работайте без ограничений."
        ),
        "tariff_screen_pro": (
            "💎 Ваш тариф: *Pro*{expires}\n\n"
            "Всё из Start, плюс:\n"
            "• Неограниченное количество клиентов\n"
            "• До 10 когорт\n"
            "• До 50 участников в когорте\n"
            "• Полная история аналитики\n"
            "• ✅ Экспорт заметок и сессий\n"
            "• ✅ Журнал супервизии\n\n"
            "Спасибо, что поддерживаете проект! 🙌"
        ),
        "tariff_compare": (
            "📊 *Сравнение тарифов*\n\n"
            "┌──────────────────┬────────┬──────┐\n"
            "│ Функция          │ Start  │  Pro │\n"
            "├──────────────────┼────────┼──────┤\n"
            "│ Клиенты          │  5     │  ∞   │\n"
            "│ Когорты          │  2     │  10  │\n"
            "│ Участников/когор.│  15    │  50  │\n"
            "│ Аналитика        │ 30 дн  │  ∞   │\n"
            "│ Экспорт          │  ❌    │  ✅  │\n"
            "│ Супервизия       │  ❌    │  ✅  │\n"
            "│ Чек-ины          │  ✅    │  ✅  │\n"
            "└──────────────────┴────────┴──────┘\n\n"
            "Для активации Pro введите промокод: /promo"
        ),
        "tariff_howto": (
            "❓ *Как это работает?*\n\n"
            "У Прохора два тарифа:\n\n"
            "🟢 *Start* — бесплатный, навсегда. Отлично подходит для старта "
            "и работы с небольшой базой клиентов.\n\n"
            "💎 *Pro* — активируется по промокоду. Снимает все ограничения, "
            "открывает экспорт и журнал супервизии.\n\n"
            "Чтобы получить промокод, обратитесь к администратору "
            "или загляните в основной канал бота.\n\n"
            "Ввести промокод: /promo"
        ),
        "tariff_history_empty": (
            "📜 Изменений тарифа пока нет.\n\n"
            "Ваш текущий тариф: *{plan}*"
        ),
        "tariff_already_pro": "💎 Вы уже на тарифе Pro — работайте без ограничений!",
        # Reminder sent the day before a paid plan expires (notify_expiring_plans)
        "plan_expiring_tomorrow": "⏰ Напоминание: завтра истекает ваш тариф {plan} ({date}). Введите /promo для продления.",
        "btn_tariff_upgrade":  "💎 Перейти на PRO",
        "btn_tariff_compare":  "📊 Сравнить тарифы",
        "btn_tariff_history":  "📜 История платежей",
        "btn_tariff_howto":    "❓ Как это работает?",
        "btn_tariff_back":     "⬅️ Назад",

        # ── Самозапись: настройки психолога ───────────────────────────────
        "btn_set_booking":           "📅 Запись клиентов",
        "section_booking":           "📅 Запись клиентов",
        "booking_pro_only":          "⚠️ Самозапись клиентов доступна только на тарифе Pro.\nВведите промокод: /promo",
        "booking_no_profile":        "Профиль для записи ещё не настроен.",
        "btn_booking_setup":         "🛠 Настроить профиль",
        "ask_booking_display_name":  "👤 Как будет называться ваша страница записи?\n(укажите имя или профессиональный псевдоним):",
        "ask_booking_bio":           "📝 Напишите краткое описание для клиентов (до 300 символов).\nОно отображается на странице записи:",
        "booking_bio_too_long":      "⚠️ Описание слишком длинное ({length} симв.). Пожалуйста, уложитесь в 300 символов:",
        "ask_booking_timezone":      "🕐 Выберите рабочий часовой пояс — слоты будут генерироваться в нём:",
        "booking_profile_saved":     "✅ Профиль создан! Теперь настройте еженедельное расписание.",
        "booking_profile_card":      (
            "📅 *Профиль записи*\n\n"
            "👤 Имя: {display_name}\n"
            "📝 Описание: {bio}\n"
            "🔗 Slug: `{slug}`\n"
            "🕐 Часовой пояс: {timezone}\n"
            "Статус: {status}\n\n"
            "Ссылка для записи:\n`{link}`"
        ),
        "booking_enabled_on":        "🟢 Принимаю записи",
        "booking_enabled_off":       "🔴 Запись приостановлена",
        "booking_toggled_on":        "✅ Запись включена — клиенты могут записываться.",
        "booking_toggled_off":       "❌ Запись приостановлена — ссылка показывает «запись недоступна».",
        "btn_booking_toggle_on":     "▶️ Включить запись",
        "btn_booking_toggle_off":    "⏸ Приостановить запись",
        "btn_booking_schedule":      "📋 Расписание",
        "btn_booking_exceptions":    "🚫 Блокировки дат",
        "btn_booking_link":          "🔗 Ссылка записи",
        "btn_booking_edit_name":     "✏️ Изменить имя",
        "btn_booking_edit_bio":      "✏️ Изменить описание",
        "btn_booking_edit_tz":       "🕐 Изменить часовой пояс",
        "booking_link_msg":          "🔗 Ваша ссылка для записи:\n\n`{link}`\n\nПоделитесь ею с клиентами, чтобы они могли записываться.",
        "booking_schedule_title":    "📋 *Еженедельное расписание*\n\nНажмите на день для настройки:",
        "booking_day_configured":    "✅ {day}: {start}–{end} ({duration} мин + {buffer} мин перерыв)",
        "booking_day_none":          "➖ {day}: не настроен",
        "ask_booking_day_start":     "⏰ *{day}*\nВведите время начала приёма (ЧЧ:ММ, например 10:00):",
        "ask_booking_day_end":       "Введите время окончания (ЧЧ:ММ, например 18:00):",
        "ask_booking_day_duration":  "Введите длительность сессии в минутах (например 50):",
        "ask_booking_day_buffer":    "Введите перерыв между сессиями в минутах (0 — без перерыва):",
        "booking_day_saved":         "✅ Расписание для {day} сохранено.",
        "booking_day_removed":       "🗑 Расписание для {day} удалено.",
        "booking_invalid_time":      "⚠️ Неверный формат. Введите как ЧЧ:ММ (например 10:00):",
        "booking_invalid_number":    "⚠️ Введите целое число:",
        "booking_time_order":        "⚠️ Время окончания должно быть позже начала. Введите время окончания заново:",
        "btn_booking_remove_day":    "🗑 Убрать этот день",
        "booking_exceptions_title":  "🚫 *Блокировки дат*\n\n{items}",
        "booking_no_exceptions":     "Блокировок нет.",
        "booking_exception_row":     "• {date} {time_range}",
        "booking_exception_whole_day": "(весь день)",
        "ask_booking_ex_date":       "Введите дату блокировки (ДД.ММ.ГГГГ или ГГГГ-ММ-ДД):",
        "ask_booking_ex_start":      "Введите время начала блокировки (ЧЧ:ММ) или нажмите «Весь день»:",
        "ask_booking_ex_end":        "Введите время окончания блокировки (ЧЧ:ММ):",
        "booking_ex_saved":          "✅ Дата заблокирована: {date}.",
        "booking_invalid_date":      "⚠️ Неверная дата. Введите как ДД.ММ.ГГГГ или ГГГГ-ММ-ДД:",
        "btn_booking_add_exception": "➕ Добавить блокировку",
        "btn_booking_whole_day":     "🚫 Весь день",
        "btn_booking_del_ex":        "🗑 Удалить",

        # ── Самозапись: клиентская сторона ────────────────────────────────
        "booking_card_text":         "👤 *{display_name}*\n\n{bio}",
        "btn_booking_book":          "📅 Записаться",
        "booking_unavailable":       "⚠️ Специалист временно не принимает записи. Попробуйте позже.",
        "booking_profile_not_found": "😕 Страница записи не найдена. Ссылка могла устареть.",
        "ask_client_tz_booking":     "🕐 Укажите ваш часовой пояс — чтобы показать доступные слоты в вашем времени:",
        "booking_no_slots":          "😕 Свободных слотов на ближайшие 14 дней нет. Загляните позже.",
        "booking_dates_title":       "📅 Выберите дату:",
        "booking_slots_title":       "🕐 Слоты на {date} (ваше время):",
        "booking_confirm_text":      "✅ *Подтверждение записи*\n\n📅 {datetime} (ваше время)\n👤 {name}\n\nЗаписаться?",
        "btn_booking_confirm":       "✅ Подтвердить",
        "btn_booking_back_dates":    "⬅️ Другая дата",
        "btn_booking_back_slots":    "⬅️ Другое время",
        "booking_success":           "🎉 Запись подтверждена!\n\n📅 *{datetime}* (ваше время)\n👤 {name}\n\nНапомню за 24ч и за 1ч до сессии.",
        "booking_slot_taken":        "⚠️ Этот слот только что заняли. Выберите другое время.",
        "booking_error":             "⚠️ Что-то пошло не так. Попробуйте ещё раз.",
        "booking_psych_notify":      (
            "📅 *Новая самозапись!*\n\n"
            "Клиент: {client}\n"
            "Дата: {datetime} (ваше время)\n\n"
            "ℹ️ Клиент записался самостоятельно через ссылку самозаписи."
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Return translated string for the given language and key.
    Falls back to English if the key or language is not found."""
    text = TEXTS.get(lang, TEXTS["en"]).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
