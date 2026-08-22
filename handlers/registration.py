from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, ReplyKeyboardRemove

from database import get_registration, save_registration, track_funnel_event
from keyboards import FINAL_SUBMIT, JOIN_REASONS, NO, RESTART, START_REGISTRATION, YES, reply_keyboard
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
    await state.set_state(Registration.join_reason)
    await message.answer("بیشتر برای چی دوست داری تو این دورهمی شرکت کنی؟", reply_markup=reply_keyboard(JOIN_REASONS, 1))


@router.message(Registration.join_reason, F.text.in_(JOIN_REASONS))
async def join_reason(message: Message, state: FSMContext) -> None:
    await state.update_data(join_reason=message.text)
    await track_funnel_event(message.from_user.id, "join_reason_selected")
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
    referral_link = ""
    try:
        bot_username = (await message.bot.get_me()).username
        if bot_username:
            referral_link = f"\nhttps://t.me/{bot_username}"
    except TelegramAPIError:
        pass
    await message.answer(
        "ثبت‌نامت انجام شد ✅\n\n"
        "این ثبت‌نام فقط یعنی برای شرکت در دورهمی علاقه‌مندی و به معنی حضور قطعی نیست.\n\n"
        "نتیجه انتخاب افراد سه‌شنبه از طریق همین بات اعلام میشه.\n\n"
        "📅 دورهمی: پنجشنبه\n"
        "⏰ ساعت: ۱۸ تا ۲۰\n"
        "📍 کافه دایموند\n"
        "محدوده: منطقه ۶ تهران، خیابان فلاح‌پور\n\n"
        "اگر انتخاب بشی، قبل از دورهمی پیام تأیید و لوکیشن دقیق برات از طریق همین بات ارسال میشه.\n\n"
        "اگه کسی رو می‌شناسی که فکر می‌کنی پایه چنین دورهمی‌ایه، لینک جمعینو رو براش بفرست 👇"
        f"{referral_link}",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Registration.review, F.text == RESTART)
async def restart(message: Message, state: FSMContext) -> None:
    await begin_registration(message, state)


@router.message(Registration.review)
async def review_invalid(message: Message) -> None:
    await message.answer("لطفاً ثبت نهایی یا شروع دوباره را انتخاب کن.")


def format_registration(data: dict, include_status: bool = False) -> str:
    fields = [
        ("اسم", data.get("first_name")),
        ("سن", data.get("age")),
        ("جنسیت", data.get("gender")),
        ("محدوده", data.get("area")),
        ("فعالیت‌ها", ", ".join(data.get("activities") or [])),
        ("ترجیح اختلاف سنی", data.get("age_preference")),
        ("زمان‌های آزاد", ", ".join(data.get("availability") or [])),
        ("دلیل شرکت", data.get("join_reason")),
    ]
    lines = [f"{label}: {value}" for label, value in fields if value]
    if include_status and data.get("status"):
        lines.append(f"وضعیت: {data['status']}")
    return "📝 مرور ثبت‌نام\n\n" + "\n".join(lines)
