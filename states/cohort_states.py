from aiogram.fsm.state import State, StatesGroup

# COHORT: FSM states for the cohort creation wizard


class CohortCreateForm(StatesGroup):
    name = State()
    description = State()
    max_participants = State()
    type_ = State()
