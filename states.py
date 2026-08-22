from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    age_confirmation = State()
    first_name = State()
    age = State()
    gender = State()
    join_reason = State()
    review = State()


class EventCreation(StatesGroup):
    title = State()
    date = State()
    time = State()
    location_name = State()
    location_address = State()
    latitude = State()
    longitude = State()
    message = State()
