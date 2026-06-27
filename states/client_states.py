from aiogram.fsm.state import State, StatesGroup


class AddClientForm(StatesGroup):
    name = State()


class InviteClientForm(StatesGroup):
    client_name = State()
