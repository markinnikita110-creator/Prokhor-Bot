"""Public API surface for the psychologist profile / users domain.

Re-exports all profile functions from ``core.db.users_repository`` so that
callers can import from a single, stable location.  Any future business-logic
wrappers (e.g. validated timezone saving, registration events) belong here.
"""

from core.db.users_repository import (
    ensure_user,
    get_user_lang,
    get_user_timezone,
    needs_tz_confirm,
    set_user_lang,
    set_user_timezone,
)

__all__ = [
    "ensure_user",
    "get_user_lang",
    "get_user_timezone",
    "needs_tz_confirm",
    "set_user_lang",
    "set_user_timezone",
]
