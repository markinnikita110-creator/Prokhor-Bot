from aiogram.fsm.state import State, StatesGroup


# COHORT: FSM for cohort creation wizard
class CohortCreateForm(StatesGroup):
    name = State()
    description = State()
    max_participants = State()
    type_ = State()


# COHORT_SESSION: FSM for scheduling a group session
class CohortScheduleForm(StatesGroup):
    cohort = State()
    session_number = State()
    datetime_ = State()
    topic = State()
    link = State()


# COHORT_SESSION: FSM for recording attendance
class CohortAttendanceForm(StatesGroup):
    cohort = State()
    session = State()


# RECURRING: FSM for scheduling a recurring (weekly) group session
class CohortRecurringScheduleForm(StatesGroup):
    cohort = State()
    days = State()
    time_ = State()
    topic = State()
    link = State()


# COHORT_V2: FSM for broadcasting a message to all cohort members
class CohortBroadcastForm(StatesGroup):
    message = State()
    confirm = State()


# COHORT_V2: FSM for configuring auto check-ins for a cohort
class CohortCheckinSetupForm(StatesGroup):
    question = State()
    interval = State()


# COHORT_V2: FSM for adding a plain note to a cohort session
class CohortSessionNoteForm(StatesGroup):
    note_text = State()


# COHORT_V2: FSM for adding a SOAP note to a cohort session (4 steps)
class CohortSOAPNoteForm(StatesGroup):
    s = State()
    o = State()
    a = State()
    p = State()
