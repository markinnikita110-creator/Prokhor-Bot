from aiogram.fsm.state import State, StatesGroup


# COHORT_V2: FSM for creating a supervision case (5-step wizard)
class SupervisionCaseForm(StatesGroup):
    client_alias = State()
    presenting_issue = State()
    hypothesis = State()
    intervention = State()
    outcome = State()
