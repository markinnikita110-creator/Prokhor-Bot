from . import menu, clients, sessions, homework, notes, analytics, checkins, settings, timezone

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
]
