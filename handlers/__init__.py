from . import (  # noqa: F401
    legal, menu, clients, sessions, homework, notes,
    analytics, checkins, settings, timezone,
    cohorts, supervision, client_sessions, plans,
    booking_settings, booking,
)

routers = [
    legal.router,              # LEGAL: consent callbacks first
    menu.router,
    plans.router,              # PLANS: /promo, /myplan, st_tariff and sub-screens
    client_sessions.router,    # INDIVIDUAL_SESSION: ics_/isd_/etc. before clients
    clients.router,
    sessions.router,
    homework.router,
    notes.router,
    analytics.router,
    checkins.router,
    settings.router,
    booking_settings.router,   # BOOKING: settings FSM before timezone (state priority)
    booking.router,            # BOOKING: client-facing flow
    timezone.router,
    cohorts.router,
    supervision.router,
]
