from . import menu, clients, sessions, homework, notes, analytics, checkins, settings, timezone, cohorts, supervision  # COHORT_V2

routers = [
    menu.router,
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
