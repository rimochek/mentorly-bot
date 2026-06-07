from aiogram.fsm.state import State, StatesGroup


class StudentSearchStates(StatesGroup):
    exam = State()
    goal = State()
    level = State()
    budget = State()
    browsing = State()
