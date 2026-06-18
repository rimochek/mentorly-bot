from aiogram.fsm.state import State, StatesGroup


class AdminModerationStates(StatesGroup):
    browsing = State()


class AdminBroadcastStates(StatesGroup):
    waiting_message = State()
