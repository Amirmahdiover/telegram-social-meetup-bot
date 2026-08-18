from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from database import get_registration, save_registration, track_funnel_event
from keyboards import (
    ACTIVITIES, ACTIVITIES_DONE, AGE_PREFERENCES, AREAS, AVAILABILITY, AVAILABILITY_DONE,
    FINAL_SUBMIT, GENDERS, JOIN_REASONS, NO, RESTART, START_REGISTRATION, YES,
    contact_keyboard, multi_select_keyboard, reply_keyboard,
)
from states import Registration

router = Router()

INTRO = (
    "سلام! اینجا دورهمی‌های کوچک تهران برای حدود ۶ تا ۸ نفره؛ "
    "برای آشنا شدن با آدم‌های جدید، تجربه‌ی جمعی و خوش‌گذرونی.\n\n"
    "چند سؤال کوتاه می‌پرسیم تا برای ساختن گروه‌های بهتر کمک کند. "
)


async def begin_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Registration.age_confirmation)
    await message.answer(
        "قبل از شروع، تأیید می‌کنی که ۱۸ سال یا بیشتر داری؟",
        reply_markup=reply_keyboard([YES, NO]),
    )


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await track_funnel_event(message.from_user.id, "registration_started")
    await message.answer(INTRO, reply_markup=reply_keyboard([START_REGISTRATION], 1))


@router.message(F.text == START_REGISTRATION)
async def start_button(message: Message, state: FSMContext) -> None:
    await begin_registration(message, state)


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("ثبت‌نام فعالی نداری.", reply_markup=ReplyKeyboardRemove())
        return
    await state.clear()
    await message.answer("فرایند ثبت‌نام لغو شد. هر زمان خواستی با /start دوباره شروع کن.", reply_markup=ReplyKeyboardRemove())


@router.message(Command("me"))
async def me(message: Message) -> None:
    registration = await get_registration(message.from_user.id)
    if not registration:
        await message.answer("هنوز ثبت‌نامی نداری. برای شروع /start را بزن.")
        return
    await message.answer(format_registration(registration, include_status=True))


@router.message(Command("whoami"))
async def whoami(message: Message) -> None:
    await message.answer(str(message.from_user.id))


@router.message(Registration.age_confirmation, F.text == YES)
async def age_confirmed(message: Message, state: FSMContext) -> None:
    await track_funnel_event(message.from_user.id, "age_confirmed")
    await state.set_state(Registration.first_name)
    await message.answer("اسمت چیه؟ اسم کوچک کافیه 🙂", reply_markup=ReplyKeyboardRemove())


@router.message(Registration.age_confirmation, F.text == NO)
async def age_declined(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("دورهمی‌های فعلی فقط برای کاربران ۱۸ سال به بالا هستند.", reply_markup=ReplyKeyboardRemove())


@router.message(Registration.age_confirmation)
async def age_confirmation_invalid(message: Message) -> None:
    await message.answer("لطفاً یکی از دکمه‌های بله یا خیر را انتخاب کن.")


@router.message(Registration.first_name)
async def first_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 40 or any(char.isdigit() for char in name):
        await message.answer("لطفاً فقط اسم کوچک و کوتاهت را وارد کن (حداکثر ۴۰ کاراکتر).")
        return
    await state.update_data(first_name=name)
    await track_funnel_event(message.from_user.id, "name_entered")
    await state.set_state(Registration.age)
    await message.answer("چند سالته؟")


@router.message(Registration.age)
async def age(message: Message, state: FSMContext) -> None:
    try:
        value = int((message.text or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
    except ValueError:
        await message.answer("لطفاً سنت را فقط به‌صورت عدد وارد کن.")
        return
    if not 18 <= value <= 60:
        await message.answer("برای این نسخه، سن باید بین ۱۸ تا ۶۰ سال باشد.")
        return
    await state.update_data(age=value)
    await track_funnel_event(message.from_user.id, "age_entered")
    await state.set_state(Registration.gender)
    await message.answer("جنسیتت رو انتخاب کن:", reply_markup=reply_keyboard(GENDERS))


@router.message(Registration.gender, F.text.in_(GENDERS))
async def gender(message: Message, state: FSMContext) -> None:
    await state.update_data(gender=message.text)
    await track_funnel_event(message.from_user.id, "gender_selected")
    await state.set_state(Registration.area)
    await message.answer("معمولاً کدوم محدوده تهران برات راحت‌تره؟", reply_markup=reply_keyboard(AREAS, 3))


@router.message(Registration.gender)
async def gender_invalid(message: Message) -> None:
    await message.answer("لطفاً یکی از گزینه‌های جنسیت را انتخاب کن.")


@router.message(Registration.area, F.text.in_(AREAS))
async def area(message: Message, state: FSMContext) -> None:
    await state.update_data(area=message.text)
    await track_funnel_event(message.from_user.id, "area_selected")
    await state.set_state(Registration.phone)
    await message.answer(
        "📱 برای هماهنگی و تأیید حضور قبل از دورهمی، شماره تلفنت رو با ما به اشتراک بذار. "
        "شماره‌ات به سایر شرکت‌کننده‌ها نمایش داده نمی‌شه و فقط برای هماهنگی دورهمی و تأیید حضور استفاده می‌شه.",
        reply_markup=contact_keyboard(),
    )
    await track_funnel_event(message.from_user.id, "phone_requested")


@router.message(Registration.area)
async def area_invalid(message: Message) -> None:
    await message.answer("لطفاً یکی از محدوده‌ها را انتخاب کن.")


@router.message(Registration.phone, F.contact)
async def phone(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer("لطفاً فقط شماره‌ی خودت را با دکمه‌ی پایین ارسال کن.")
        return
    await state.update_data(phone=contact.phone_number)
    await track_funnel_event(message.from_user.id, "phone_shared")
    await state.update_data(activities=[])
    await state.set_state(Registration.activities)
    await message.answer(
        "کدوم نوع دورهمی‌ها برات جذاب‌تره؟ می‌تونی چند مورد انتخاب کنی.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("انتخاب‌هایت را بزن و بعد ثبت انتخاب‌ها را بزن:", reply_markup=multi_select_keyboard(ACTIVITIES, [], ACTIVITIES_DONE))


@router.message(Registration.phone)
async def phone_invalid(message: Message) -> None:
    await message.answer("لطفاً با دکمه‌ی «اشتراک‌گذاری شماره خودم» شماره‌ات را ارسال کن.")


async def show_multi(callback: CallbackQuery, state: FSMContext, items: list[str], key: str, done_label: str, next_state, prompt: str) -> None:
    data = await state.get_data()
    selected = data.get(key, [])
    _, action = (callback.data or "").split(":", 1)
    if action == "done":
        if not selected:
            await callback.answer("حداقل یک مورد را انتخاب کن.", show_alert=True)
            return
        await state.set_state(next_state)
        completed_event = "activities_selected" if key == "activities" else "availability_selected"
        await track_funnel_event(callback.from_user.id, completed_event)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            prompt,
            reply_markup=reply_keyboard(
                AGE_PREFERENCES if next_state == Registration.age_preference else JOIN_REASONS,
                1,
            ),
        )
        await callback.answer()
        return
    item = items[int(action)]
    selected = [value for value in selected if value != item] if item in selected else [*selected, item]
    await state.update_data(**{key: selected})
    await callback.message.edit_reply_markup(reply_markup=multi_select_keyboard(items, selected, done_label))
    await callback.answer()


@router.callback_query(Registration.activities, F.data.startswith("multi:"))
async def activity_selection(callback: CallbackQuery, state: FSMContext) -> None:
    await show_multi(callback, state, ACTIVITIES, "activities", ACTIVITIES_DONE, Registration.age_preference, "اختلاف سنی افراد جمع چقدر برات مهمه؟")


@router.message(Registration.age_preference, F.text.in_(AGE_PREFERENCES))
async def age_preference(message: Message, state: FSMContext) -> None:
    await state.update_data(age_preference=message.text, availability=[])
    await track_funnel_event(message.from_user.id, "age_preference_selected")
    await state.set_state(Registration.availability)
    await message.answer("چه زمان‌هایی برای دورهمی آزادی؟ هر تعداد که می‌تونی انتخاب کن.", reply_markup=ReplyKeyboardRemove())
    await message.answer("انتخاب‌هایت را بزن و بعد ثبت زمان‌ها را بزن:", reply_markup=multi_select_keyboard(AVAILABILITY, [], AVAILABILITY_DONE))


@router.message(Registration.age_preference)
async def age_preference_invalid(message: Message) -> None:
    await message.answer("لطفاً یکی از گزینه‌ها را انتخاب کن.")


@router.callback_query(Registration.availability, F.data.startswith("multi:"))
async def availability_selection(callback: CallbackQuery, state: FSMContext) -> None:
    await show_multi(callback, state, AVAILABILITY, "availability", AVAILABILITY_DONE, Registration.join_reason, "بیشتر برای چی دوست داری تو این دورهمی‌ها شرکت کنی؟")


@router.message(Registration.join_reason, F.text.in_(JOIN_REASONS))
async def join_reason(message: Message, state: FSMContext) -> None:
    await state.update_data(join_reason=message.text)
    await track_funnel_event(message.from_user.id, "reason_selected")
    await state.set_state(Registration.review)
    data = await state.get_data()
    await message.answer(format_registration(data), reply_markup=reply_keyboard([FINAL_SUBMIT, RESTART], 1))


@router.message(Registration.join_reason)
async def join_reason_invalid(message: Message) -> None:
    await message.answer("لطفاً یکی از گزینه‌ها را انتخاب کن.")


@router.message(Registration.review, F.text == FINAL_SUBMIT)
async def submit(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await save_registration(message.from_user.id, message.from_user.username, data)
    await track_funnel_event(message.from_user.id, "registration_completed")
    await state.clear()
    await message.answer(
        "✅ ثبت‌نامت انجام شد.\n\nوقتی یک گروه دورهمی مناسب شکل بگیره، باهات تماس می‌گیریم. "
        "جزئیات نهایی فقط بعد از تأیید حضورت ارسال می‌شه.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Registration.review, F.text == RESTART)
async def restart(message: Message, state: FSMContext) -> None:
    await begin_registration(message, state)


@router.message(Registration.review)
async def review_invalid(message: Message) -> None:
    await message.answer("لطفاً ثبت نهایی یا شروع دوباره را انتخاب کن.")


def format_registration(data: dict, include_status: bool = False) -> str:
    status = f"\nوضعیت: {data['status']}" if include_status else ""
    return (
        "📝 مرور ثبت‌نام\n\n"
        f"اسم: {data['first_name']}\nسن: {data['age']}\nجنسیت: {data['gender']}\n"
        f"محدوده: {data['area']}\nفعالیت‌ها: {', '.join(data['activities'])}\n"
        f"ترجیح اختلاف سنی: {data['age_preference']}\n"
        f"زمان‌های آزاد: {', '.join(data['availability'])}\n"
        f"دلیل شرکت: {data['join_reason']}{status}"
    )
