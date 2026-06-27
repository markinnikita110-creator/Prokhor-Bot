from aiogram.fsm.state import State, StatesGroup


class AssignHomeworkForm(StatesGroup):
    """Used when assigning from menu (no client pre-selected)."""
    client_name = State()
    text = State()


class AssignHomeworkFromCardForm(StatesGroup):
    """Used when assigning from client card (client already in FSM data)."""
    text = State()
