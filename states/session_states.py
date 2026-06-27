from aiogram.fsm.state import State, StatesGroup


class ScheduleSessionForm(StatesGroup):
    """Used when scheduling from menu (no client pre-selected)."""
    client_name = State()
    datetime_str = State()


class ScheduleSessionFromCardForm(StatesGroup):
    """Used when scheduling from client card (client already in FSM data)."""
    datetime_str = State()


class RescheduleForm(StatesGroup):
    datetime_str = State()
