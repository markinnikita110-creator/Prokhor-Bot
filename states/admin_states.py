from aiogram.fsm.state import State, StatesGroup


class AdminGrantPlanForm(StatesGroup):
    target_id = State()
    plan_name = State()
    days = State()
    confirm = State()


class AdminFindForm(StatesGroup):
    query = State()


class AdminBroadcastForm(StatesGroup):
    text = State()
    confirm = State()
