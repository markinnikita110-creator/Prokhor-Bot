from aiogram.fsm.state import State, StatesGroup

# COHORT: FSM states for the cohort creation wizard


class CohortCreateForm(StatesGroup):
    name = State()
    description = State()
    max_participants = State()
    type_ = State()


# COHORT_SESSION: FSM states for scheduling a cohort session
class CohortScheduleForm(StatesGroup):
    cohort = State()
    session_number = State()
    datetime_ = State()
    topic = State()
    link = State()


# COHORT_SESSION: FSM states for recording attendance
class CohortAttendanceForm(StatesGroup):
    cohort = State()
    session = State()
