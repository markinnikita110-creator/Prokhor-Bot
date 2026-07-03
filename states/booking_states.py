from aiogram.fsm.state import State, StatesGroup


class BookingSetupForm(StatesGroup):
    display_name = State()
    bio = State()
    timezone = State()
    timezone_custom = State()


class BookingEditForm(StatesGroup):
    display_name = State()
    bio = State()
    timezone = State()
    timezone_custom = State()


class BookingScheduleForm(StatesGroup):
    start_time = State()
    end_time = State()
    duration = State()
    buffer = State()


class BookingExceptionForm(StatesGroup):
    date = State()
    start_time = State()
    end_time = State()


class BookingClientForm(StatesGroup):
    timezone = State()
    timezone_custom = State()
