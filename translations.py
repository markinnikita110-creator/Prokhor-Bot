TEXTS = {
    "en": {
        # ── Psychologist welcome ───────────────────────────────────────────
        "welcome": "Prokhor is online. I will remember your clients and session notes.",
        "language_select": "Select language:",
        "language_saved": "Language saved.",

        # ── Client management ─────────────────────────────────────────────
        "client_added": "Client added: {name}",
        "client_not_found": "No client found: {name}",
        "no_clients": "No clients yet.",
        "clients_title": "Clients:",
        "clients_status_title": "Client status:",
        "connected": "connected",
        "not_connected": "not connected",
        "client_archived": "Client {name} archived.",
        "client_already_archived": "Client {name} is already archived.",
        "client_unarchived": "Client {name} restored to active list.",
        "client_not_archived": "Client {name} is not archived.",
        "archived_title": "Archived clients:",
        "no_archived": "No archived clients.",

        # ── Notes ─────────────────────────────────────────────────────────
        "note_saved": "Note saved for {client}.",
        "notes_title": "Notes for {client}:",
        "no_notes": "No notes yet for {client}.",
        "summary_text": "Client: {client}\nNotes: {count}",
        "summary_last": "\nLast update:\n{last}",
        "soap_saved": "SOAP note saved for {client}:\n\n{text}",
        "soap_s": "Starting SOAP note for {client}.\n\nS — Subjective (client's own words, complaints, mood):",
        "soap_o": "O — Objective (your observations, behavior, test results):",
        "soap_a": "A — Assessment (your clinical impression, hypothesis):",
        "soap_p": "P — Plan (next steps, homework, next session focus):",

        # ── Check-ins ─────────────────────────────────────────────────────
        "checkin_saved": "Check-in saved for {client}: {score}/10",
        "checkins_title": "Check-ins for {client}:",
        "no_checkins": "No check-ins yet for {client}.",
        "checkin_request_sent": "Check-in request sent to {client}.",
        "auto_checkin_enabled": "Auto check-in enabled for {client} every {interval} minutes.",
        "no_auto_checkins": "No auto check-ins configured.",
        "auto_checkins_done": "Auto check-ins executed for {count} client(s).",

        # ── Engagement ────────────────────────────────────────────────────
        "engagement_text": "Client: {client}\nNotes: {notes}\nCheck-ins: {checkins}\nAverage score: {avg}\n\n{label}",
        "good_stability": "Good stability",
        "moderate": "Moderate fluctuations",
        "risk_zone": "Risk zone",
        "no_checkin_data": "No check-in data",
        "flag_risk": "⚠ Risk zone detected: low emotional stability trend",
        "flag_negative": "⚠ Negative trend detected",

        # ── Reminders ─────────────────────────────────────────────────────
        "reminder_set": "Reminder set for {client} in {minutes} minutes.",
        "no_reminders": "No reminders set.",
        "reminders_title": "Reminders:",

        # ── Sessions ──────────────────────────────────────────────────────
        "session_scheduled": "Session scheduled with {client} on {date} ({tz_info}).\nYou will be reminded 24h and 1h before.",
        "tz_info": "your time, {offset}",
        "timezone_usage": "Current timezone: {current}\n\nSet with:\n/timezone +3\n/timezone -5\n/timezone +05:30\n/timezone Europe/Moscow",
        "timezone_invalid": "⚠️ Unknown timezone. Examples:\n/timezone +3\n/timezone Europe/Moscow\n/timezone -05:30",
        "timezone_saved": "✅ Timezone set: {tz} ({offset}).",
        "onboarding_welcome": "👋 Welcome to Prokhor!\n\nFirst, choose your language:",
        "ask_timezone_onboarding": (
            "🕐 Almost done! Select your timezone so session times are shown correctly:"
        ),
        "ask_timezone_settings": "🕐 Select your timezone:",
        "ask_timezone_custom": (
            "Enter your timezone:\n\nExamples:\n"
            "  +3   -5   +05:30\n"
            "  Europe/Moscow   America/New_York"
        ),
        "btn_tz_custom": "✏️ Enter manually",
        "btn_skip":      "⏭ Skip for now",
        "btn_timezone":  "🕐 Timezone",
        "tz_skipped": "Timezone set to UTC by default. Change it any time in ⚙️ Settings.",
        "sessions_title": "Upcoming sessions:",
        "no_sessions": "No upcoming sessions.",
        "session_row": "#{id} | {client} | {date}",
        "session_cancelled": "Session #{id} cancelled.",
        "session_not_found": "Session not found.",
        "session_rescheduled": "Session #{id} rescheduled to {date}.",
        "session_cancelled_notify": "⚠ Your session on {date} has been cancelled.",
        "session_rescheduled_notify": "🔄 Your session has been rescheduled to {date}.",
        "reminder_psych_24h": "🔔 Reminder: session with {client} tomorrow at {time}.",
        "reminder_psych_1h": "🔔 Reminder: session with {client} in 1 hour at {time}.",
        "reminder_client_24h": "⏰ Reminder:\nTomorrow at {time} you have a session with your specialist.",
        "reminder_client_1h": "⏰ Reminder:\nYour session starts in 1 hour (at {time}).",
        "session_link_line": "\nSession link:\n{link}",

        # ── Dashboard ─────────────────────────────────────────────────────
        "dashboard_title": "Dashboard:",
        "dashboard_row": "Client: {name}\nNotes: {notes} | Check-ins: {checkins} | Avg: {avg}\nStatus: {status}",
        "no_data": "No data",

        # ── Homework ──────────────────────────────────────────────────────
        "homework_sent": "Homework sent to {client}.",
        "homework_saved_offline": "Homework saved for {client} (client not yet connected).",
        "homeworks_title": "Homework for {client}:",
        "no_homework": "No homework for {client} yet.",
        "new_homework_client": "📚 New homework from your specialist:\n\n{text}",

        # ── Invite ────────────────────────────────────────────────────────
        "invite_link": "Invite link for {client}:\n{link}",
        "invite_invalid": "Invalid or expired invite link.",
        "client_info": "Client: {client}\nConnected: {connected}\n{tg_line}",
        "tg_id_line": "Telegram ID: {tid}",
        "tg_not_connected": "Telegram ID: not connected",

        # ── Timeline ──────────────────────────────────────────────────────
        "timeline_title": "Timeline for {client}:",
        "no_timeline": "No history yet.",
        "timeline_note": "📝 Note: {text}",
        "timeline_checkin": "📊 Check-in: {score}/10",
        "timeline_homework": "📚 Homework: {text}",
        "timeline_session": "📅 Session",

        # ── Alerts ────────────────────────────────────────────────────────
        "alerts_title": "Alerts:",
        "no_alerts": "No alerts. Everything looks good.",
        "alert_low_score": "⚠ {client}: average score below 4",
        "alert_no_checkin": "⚠ {client}: no check-ins for 10+ days",
        "alert_no_session": "⚠ {client}: no sessions for 30+ days",

        # ── Tags ──────────────────────────────────────────────────────────
        "tag_added": "Tag '{tag}' added to {client}.",
        "find_title": "Clients with tag '{tag}':",
        "no_clients_tag": "No clients found with tag '{tag}'.",

        # ── Export ────────────────────────────────────────────────────────
        "export_filename": "export_{client}.txt",

        # ── Client-side ───────────────────────────────────────────────────
        "client_connected": "You are now connected to {specialist}.\n\nAvailable commands:\n/my_homeworks — your homework list\n/checkin_history — your last check-ins",
        "client_menu": "Welcome to Prokhor.\n\nAvailable commands:\n/my_homeworks — your homework list\n/checkin_history — your last check-ins",
        "not_a_client": "You are not connected as a client. Use your invite link to connect.",
        "checkin_question": "How are you feeling today?",
        "checkin_thanks": "Thank you. Your response has been recorded.",
        "checkin_submitted": "Client {client} submitted a check-in: {score}/10",
        "my_homeworks_title": "Your homework:",
        "no_my_homeworks": "No homework assigned yet.",
        "my_checkins_title": "Your recent check-ins:",
        "no_my_checkins": "No check-ins recorded yet.",
        "client_not_connected_tg": "Client is not connected to Telegram yet.",

        # ── Dual role / self-invite protection ────────────────────────────
        "self_invite_error": "⚠️ You cannot use your own invite link.",
        "dual_role_select": "You have two roles. Which interface would you like to open?",
        "btn_role_psychologist": "🧠 Psychologist interface",
        "btn_role_client": "👤 My client profile",
        "switch_no_dual_role": "You have only one role. Use /start to open your interface.",
        "client_role_reset": "Your client profile has been disconnected. Psychologist mode active.",
        "client_role_not_found": "No active client profile found to disconnect.",

        # ── Errors / usage ────────────────────────────────────────────────
        "score_invalid": "Score must be an integer between 1 and 10.",
        "minutes_invalid": "Minutes must be a positive integer.",
        "interval_invalid": "Interval must be a positive integer.",
        "date_invalid": "Invalid date format. Use: YYYY-MM-DD HH:MM",
        "id_invalid": "Session ID must be a positive integer.",

        # ── Main menu button labels ───────────────────────────────────────
        "btn_clients":   "👤 Clients",
        "btn_sessions":  "📅 Sessions",
        "btn_homework":  "📚 Homework",
        "btn_analytics": "📊 Analytics",
        "btn_checkins":  "🔔 Check-ins",
        "btn_settings":  "⚙️ Settings",

        # ── Navigation ────────────────────────────────────────────────────
        "btn_back":      "⬅ Back",
        "btn_main_menu": "🏠 Main Menu",
        "btn_prev":      "⬅ Prev",
        "btn_next":      "Next ➡",
        "btn_cancel":    "✖ Cancel",

        # ── Section sub-buttons ───────────────────────────────────────────
        "btn_add_client":       "➕ Add Client",
        "btn_client_list":      "📋 Client List",
        "btn_invite_client":    "🔗 Invite Client",
        "btn_archived_clients": "🗄 Archived",
        "btn_schedule_session": "➕ Schedule Session",
        "btn_upcoming_sessions":"📋 Upcoming Sessions",
        "btn_assign_homework":  "➕ Assign Homework",
        "btn_active_homework":  "📋 Active Homework",
        "btn_dashboard":        "📈 Dashboard",
        "btn_alerts":           "⚠ Alerts",
        "btn_send_checkin":     "➕ Send Check-in",
        "btn_auto_checkins":    "⚙ Auto Check-ins",
        "btn_recent_checkins":  "📋 Recent Check-ins",
        "btn_language":         "🌍 Language",
        "btn_about":            "ℹ About",

        # ── Client card action buttons ────────────────────────────────────
        "btn_add_note":      "📝 Note",
        "btn_soap_note":     "📄 SOAP",
        "btn_assign_hw":     "📚 Homework",
        "btn_send_ci":       "💬 Check-in",
        "btn_sched_session": "📅 Session",
        "btn_timeline":      "📈 Timeline",
        "btn_tags":          "🏷 Tags",
        "btn_engagement":    "📊 Engagement",
        "btn_export":        "📤 Export",
        "btn_archive":       "🗄 Archive",
        "btn_unarchive":     "♻️ Restore",
        "btn_invite_link":   "🔗 Invite Link",

        # ── Session card buttons ──────────────────────────────────────────
        "btn_reschedule":    "✏ Reschedule",
        "btn_cancel_session":"❌ Cancel",

        # ── Section titles ────────────────────────────────────────────────
        "section_clients":   "👤 Clients",
        "section_sessions":  "📅 Sessions",
        "section_homework":  "📚 Homework",
        "section_analytics": "📊 Analytics",
        "section_checkins":  "🔔 Check-ins",
        "section_settings":  "⚙️ Settings",

        # ── FSM prompts ───────────────────────────────────────────────────
        "ask_client_name":       "What is the client's name?",
        "ask_note_text":         "Enter note text:",
        "ask_homework_text":     "Enter homework assignment:",
        "ask_session_datetime":  "Enter date and time in your local timezone (YYYY-MM-DD HH:MM):",
        "ask_reschedule_datetime":"Enter new date and time in your local timezone (YYYY-MM-DD HH:MM):",
        "ask_tag":               "Enter tag:",
        "ask_checkin_client":    "Enter client name to send check-in:",
        "ask_auto_client":       "Enter client name:",
        "ask_auto_interval":     "Enter interval in minutes:",
        "fsm_cancelled":         "Cancelled.",

        # ── Client card ───────────────────────────────────────────────────
        "client_card":    "👤 {name}\n\nNotes: {notes} | Check-ins: {checkins} | Avg: {avg}\nNext session: {session}",
        "no_next_session":"None",
        "page_indicator": "{page}/{total}",

        # ── Homework list ─────────────────────────────────────────────────
        "homework_list_title": "Active homework:",
        "no_active_homework":  "No active homework.",

        # ── Check-in recent ───────────────────────────────────────────────
        "recent_checkins_title": "Recent check-ins (last 10):",
        "no_recent_checkins":    "No check-ins yet.",

        # ── About ─────────────────────────────────────────────────────────
        "about_text": "🤖 Prokhor — assistant for psychologists and coaches.\n\nVersion 2.0\n\nFeatures: clients, sessions, homework, notes, SOAP, analytics, export, localization.",

        # ── Cohorts ───────────────────────────────────────────────────────
        "cohort_ask_name":              "Enter a name for the cohort:",
        "cohort_ask_description":       "Enter a description (or press Skip):",
        "cohort_ask_max":               "Max number of participants (enter a number or send anything to use the default of 12):",
        "cohort_ask_type":              "Select cohort type:",
        "cohort_created":               "✅ Cohort created: <b>{name}</b>\n\nType: {type}\nMax participants: {max}\n\nInvite link:\n{link}",
        "cohort_list_title":            "Your cohorts:",
        "no_cohorts":                   "No cohorts yet. Use /cohort_create to add one.",
        "cohort_list_row":              "• {name} ({count}/{max} participants)",
        "cohort_join_prompt":           "You are invited to join the cohort <b>{name}</b>.\n\nPress the button below to confirm.",
        "cohort_join_confirm":          "✅ You have joined the cohort <b>{name}</b>!",
        "cohort_already_member":        "You are already a member of this cohort.",
        "cohort_is_leader":             "You are the leader of this cohort.",
        "cohort_invalid_token":         "Invalid or expired cohort invite link.",
        "cohort_full":                  "This cohort is full.",
        "btn_cohort_join":              "✅ Join cohort",
        "btn_cohort_skip_desc":         "⏭ Skip",
        "btn_cohort_type_course":       "📚 Course",
        "btn_cohort_type_group":        "👥 Group",
        "btn_cohort_type_supervision":  "🔍 Supervision",

        # ── Cohort sessions ───────────────────────────────────────────────
        "cs_pick_cohort_schedule":  "Select a cohort to schedule a session for:",
        "cs_pick_cohort_list":      "Select a cohort to view sessions:",
        "cs_ask_session_num":       "Enter session number:",
        "cs_ask_datetime":          "Enter date and time in your local timezone (YYYY-MM-DD HH:MM):",
        "cs_ask_topic":             "Enter session topic (or press Skip):",
        "cs_ask_link":              "Enter session link (or press Skip):",
        "cs_skip":                  "⏭ Skip",
        "cs_created":               "✅ Session #{num} scheduled\nCohort: {cohort}\n📅 {date}\n📋 Topic: {topic}",
        "cs_no_topic":              "—",
        "cs_list_title":            "Sessions — {cohort}:",
        "no_cs":                    "No sessions scheduled yet. Use /cohort_schedule to add one.",
        "cs_row":                   "#{num} — {date} — {topic} [{status}]",
        "cs_status_scheduled":      "scheduled",
        "cs_status_completed":      "completed",
        "cs_status_cancelled":      "cancelled",
        "cs_att_pick_cohort":       "Select a cohort:",
        "cs_att_pick_session":      "Select a session:",
        "cs_att_title":             "Attendance — Session #{num} ({cohort}):",
        "cs_att_no_members":        "No members in this cohort yet.",
        "cs_att_no_sessions":       "No sessions found for this cohort.",
        "cs_att_saved":             "✅ Saved.",
        "cs_reminder_24h":          "🔔 Tomorrow at {time} — cohort session #{num} ({cohort}){link_line}",
        "cs_reminder_1h":           "🔔 In 1 hour at {time} — cohort session #{num} ({cohort}){link_line}",
        "cs_reminder_psych_24h":    "🔔 Cohort session #{num} ({cohort}) — tomorrow at {time}. Members notified.{link_line}",
        "cs_reminder_psych_1h":     "🔔 Cohort session #{num} ({cohort}) — in 1 hour at {time}. Members notified.{link_line}",
        "cs_link_line":             "\n🔗 {link}",

        # ── SESSIONS: browsable session list + detail/action view ──────────
        "cv2_sessions":             "📅 Sessions",
        "cs2_list_title":           "📅 Sessions — «{cohort}» (next {days} days):",
        "cs2_list_empty":           "No sessions in the next {days} days for «{cohort}».",
        "cs2_btn_add_oneoff":       "➕ One-off session",
        "cs2_btn_add_recurring":    "🔁 Set up recurring",
        "cs2_btn_back_list":        "⬅️ Back to list",
        "cs2_not_found":            "Session not found or already removed.",
        "cs2_detail_header":       "📋 Session #{num} — {cohort}",
        "cs2_detail_date":         "📅 {date}",
        "cs2_detail_topic":        "📝 Topic: {topic}",
        "cs2_detail_link":         "🔗 Link: {link}",
        "cs2_detail_recurring":    "🔁 Recurring: {days}",
        "cs2_detail_paused":       "⏸ Paused — no new sessions being generated",
        "cs2_no_link":             "—",
        "cs2_btn_edit_dt":          "✏️ Date/time",
        "cs2_btn_edit_topic":       "📝 Topic",
        "cs2_btn_edit_link":        "🔗 Link",
        "cs2_btn_delete":           "🗑 Delete",
        "cs2_btn_pause":            "⏸ Pause recurrence",
        "cs2_btn_resume":           "▶️ Resume recurrence",
        "cs2_btn_delete_rule":      "🚫 Delete recurrence rule",
        "cs2_btn_clear":            "🗑 Clear",
        "cs2_ask_datetime_new":     "Enter new date and time in your local timezone (YYYY-MM-DD HH:MM):",
        "cs2_ask_topic_new":        "Enter new topic (or press Clear to remove it):",
        "cs2_ask_link_new":         "Enter new link (or press Clear to remove it):",
        "cs2_updated_dt":           "✅ Date/time updated.",
        "cs2_updated_topic":        "✅ Topic updated.",
        "cs2_updated_link":         "✅ Link updated.",
        "cs2_delete_confirm":       "Delete session #{num} on {date}?\nIts attendance records will also be removed.",
        "cs2_delete_yes":           "🗑 Delete",
        "cs2_delete_no":            "❌ Cancel",
        "cs2_deleted_ok":           "✅ Session #{num} deleted.",
        "cs2_paused_ok":            "⏸ Recurrence paused for «{cohort}». No new sessions will be generated until resumed.",
        "cs2_resumed_ok":           "▶️ Recurrence resumed for «{cohort}».",
        "cs2_delrule_confirm":      "Delete the recurrence rule for «{cohort}»?\nAlready scheduled sessions will stay, but no new ones will be generated.",
        "cs2_delrule_yes":          "🚫 Delete rule",
        "cs2_delrule_no":           "❌ Cancel",
        "cs2_delrule_ok":           "✅ Recurrence rule deleted for «{cohort}».",

        # ── RECURRING: recurring cohort sessions ───────────────────────────
        "dow_mon": "Mon", "dow_tue": "Tue", "dow_wed": "Wed", "dow_thu": "Thu",
        "dow_fri": "Fri", "dow_sat": "Sat", "dow_sun": "Sun",
        "cs_recurring_pick_cohort":  "Select a cohort for the recurring session:",
        "cs_recurring_ask_days":    "Pick the weekdays this session repeats on, then press Done:",
        "cs_recurring_days_done":  "✅ Done",
        "cs_recurring_days_empty": "Pick at least one weekday first.",
        "cs_recurring_ask_time":   "Enter the session time in your local timezone (HH:MM):",
        "cs_recurring_created":    "✅ Recurring session set up\nCohort: {cohort}\nDays: {days}\n🕐 {time}\nUpcoming sessions for the next 30 days have been scheduled automatically.",
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
        "btn_set_notifs":        "🔔 Notifications",
        # Section headers
        "section_individual":    "👤 Individual:",
        "section_cohorts_menu":  "👥 My Cohorts:",
        "section_summary":       "📊 Summary:",
        "section_settings_menu": "⚙️ Settings:",

        # ── COHORT_V2: cohort action menu labels ───────────────────────────
        "cv2_members":    "👥 Members",
        "cv2_schedule":   "📅 Schedule",
        "cv2_attendance": "✅ Attendance",
        "cv2_checkins":   "📊 Check-ins",
        "cv2_notes":      "📝 Notes",
        "cv2_broadcast":  "📢 Broadcast",
        "cv2_stats":      "📊 Statistics",
        "cv2_archive":    "📦 Archive",
        "cv2_recurring":  "🔁 Recurring",
        "cv2_back":       "⬅️ Back",
        "cohort_action_title": "📋 {name}:",

        # Members list
        "cv2_members_title":   "Members of «{cohort}» ({count}):",
        "cv2_member_row":      "• {name}",
        "cv2_no_members":      "No members in this cohort yet.",

        # Broadcast
        "cv2_broadcast_ask":        "Enter the message to send to all {count} member(s) of «{cohort}»:",
        "cv2_broadcast_preview":    "📣 Preview:\n\n{text}\n\nSend to {count} member(s)?",
        "cv2_broadcast_send":       "✅ Send",
        "cv2_broadcast_cancel":     "❌ Cancel",
        "cv2_broadcast_done":       "✅ Sent to {sent}/{total} member(s).",
        "cv2_broadcast_no_members": "No active members to send to.",

        # Archive
        "cv2_archive_confirm":  "Archive cohort «{cohort}»?\nReminders will stop for all members.",
        "cv2_archive_yes":      "📦 Archive",
        "cv2_archive_no":       "❌ Cancel",
        "cv2_archived_ok":      "✅ Cohort «{cohort}» archived.",
        "cv2_already_archived": "This cohort is already archived.",

        # Stats
        "cv2_stats_title":          "📊 Stats — {cohort}:",
        "cv2_stats_members":        "Members: {count}",
        "cv2_stats_sessions":       "Sessions: {total} ({completed} completed)",
        "cv2_stats_attendance_pct": "Avg attendance: {pct}%",
        "cv2_stats_checkins":       "Check-in responses: {count}",
        "cv2_stats_avg_score":      "Avg score: {avg}/10",

        # Check-ins
        "cv2_checkin_options_title": "Check-ins for «{cohort}»:",
        "cv2_checkin_btn_setup":     "⚙️ Setup Auto Check-in",
        "cv2_checkin_btn_summary":   "📊 View Summary",
        "cv2_checkin_btn_send_now":  "📤 Send Now",
        "cv2_checkin_ask_question":  "Enter the check-in question (will be sent to all members):",
        "cv2_checkin_ask_interval":  "Send every N hours (e.g. 24 for daily):",
        "cv2_checkin_saved":         "✅ Check-in configured.\nQuestion: {q}\nInterval: every {h}h",
        "cv2_checkin_sent":          "✅ Check-in sent to {count} member(s).",
        "cv2_checkin_summary_title": "Check-in summary — {cohort}:",
        "cv2_checkin_row":           "• {name}: {count} response(s), avg {avg}/10",
        "cv2_no_checkin_data":       "No check-in data yet.",
        "cv2_checkin_member_thanks": "✅ Your response has been recorded. Thank you!",

        # Session notes
        "cv2_notes_pick_session": "Select a session to view or add notes:",
        "cv2_notes_title":        "Notes — Session #{num}:",
        "cv2_note_row":           "📝 {text}",
        "cv2_soap_row":           "📋 SOAP:\n{text}",
        "cv2_notes_empty":        "No notes for this session yet.",
        "cv2_note_btn_add":       "➕ Add Note",
        "cv2_note_btn_soap":      "📋 SOAP Note",
        "cv2_note_ask":           "Enter your note for Session #{num}:",
        "cv2_note_saved":         "✅ Note saved.",
        "cv2_soap_s":             "SOAP — Session #{num}.\n\nS — Subjective (client's words, mood, complaints):",
        "cv2_soap_o":             "O — Objective (your observations, behavior, test results):",
        "cv2_soap_a":             "A — Assessment (clinical impression, hypothesis):",
        "cv2_soap_p":             "P — Plan (next steps, homework, session focus):",
        "cv2_soap_saved":         "✅ SOAP note saved for Session #{num}.",

        # Notifications stub
        "notifs_not_implemented": "🔔 Notification preferences are coming soon.",

        # Supervision
        "sup_case_alias":       "Enter a client alias (no real names please):",
        "sup_case_issue":       "Presenting issue — what brings the client:",
        "sup_case_hypothesis":  "Your working hypothesis:",
        "sup_case_intervention":"Intervention used or planned:",
        "sup_case_outcome":     "Expected or observed outcome:",
        "sup_case_saved":       "✅ Supervision case saved: {alias}",
        "sup_logbook_title":    "Supervision logbook — {count} case(s):",
        "sup_logbook_row":      "#{id} {alias} [{status}] — {date}",
        "sup_logbook_empty":    "No supervision cases yet. Use /supervision_case to add one.",
        "sup_progress_title":   "Open supervision cases:",
        "sup_progress_row":     "#{id} {alias}\nIssue: {issue}\nHypothesis: {hyp}\nIntervention: {interv}\nOutcome: {outcome}",
        "sup_progress_empty":   "No open supervision cases.",
        "sup_close_btn":        "✅ Close case",
        "sup_case_closed":      "✅ Case #{id} marked as closed.",
        "sup_case_not_found":   "Case not found.",
    },

    "ru": {
        # ── Приветствие ───────────────────────────────────────────────────
        "welcome": "Прохор онлайн. Я запомню ваших клиентов и записи о сессиях.",
        "language_select": "Выберите язык:",
        "language_saved": "Язык сохранён.",

        # ── Управление клиентами ──────────────────────────────────────────
        "client_added": "Клиент добавлен: {name}",
        "client_not_found": "Клиент не найден: {name}",
        "no_clients": "Пока нет клиентов.",
        "clients_title": "Клиенты:",
        "clients_status_title": "Статус клиентов:",
        "connected": "подключён",
        "not_connected": "не подключён",
        "client_archived": "Клиент {name} перемещён в архив.",
        "client_already_archived": "Клиент {name} уже в архиве.",
        "client_unarchived": "Клиент {name} возвращён в активный список.",
        "client_not_archived": "Клиент {name} не находится в архиве.",
        "archived_title": "Архивные клиенты:",
        "no_archived": "Архив пуст.",

        # ── Заметки ───────────────────────────────────────────────────────
        "note_saved": "Заметка сохранена для {client}.",
        "notes_title": "Заметки для {client}:",
        "no_notes": "Для {client} пока нет заметок.",
        "summary_text": "Клиент: {client}\nЗаметок: {count}",
        "summary_last": "\nПоследнее обновление:\n{last}",
        "soap_saved": "SOAP-заметка сохранена для {client}:\n\n{text}",
        "soap_s": "Начинаем SOAP-заметку для {client}.\n\nS — Субъективно (слова клиента, жалобы, настроение):",
        "soap_o": "O — Объективно (ваши наблюдения, поведение, результаты тестов):",
        "soap_a": "A — Оценка (ваше клиническое впечатление, гипотеза):",
        "soap_p": "P — План (следующие шаги, домашнее задание, фокус следующей сессии):",

        # ── Чек-ины ───────────────────────────────────────────────────────
        "checkin_saved": "Чек-ин сохранён для {client}: {score}/10",
        "checkins_title": "Чек-ины для {client}:",
        "no_checkins": "Для {client} пока нет чек-инов.",
        "checkin_request_sent": "Запрос чек-ина отправлен {client}.",
        "auto_checkin_enabled": "Авточек-ин для {client} включён: каждые {interval} минут.",
        "no_auto_checkins": "Авточек-ины не настроены.",
        "auto_checkins_done": "Авточек-ины выполнены для {count} клиент(ов).",

        # ── Вовлечённость ─────────────────────────────────────────────────
        "engagement_text": "Клиент: {client}\nЗаметок: {notes}\nЧек-инов: {checkins}\nСредний балл: {avg}\n\n{label}",
        "good_stability": "Хорошая стабильность",
        "moderate": "Умеренные колебания",
        "risk_zone": "Зона риска",
        "no_checkin_data": "Нет данных чек-инов",
        "flag_risk": "⚠ Обнаружена зона риска: низкая эмоциональная стабильность",
        "flag_negative": "⚠ Выявлен негативный тренд",

        # ── Напоминания ───────────────────────────────────────────────────
        "reminder_set": "Напоминание для {client} установлено через {minutes} минут.",
        "no_reminders": "Напоминаний нет.",
        "reminders_title": "Напоминания:",

        # ── Сессии ────────────────────────────────────────────────────────
        "session_scheduled": "Сессия запланирована с {client} на {date} ({tz_info}).\nНапомню за 24ч и за 1ч.",
        "tz_info": "ваше время, {offset}",
        "timezone_usage": "Текущий часовой пояс: {current}\n\nУстановите с помощью:\n/timezone +3\n/timezone -5\n/timezone +05:30\n/timezone Europe/Moscow",
        "timezone_invalid": "⚠️ Неизвестный часовой пояс. Примеры:\n/timezone +3\n/timezone Europe/Moscow\n/timezone -05:30",
        "timezone_saved": "✅ Часовой пояс установлен: {tz} ({offset}).",
        "onboarding_welcome": "👋 Добро пожаловать в Прохор!\n\nСначала выберите язык:",
        "ask_timezone_onboarding": (
            "🕐 Почти готово! Выберите часовой пояс, чтобы время сессий отображалось правильно:"
        ),
        "ask_timezone_settings": "🕐 Выберите часовой пояс:",
        "ask_timezone_custom": (
            "Введите ваш часовой пояс:\n\nПримеры:\n"
            "  +3   -5   +05:30\n"
            "  Europe/Moscow   America/New_York"
        ),
        "btn_tz_custom": "✏️ Ввести вручную",
        "btn_skip":      "⏭ Пропустить",
        "btn_timezone":  "🕐 Часовой пояс",
        "tz_skipped": "Часовой пояс установлен UTC по умолчанию. Изменить можно в ⚙️ Настройках.",
        "sessions_title": "Предстоящие сессии:",
        "no_sessions": "Предстоящих сессий нет.",
        "session_row": "#{id} | {client} | {date}",
        "session_cancelled": "Сессия #{id} отменена.",
        "session_not_found": "Сессия не найдена.",
        "session_rescheduled": "Сессия #{id} перенесена на {date}.",
        "session_cancelled_notify": "⚠ Ваша сессия {date} отменена.",
        "session_rescheduled_notify": "🔄 Ваша сессия перенесена на {date}.",
        "reminder_psych_24h": "🔔 Напоминание: сессия с {client} завтра в {time}.",
        "reminder_psych_1h": "🔔 Напоминание: сессия с {client} через 1 час, в {time}.",
        "reminder_client_24h": "⏰ Напоминание:\nЗавтра в {time} у вас сессия со специалистом.",
        "reminder_client_1h": "⏰ Напоминание:\nВаша сессия начнётся через 1 час (в {time}).",
        "session_link_line": "\nСсылка на сессию:\n{link}",

        # ── Дашборд ───────────────────────────────────────────────────────
        "dashboard_title": "Дашборд:",
        "dashboard_row": "Клиент: {name}\nЗаметок: {notes} | Чек-инов: {checkins} | Ср. балл: {avg}\nСтатус: {status}",
        "no_data": "Нет данных",

        # ── Домашние задания ──────────────────────────────────────────────
        "homework_sent": "Задание отправлено {client}.",
        "homework_saved_offline": "Задание сохранено для {client} (клиент ещё не подключён).",
        "homeworks_title": "Задания для {client}:",
        "no_homework": "Для {client} пока нет заданий.",
        "new_homework_client": "📚 Новое задание от специалиста:\n\n{text}",

        # ── Приглашение ───────────────────────────────────────────────────
        "invite_link": "Ссылка-приглашение для {client}:\n{link}",
        "invite_invalid": "Недействительная или устаревшая ссылка.",
        "client_info": "Клиент: {client}\nПодключён: {connected}\n{tg_line}",
        "tg_id_line": "Telegram ID: {tid}",
        "tg_not_connected": "Telegram ID: не подключён",

        # ── Хронология ───────────────────────────────────────────────────
        "timeline_title": "Хронология для {client}:",
        "no_timeline": "История пуста.",
        "timeline_note": "📝 Заметка: {text}",
        "timeline_checkin": "📊 Чек-ин: {score}/10",
        "timeline_homework": "📚 Задание: {text}",
        "timeline_session": "📅 Сессия",

        # ── Предупреждения ────────────────────────────────────────────────
        "alerts_title": "Предупреждения:",
        "no_alerts": "Предупреждений нет. Всё в порядке.",
        "alert_low_score": "⚠ {client}: средний балл ниже 4",
        "alert_no_checkin": "⚠ {client}: нет чек-инов 10+ дней",
        "alert_no_session": "⚠ {client}: нет сессий 30+ дней",

        # ── Теги ─────────────────────────────────────────────────────────
        "tag_added": "Тег '{tag}' добавлен для {client}.",
        "find_title": "Клиенты с тегом '{tag}':",
        "no_clients_tag": "Клиентов с тегом '{tag}' не найдено.",

        # ── Экспорт ───────────────────────────────────────────────────────
        "export_filename": "экспорт_{client}.txt",

        # ── Клиентская сторона ────────────────────────────────────────────
        "client_connected": "Вы подключены к специалисту {specialist}.\n\nДоступные команды:\n/my_homeworks — ваши задания\n/checkin_history — история чек-инов",
        "client_menu": "Добро пожаловать в Прохор.\n\nДоступные команды:\n/my_homeworks — ваши задания\n/checkin_history — история чек-инов",
        "not_a_client": "Вы не подключены как клиент. Используйте ссылку-приглашение.",
        "checkin_question": "Как вы себя чувствуете сегодня?",
        "checkin_thanks": "Спасибо. Ваш ответ записан.",
        "checkin_submitted": "Клиент {client} отправил чек-ин: {score}/10",
        "my_homeworks_title": "Ваши задания:",
        "no_my_homeworks": "Заданий пока нет.",
        "my_checkins_title": "Ваши последние чек-ины:",
        "no_my_checkins": "Чек-инов пока нет.",
        "client_not_connected_tg": "Клиент ещё не подключён к Telegram.",

        # ── Двойная роль / защита от самоприглашения ──────────────────────
        "self_invite_error": "⚠️ Вы не можете использовать собственную ссылку-приглашение.",
        "dual_role_select": "У вас две роли. Какой интерфейс открыть?",
        "btn_role_psychologist": "🧠 Интерфейс психолога",
        "btn_role_client": "👤 Мой профиль клиента",
        "switch_no_dual_role": "У вас только одна роль. Используйте /start для открытия интерфейса.",
        "client_role_reset": "Профиль клиента отключён. Активен режим психолога.",
        "client_role_not_found": "Активный профиль клиента для отключения не найден.",

        # ── Ошибки / использование ────────────────────────────────────────
        "score_invalid": "Балл должен быть целым числом от 1 до 10.",
        "minutes_invalid": "Минуты должны быть положительным целым числом.",
        "interval_invalid": "Интервал должен быть положительным целым числом.",
        "date_invalid": "Неверный формат даты. Используйте: ГГГГ-ММ-ДД ЧЧ:ММ",
        "id_invalid": "ID сессии должен быть положительным целым числом.",

        # ── Кнопки главного меню ──────────────────────────────────────────
        "btn_clients":   "👤 Клиенты",
        "btn_sessions":  "📅 Сессии",
        "btn_homework":  "📚 Задания",
        "btn_analytics": "📊 Аналитика",
        "btn_checkins":  "🔔 Чек-ины",
        "btn_settings":  "⚙️ Настройки",

        # ── Навигация ─────────────────────────────────────────────────────
        "btn_back":      "⬅ Назад",
        "btn_main_menu": "🏠 Главное меню",
        "btn_prev":      "⬅ Пред",
        "btn_next":      "След ➡",
        "btn_cancel":    "✖ Отмена",

        # ── Кнопки разделов ───────────────────────────────────────────────
        "btn_add_client":       "➕ Добавить клиента",
        "btn_client_list":      "📋 Список клиентов",
        "btn_invite_client":    "🔗 Пригласить клиента",
        "btn_archived_clients": "🗄 Архив",
        "btn_schedule_session": "➕ Запланировать сессию",
        "btn_upcoming_sessions":"📋 Предстоящие сессии",
        "btn_assign_homework":  "➕ Задать задание",
        "btn_active_homework":  "📋 Активные задания",
        "btn_dashboard":        "📈 Дашборд",
        "btn_alerts":           "⚠ Предупреждения",
        "btn_send_checkin":     "➕ Отправить чек-ин",
        "btn_auto_checkins":    "⚙ Авточек-ины",
        "btn_recent_checkins":  "📋 Последние чек-ины",
        "btn_language":         "🌍 Язык",
        "btn_about":            "ℹ О боте",

        # ── Кнопки карточки клиента ───────────────────────────────────────
        "btn_add_note":      "📝 Заметка",
        "btn_soap_note":     "📄 SOAP",
        "btn_assign_hw":     "📚 Задание",
        "btn_send_ci":       "💬 Чек-ин",
        "btn_sched_session": "📅 Сессия",
        "btn_timeline":      "📈 Хронология",
        "btn_tags":          "🏷 Теги",
        "btn_engagement":    "📊 Вовлечённость",
        "btn_export":        "📤 Экспорт",
        "btn_archive":       "🗄 Архивировать",
        "btn_unarchive":     "♻️ Восстановить",
        "btn_invite_link":   "🔗 Ссылка-приглашение",

        # ── Кнопки карточки сессии ────────────────────────────────────────
        "btn_reschedule":    "✏ Перенести",
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
        "ask_note_text":         "Введите текст заметки:",
        "ask_homework_text":     "Введите текст задания:",
        "ask_session_datetime":  "Введите дату и время в вашем часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "ask_reschedule_datetime":"Введите новую дату и время в вашем часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "ask_tag":               "Введите тег:",
        "ask_checkin_client":    "Введите имя клиента для чек-ина:",
        "ask_auto_client":       "Введите имя клиента:",
        "ask_auto_interval":     "Введите интервал в минутах:",
        "fsm_cancelled":         "Отменено.",

        # ── Карточка клиента ─────────────────────────────────────────────
        "client_card":    "👤 {name}\n\nЗаметок: {notes} | Чек-инов: {checkins} | Ср. балл: {avg}\nСледующая сессия: {session}",
        "no_next_session":"Нет",
        "page_indicator": "{page}/{total}",

        # ── Список заданий ────────────────────────────────────────────────
        "homework_list_title": "Активные задания:",
        "no_active_homework":  "Активных заданий нет.",

        # ── Последние чек-ины ─────────────────────────────────────────────
        "recent_checkins_title": "Последние чек-ины (10 шт.):",
        "no_recent_checkins":    "Чек-инов пока нет.",

        # ── О боте ───────────────────────────────────────────────────────
        "about_text": "🤖 Прохор — ассистент для психологов и коучей.\n\nВерсия 2.0\n\nВозможности: клиенты, сессии, задания, заметки, SOAP, аналитика, экспорт, локализация.",

        # ── Когорты ───────────────────────────────────────────────────────
        "cohort_ask_name":              "Введите название когорты:",
        "cohort_ask_description":       "Введите описание (или нажмите Пропустить):",
        "cohort_ask_max":               "Максимальное количество участников (введите число или отправьте что угодно для значения по умолчанию — 12):",
        "cohort_ask_type":              "Выберите тип когорты:",
        "cohort_created":               "✅ Когорта создана: <b>{name}</b>\n\nТип: {type}\nМакс. участников: {max}\n\nСсылка-приглашение:\n{link}",
        "cohort_list_title":            "Ваши когорты:",
        "no_cohorts":                   "Когорт пока нет. Используйте /cohort_create для создания.",
        "cohort_list_row":              "• {name} ({count}/{max} участников)",
        "cohort_join_prompt":           "Вас приглашают в когорту <b>{name}</b>.\n\nНажмите кнопку ниже, чтобы подтвердить.",
        "cohort_join_confirm":          "✅ Вы вступили в когорту <b>{name}</b>!",
        "cohort_already_member":        "Вы уже являетесь участником этой когорты.",
        "cohort_is_leader":             "Вы являетесь ведущим этой когорты.",
        "cohort_invalid_token":         "Недействительная или устаревшая ссылка-приглашение.",
        "cohort_full":                  "Когорта заполнена.",
        "btn_cohort_join":              "✅ Вступить в когорту",
        "btn_cohort_skip_desc":         "⏭ Пропустить",
        "btn_cohort_type_course":       "📚 Курс",
        "btn_cohort_type_group":        "👥 Группа",
        "btn_cohort_type_supervision":  "🔍 Супервизия",

        # ── Сессии когорты ────────────────────────────────────────────────
        "cs_pick_cohort_schedule":  "Выберите когорту для планирования сессии:",
        "cs_pick_cohort_list":      "Выберите когорту для просмотра сессий:",
        "cs_ask_session_num":       "Введите номер сессии:",
        "cs_ask_datetime":          "Введите дату и время в вашем часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "cs_ask_topic":             "Введите тему сессии (или нажмите Пропустить):",
        "cs_ask_link":              "Введите ссылку на сессию (или нажмите Пропустить):",
        "cs_skip":                  "⏭ Пропустить",
        "cs_created":               "✅ Сессия #{num} запланирована\nКогорта: {cohort}\n📅 {date}\n📋 Тема: {topic}",
        "cs_no_topic":              "—",
        "cs_list_title":            "Сессии — {cohort}:",
        "no_cs":                    "Сессий пока нет. Используйте /cohort_schedule для добавления.",
        "cs_row":                   "#{num} — {date} — {topic} [{status}]",
        "cs_status_scheduled":      "запланирована",
        "cs_status_completed":      "завершена",
        "cs_status_cancelled":      "отменена",
        "cs_att_pick_cohort":       "Выберите когорту:",
        "cs_att_pick_session":      "Выберите сессию:",
        "cs_att_title":             "Посещаемость — Сессия #{num} ({cohort}):",
        "cs_att_no_members":        "В этой когорте пока нет участников.",
        "cs_att_no_sessions":       "Сессий в этой когорте не найдено.",
        "cs_att_saved":             "✅ Сохранено.",
        "cs_reminder_24h":          "🔔 Завтра в {time} — сессия когорты #{num} ({cohort}){link_line}",
        "cs_reminder_1h":           "🔔 Через час в {time} — сессия когорты #{num} ({cohort}){link_line}",
        "cs_reminder_psych_24h":    "🔔 Сессия когорты #{num} ({cohort}) — завтра в {time}. Участники уведомлены.{link_line}",
        "cs_reminder_psych_1h":     "🔔 Сессия когорты #{num} ({cohort}) — через час в {time}. Участники уведомлены.{link_line}",
        "cs_link_line":             "\n🔗 {link}",

        # ── SESSIONS: список сессий и детальный экран с действиями ──────────
        "cv2_sessions":             "📅 Сессии",
        "cs2_list_title":           "📅 Сессии — «{cohort}» (ближайшие {days} дней):",
        "cs2_list_empty":           "Нет сессий в ближайшие {days} дней для «{cohort}».",
        "cs2_btn_add_oneoff":       "➕ Разовая сессия",
        "cs2_btn_add_recurring":    "🔁 Настроить повтор",
        "cs2_btn_back_list":        "⬅️ К списку",
        "cs2_not_found":            "Сессия не найдена или уже удалена.",
        "cs2_detail_header":       "📋 Сессия #{num} — {cohort}",
        "cs2_detail_date":         "📅 {date}",
        "cs2_detail_topic":        "📝 Тема: {topic}",
        "cs2_detail_link":         "🔗 Ссылка: {link}",
        "cs2_detail_recurring":    "🔁 Повторяется: {days}",
        "cs2_detail_paused":       "⏸ На паузе — новые сессии не создаются",
        "cs2_no_link":             "—",
        "cs2_btn_edit_dt":          "✏️ Дата/время",
        "cs2_btn_edit_topic":       "📝 Тема",
        "cs2_btn_edit_link":        "🔗 Ссылка",
        "cs2_btn_delete":           "🗑 Удалить",
        "cs2_btn_pause":            "⏸ Приостановить повтор",
        "cs2_btn_resume":           "▶️ Продолжить повтор",
        "cs2_btn_delete_rule":      "🚫 Удалить правило повтора",
        "cs2_btn_clear":            "🗑 Очистить",
        "cs2_ask_datetime_new":     "Введите новую дату и время в вашем часовом поясе (ГГГГ-ММ-ДД ЧЧ:ММ):",
        "cs2_ask_topic_new":        "Введите новую тему (или нажмите Очистить, чтобы убрать её):",
        "cs2_ask_link_new":         "Введите новую ссылку (или нажмите Очистить, чтобы убрать её):",
        "cs2_updated_dt":           "✅ Дата/время обновлены.",
        "cs2_updated_topic":        "✅ Тема обновлена.",
        "cs2_updated_link":         "✅ Ссылка обновлена.",
        "cs2_delete_confirm":       "Удалить сессию #{num} от {date}?\nЕё записи посещаемости также будут удалены.",
        "cs2_delete_yes":           "🗑 Удалить",
        "cs2_delete_no":            "❌ Отмена",
        "cs2_deleted_ok":           "✅ Сессия #{num} удалена.",
        "cs2_paused_ok":            "⏸ Повтор приостановлен для «{cohort}». Новые сессии не будут создаваться до возобновления.",
        "cs2_resumed_ok":           "▶️ Повтор возобновлён для «{cohort}».",
        "cs2_delrule_confirm":      "Удалить правило повтора для «{cohort}»?\nУже запланированные сессии останутся, но новые создаваться не будут.",
        "cs2_delrule_yes":          "🚫 Удалить правило",
        "cs2_delrule_no":           "❌ Отмена",
        "cs2_delrule_ok":           "✅ Правило повтора удалено для «{cohort}».",

        # ── RECURRING: повторяющиеся сессии когорты ────────────────────────
        "dow_mon": "Пн", "dow_tue": "Вт", "dow_wed": "Ср", "dow_thu": "Чт",
        "dow_fri": "Пт", "dow_sat": "Сб", "dow_sun": "Вс",
        "cs_recurring_pick_cohort":  "Выберите когорту для повторяющейся сессии:",
        "cs_recurring_ask_days":    "Выберите дни недели, в которые повторяется сессия, затем нажмите Готово:",
        "cs_recurring_days_done":  "✅ Готово",
        "cs_recurring_days_empty": "Сначала выберите хотя бы один день недели.",
        "cs_recurring_ask_time":   "Введите время сессии в вашем часовом поясе (ЧЧ:ММ):",
        "cs_recurring_created":    "✅ Повторяющаяся сессия настроена\nКогорта: {cohort}\nДни: {days}\n🕐 {time}\nБудущие сессии на ближайшие 30 дней уже запланированы автоматически.",
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
        "btn_set_notifs":        "🔔 Уведомления",
        # Заголовки разделов
        "section_individual":    "👤 Индивидуальные:",
        "section_cohorts_menu":  "👥 Мои когорты:",
        "section_summary":       "📊 Сводка:",
        "section_settings_menu": "⚙️ Настройки:",

        # ── COHORT_V2: кнопки меню когорты ────────────────────────────────
        "cv2_members":    "👥 Участники",
        "cv2_schedule":   "📅 Расписание",
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
        "cv2_members_title":   "Участники «{cohort}» ({count}):",
        "cv2_member_row":      "• {name}",
        "cv2_no_members":      "В этой когорте пока нет участников.",

        # Рассылка
        "cv2_broadcast_ask":        "Введите сообщение для рассылки всем {count} участникам «{cohort}»:",
        "cv2_broadcast_preview":    "📣 Предпросмотр:\n\n{text}\n\nОтправить {count} участникам?",
        "cv2_broadcast_send":       "✅ Отправить",
        "cv2_broadcast_cancel":     "❌ Отмена",
        "cv2_broadcast_done":       "✅ Отправлено {sent}/{total} участникам.",
        "cv2_broadcast_no_members": "Нет активных участников для рассылки.",

        # Архивация
        "cv2_archive_confirm":  "Архивировать когорту «{cohort}»?\nНапоминания будут отключены.",
        "cv2_archive_yes":      "📦 Архивировать",
        "cv2_archive_no":       "❌ Отмена",
        "cv2_archived_ok":      "✅ Когорта «{cohort}» архивирована.",
        "cv2_already_archived": "Эта когорта уже архивирована.",

        # Статистика
        "cv2_stats_title":          "📊 Статистика — {cohort}:",
        "cv2_stats_members":        "Участников: {count}",
        "cv2_stats_sessions":       "Сессий: {total} ({completed} завершено)",
        "cv2_stats_attendance_pct": "Средняя посещаемость: {pct}%",
        "cv2_stats_checkins":       "Ответов на чек-ины: {count}",
        "cv2_stats_avg_score":      "Средний балл: {avg}/10",

        # Чек-ины
        "cv2_checkin_options_title": "Чек-ины для «{cohort}»:",
        "cv2_checkin_btn_setup":     "⚙️ Настроить авточек-ин",
        "cv2_checkin_btn_summary":   "📊 Сводка ответов",
        "cv2_checkin_btn_send_now":  "📤 Отправить сейчас",
        "cv2_checkin_ask_question":  "Введите вопрос для чек-ина (будет отправлен всем участникам):",
        "cv2_checkin_ask_interval":  "Отправлять каждые N часов (например, 24 — ежедневно):",
        "cv2_checkin_saved":         "✅ Чек-ин настроен.\nВопрос: {q}\nИнтервал: каждые {h}ч",
        "cv2_checkin_sent":          "✅ Чек-ин отправлен {count} участникам.",
        "cv2_checkin_summary_title": "Сводка чек-инов — {cohort}:",
        "cv2_checkin_row":           "• {name}: {count} ответ(ов), средний балл {avg}/10",
        "cv2_no_checkin_data":       "Данных чек-инов пока нет.",
        "cv2_checkin_member_thanks": "✅ Ваш ответ записан. Спасибо!",

        # Заметки по сессии
        "cv2_notes_pick_session": "Выберите сессию для просмотра или добавления заметок:",
        "cv2_notes_title":        "Заметки — Сессия #{num}:",
        "cv2_note_row":           "📝 {text}",
        "cv2_soap_row":           "📋 SOAP:\n{text}",
        "cv2_notes_empty":        "Заметок для этой сессии пока нет.",
        "cv2_note_btn_add":       "➕ Добавить заметку",
        "cv2_note_btn_soap":      "📋 SOAP-заметка",
        "cv2_note_ask":           "Введите заметку для Сессии #{num}:",
        "cv2_note_saved":         "✅ Заметка сохранена.",
        "cv2_soap_s":             "SOAP — Сессия #{num}.\n\nS — Субъективное (слова клиента, жалобы, настроение):",
        "cv2_soap_o":             "O — Объективное (ваши наблюдения, поведение, тесты):",
        "cv2_soap_a":             "A — Оценка (клиническое впечатление, гипотеза):",
        "cv2_soap_p":             "P — План (следующие шаги, домашнее задание, фокус):",
        "cv2_soap_saved":         "✅ SOAP-заметка сохранена для Сессии #{num}.",

        # Уведомления (заглушка)
        "notifs_not_implemented": "🔔 Настройки уведомлений появятся в ближайшем обновлении.",

        # Супервизия
        "sup_case_alias":       "Введите псевдоним клиента (без реального имени):",
        "sup_case_issue":       "Запрос — с чем пришёл клиент:",
        "sup_case_hypothesis":  "Рабочая гипотеза:",
        "sup_case_intervention":"Использованная или планируемая интервенция:",
        "sup_case_outcome":     "Ожидаемый или наблюдаемый результат:",
        "sup_case_saved":       "✅ Случай супервизии сохранён: {alias}",
        "sup_logbook_title":    "Журнал супервизии — {count} случай(ев):",
        "sup_logbook_row":      "#{id} {alias} [{status}] — {date}",
        "sup_logbook_empty":    "Случаев супервизии пока нет. Используйте /supervision_case.",
        "sup_progress_title":   "Открытые случаи супервизии:",
        "sup_progress_row":     "#{id} {alias}\nЗапрос: {issue}\nГипотеза: {hyp}\nИнтервенция: {interv}\nРезультат: {outcome}",
        "sup_progress_empty":   "Нет открытых случаев супервизии.",
        "sup_close_btn":        "✅ Закрыть случай",
        "sup_case_closed":      "✅ Случай #{id} закрыт.",
        "sup_case_not_found":   "Случай не найден.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Return translated string for the given language and key.
    Falls back to English if the key or language is not found."""
    text = TEXTS.get(lang, TEXTS["en"]).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
