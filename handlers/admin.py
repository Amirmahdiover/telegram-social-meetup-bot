import csv
import io
import json

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from config import Settings
from database import get_all_registrations, get_funnel_counts


def create_admin_router(settings: Settings) -> Router:
    router = Router()

    @router.message(Command("registrations"))
    async def registrations(message: Message) -> None:
        if message.from_user.id not in settings.admin_ids:
            await message.answer("این دستور فقط برای مدیران در دسترس است.")
            return
        rows = await get_all_registrations()
        output = io.StringIO(newline="")
        columns = ["telegram_user_id", "username", "name", "age", "gender", "area", "phone", "activities", "age_preference", "availability", "join_reason", "status", "created_at"]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "telegram_user_id": row["telegram_user_id"], "username": row["telegram_username"],
                "name": row["first_name"], "age": row["age"], "gender": row["gender"],
                "area": row["area"], "phone": row["phone"],
                "activities": " | ".join(json.loads(row["activities"])),
                "age_preference": row["age_preference"],
                "availability": " | ".join(json.loads(row["availability"])),
                "join_reason": row["join_reason"], "status": row["status"], "created_at": row["created_at"],
            })
        content = ("\ufeff" + output.getvalue()).encode("utf-8")
        await message.answer_document(BufferedInputFile(content, filename="registrations.csv"), caption=f"{len(rows)} ثبت‌نام")

    @router.message(Command("funnel"))
    async def funnel(message: Message) -> None:
        if message.from_user.id not in settings.admin_ids:
            await message.answer("این دستور فقط برای مدیران در دسترس است.")
            return

        counts = await get_funnel_counts()

        def count(event_name: str) -> int:
            return counts.get(event_name, 0)

        phone_requested = count("phone_requested")
        phone_shared = count("phone_shared")
        started = count("registration_started")
        completed = count("registration_completed")
        phone_dropoff = phone_requested - phone_shared
        phone_share_rate = phone_shared / phone_requested * 100 if phone_requested else 0
        completion_rate = completed / started * 100 if started else 0
        phone_dropoff_rate = phone_dropoff / phone_requested * 100 if phone_requested else 0

        report = (
            "📊 قیف ثبت‌نام\n\n"
            f"شروع ثبت‌نام: {started}\n"
            f"تأیید ۱۸+: {count('age_confirmed')}\n"
            f"ثبت نام: {count('name_entered')}\n"
            f"ثبت سن: {count('age_entered')}\n"
            f"انتخاب جنسیت: {count('gender_selected')}\n"
            f"انتخاب محدوده: {count('area_selected')}\n\n"
            f"📱 درخواست شماره: {phone_requested}\n"
            f"📱 اشتراک شماره: {phone_shared}\n\n"
            f"انتخاب فعالیت: {count('activities_selected')}\n"
            f"انتخاب بازه سنی: {count('age_preference_selected')}\n"
            f"انتخاب زمان: {count('availability_selected')}\n"
            f"انتخاب هدف: {count('reason_selected')}\n"
            f"ثبت‌نام کامل: {completed}\n\n"
            "📉 ریزش در مرحله شماره:\n"
            f"{phone_dropoff} نفر\n{phone_dropoff_rate:.1f}%\n\n"
            "✅ نرخ اشتراک شماره:\n"
            f"{phone_share_rate:.1f}%\n\n"
            "✅ نرخ تکمیل کل ثبت‌نام:\n"
            f"{completion_rate:.1f}%"
        )
        await message.answer(report)

    return router
