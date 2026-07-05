"""Notes service layer.

No business rules currently exist for notes (no plan limits, no length
validation, no auto-linking to sessions — see Этап 0 audit). This module is
a thin pass-through re-export of the repository so handlers have a single
stable import point if rules are added later.
"""

from core.db.notes_repository import (
    count_notes,
    get_notes_created_text,
    get_notes_full,
    get_notes_text_only,
    insert_plain_note,
    insert_soap_note,
)

__all__ = [
    "count_notes",
    "get_notes_created_text",
    "get_notes_full",
    "get_notes_text_only",
    "insert_plain_note",
    "insert_soap_note",
]
