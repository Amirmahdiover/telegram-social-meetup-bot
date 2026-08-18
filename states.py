from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    age_confirmation = State()
    first_name = State()
    age = State()
    gender = State()
    area = State()
    phone = State()
    activities = State()
    age_preference = State()
    availability = State()
    join_reason = State()
    review = State()
