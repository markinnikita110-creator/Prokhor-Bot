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


class IndividualSessionRecurringForm(StatesGroup):
    """INDIVIDUAL_SESSION: FSM for setting up a recurring individual session."""
    days = State()
    time_ = State()
    topic = State()
    link = State()


class IndividualSessionEditForm(StatesGroup):
    """INDIVIDUAL_SESSION: FSM for editing one field of an individual session."""
    datetime_ = State()
    topic = State()
    link = State()


class IndividualOneOffForm(StatesGroup):
    """INDIVIDUAL_SESSION: FSM for creating a one-off session from the sessions panel."""
    datetime_ = State()
    topic = State()
    link = State()
