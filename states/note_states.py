from aiogram.fsm.state import State, StatesGroup


class AddNoteForm(StatesGroup):
    """Plain note — client pre-selected via client card."""
    text = State()


class SOAPForm(StatesGroup):
    """4-step SOAP note — client pre-selected or via /note_soap."""
    subjective = State()
    objective  = State()
    assessment = State()
    plan       = State()


class TagForm(StatesGroup):
    """Add tag — client pre-selected via client card."""
    tag = State()


class AddCheckinForm(StatesGroup):
    """Manual check-in entry from menu."""
    client_name = State()
    score       = State()
