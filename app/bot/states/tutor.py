from aiogram.fsm.state import State, StatesGroup


class TutorRegistrationStates(StatesGroup):
    name = State()
    age = State()
    city = State()
    place_of_study = State()
    price_min = State()
    price_max = State()
    description = State()
    photo = State()


class TutorEditStates(StatesGroup):
    waiting_value = State()
    photo = State()
