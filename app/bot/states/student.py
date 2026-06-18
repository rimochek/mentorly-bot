from aiogram.fsm.state import State, StatesGroup


class StudentSearchStates(StatesGroup):
    exam = State()
    custom_exam_name = State()
    exam_detail = State()
    ap_custom = State()
    custom_goal = State()
    olympiad_subject = State()
    olympiad_grade = State()
    level = State()
    budget = State()
    browsing = State()
