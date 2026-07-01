from . import legal, menu, clients, sessions, homework, notes, analytics, checkins, settings, timezone, cohorts, supervision, client_sessions  # COHORT_V2

routers = [
    legal.router,  # LEGAL: must be first so consent callbacks fire before menu routing
    menu.router,
    client_sessions.router,  # INDIVIDUAL_SESSION: before clients.router so ics_/isd_/etc. take priority
    clients.router,
    sessions.router,
    homework.router,
    notes.router,
    analytics.router,
    checkins.router,
    settings.router,
    timezone.router,
    cohorts.router,    # COHORT
    supervision.router,  # COHORT_V2
]
