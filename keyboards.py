from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

START_REGISTRATION = "شروع ثبت‌نام 🚀"
YES = "✅ بله"
NO = "❌ خیر"
FINAL_SUBMIT = "✅ ثبت نهایی"
RESTART = "🔄 شروع دوباره"
ACTIVITIES_DONE = "ثبت انتخاب‌ها ✅"
AVAILABILITY_DONE = "ثبت زمان‌ها ✅"

GENDERS = ["👨 مرد", "👩 زن"]
AREAS = ["غرب", "شرق", "مرکز", "شمال", "جنوب", "فرقی نمی‌کنه"]
ACTIVITIES = [
    "☕ کافه و گفتگو", "🎲 کافه + بردگیم",
]
AGE_PREFERENCES = ["حدود ±۲ سال", "حدود ±۴ سال", "حدود ±۶ سال", "سن خیلی مهم نیست"]
AVAILABILITY = [
    "پنجشنبه ۱۷ تا ۲۰", "پنجشنبه ۲۰ تا ۲۳", "جمعه ۱۵ تا ۱۸",
    "جمعه ۱۸ تا ۲۱", "جمعه ۲۰ تا ۲۳",
]
JOIN_REASONS = [
    "👥 آشنا شدن با آدم‌های جدید", "🤝 پیدا کردن دوست جدید",
    "🎉 تفریح و تجربه جدید", "🎯 پیدا کردن همراه برای فعالیت‌های مشترک",
    "ترکیبی از این‌ها",
]
SOCIAL_WARMUP_OPTIONS = {
    "زود گرم می‌گیرم": "quick_warmup",
    "یکم زمان می‌خوام": "needs_time",
    "بیشتر شنونده‌ام": "listener",
}
MEETUP_STYLE_OPTIONS = {
    "بیشتر گپ و آشنایی": "conversation",
    "بیشتر بازی": "games",
    "ترکیبی از هر دو": "balanced",
}
CONVERSATION_INITIATIVE_OPTIONS = {"زیاد": "high", "متوسط": "medium", "کم": "low"}
SOCIAL_VALUE_LABELS = {
    **{value: label for label, value in SOCIAL_WARMUP_OPTIONS.items()},
    **{value: label for label, value in MEETUP_STYLE_OPTIONS.items()},
    **{value: label for label, value in CONVERSATION_INITIATIVE_OPTIONS.items()},
}


def reply_keyboard(options: list[str], columns: int = 2, *, resize: bool = True) -> ReplyKeyboardMarkup:
    rows = [options[index:index + columns] for index in range(0, len(options), columns)]
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=item) for item in row] for row in rows], resize_keyboard=resize)


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 اشتراک‌گذاری شماره خودم", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def multi_select_keyboard(items: list[str], selected: list[str], done_label: str):
    builder = InlineKeyboardBuilder()
    for index, item in enumerate(items):
        prefix = "✅ " if item in selected else "▫️ "
        builder.button(text=prefix + item, callback_data=f"multi:{index}")
    builder.adjust(1)
    builder.button(text=done_label, callback_data="multi:done")
    return builder.as_markup()


def event_invitation_keyboard(event_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ میام", callback_data=f"event_response:{event_id}:confirmed")
    builder.button(text="❌ نمی‌تونم بیام", callback_data=f"event_response:{event_id}:declined")
    builder.adjust(1)
    return builder.as_markup()


def event_send_confirmation_keyboard(event_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm Send", callback_data=f"event_send:{event_id}:confirm")
    builder.button(text="❌ Cancel", callback_data=f"event_send:{event_id}:cancel")
    builder.adjust(1)
    return builder.as_markup()


def funnel_reset_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm reset", callback_data="funnel_reset:confirm")
    builder.button(text="❌ Cancel", callback_data="funnel_reset:cancel")
    builder.adjust(1)
    return builder.as_markup()
