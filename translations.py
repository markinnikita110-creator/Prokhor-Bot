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
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Return translated string for the given language and key.
    Falls back to English if the key or language is not found."""
    text = TEXTS.get(lang, TEXTS["en"]).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
