from aiogram.fsm.state import State, StatesGroup


class OnboardingForm(StatesGroup):
    language = State()          # step 1: waiting for language button click
    timezone = State()          # step 2: timezone keyboard shown, waiting for button
    timezone_custom = State()   # step 2b: waiting for manual text input (onboarding)


class TimezoneInputForm(StatesGroup):
    input = State()             # settings path: waiting for manual text input
