from . import (  # noqa: F401
    legal, menu, clients, sessions, homework, notes,
    analytics, checkins, settings, timezone,
    cohorts, supervision, client_sessions, plans,
)

routers = [
    legal.router,           # LEGAL: consent callbacks first
    menu.router,
    plans.router,           # PLANS: /promo, /myplan, st_tariff and sub-screens
    client_sessions.router, # INDIVIDUAL_SESSION: ics_/isd_/etc. before clients
    clients.router,
    sessions.router,
    homework.router,
    notes.router,
    analytics.router,
    checkins.router,
    settings.router,
    timezone.router,
    cohorts.router,
    supervision.router,
]
