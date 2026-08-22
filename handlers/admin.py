import csv
import io
import json

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from config import Settings
from database import add_event_member, create_event, get_all_registrations, get_event, get_event_members, get_funnel_counts, get_invited_members, update_event_member_status
from keyboards import event_invitation_keyboard, event_send_confirmation_keyboard
from states import EventCreation


def create_admin_router(settings: Settings) -> Router:
    router = Router()

    async def require_admin(message: Message) -> bool:
        if message.from_user.id in settings.admin_ids:
            return True
        await message.answer("این دستور فقط برای مدیران در دسترس است.")
        return False

    @router.message(Command("registrations"))
    async def registrations(message: Message) -> None:
        if not await require_admin(message):
            return
        rows = await get_all_registrations()
        output = io.StringIO(newline="")
        columns = ["telegram_user_id", "username", "name", "age", "gender", "area", "phone", "activities", "age_preference", "availability", "join_reason", "status", "created_at"]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({"telegram_user_id": row["telegram_user_id"], "username": row["telegram_username"], "name": row["first_name"], "age": row["age"], "gender": row["gender"], "area": row["area"], "phone": row["phone"], "activities": " | ".join(json.loads(row["activities"] or "[]")), "age_preference": row["age_preference"], "availability": " | ".join(json.loads(row["availability"] or "[]")), "join_reason": row["join_reason"], "status": row["status"], "created_at": row["created_at"]})
        content = ("\ufeff" + output.getvalue()).encode("utf-8")
        await message.answer_document(BufferedInputFile(content, filename="registrations.csv"), caption=f"{len(rows)} ثبت‌نام")

    @router.message(Command("users"))
    async def users(message: Message) -> None:
        if not await require_admin(message):
            return
        rows = await get_all_registrations()
        if not rows:
            await message.answer("کاربر ثبت‌نام‌شده‌ای وجود ندارد.")
            return
        lines = ["Registered users", ""]
        for index, user in enumerate(rows, start=1):
            lines.extend([
                f"{index}. {user['first_name']}",
                f"Telegram ID: {user['telegram_user_id']}",
                "",
            ])
        await message.answer("\n".join(lines).rstrip())

    @router.message(Command("funnel"))
    async def funnel(message: Message) -> None:
        if not await require_admin(message):
            return
        counts = await get_funnel_counts()
        count = lambda name: counts.get(name, 0)
        started, completed = count("registration_started"), count("registration_completed")
        report = (
            "📊 قیف ثبت‌نام\n\n"
            f"شروع ثبت‌نام: {started}\nتأیید ۱۸+: {count('age_confirmed')}\nثبت نام: {count('name_entered')}\nثبت سن: {count('age_entered')}\nانتخاب هدف: {count('join_reason_selected')}\nثبت‌نام کامل: {completed}\n\n"
            f"✅ نرخ تکمیل کل ثبت‌نام:\n{(completed / started * 100 if started else 0):.1f}%"
        )
        await message.answer(report)

    @router.message(Command("create_event"))
    async def create_event_command(message: Message, state: FSMContext) -> None:
        if not await require_admin(message): return
        await state.clear()
        await state.set_state(EventCreation.title)
        await message.answer("عنوان دورهمی را بفرست.")

    @router.message(EventCreation.title)
    async def event_title(message: Message, state: FSMContext) -> None:
        await advance(message, state, "title", EventCreation.date, "تاریخ دورهمی را بفرست (مثلاً ۱۴۰۵/۰۵/۲۷).")

    @router.message(EventCreation.date)
    async def event_date(message: Message, state: FSMContext) -> None:
        await advance(message, state, "date", EventCreation.time, "ساعت دورهمی را بفرست (مثلاً ۱۹:۰۰).")

    @router.message(EventCreation.time)
    async def event_time(message: Message, state: FSMContext) -> None:
        await advance(message, state, "time", EventCreation.location_name, "نام محل را بفرست.")

    @router.message(EventCreation.location_name)
    async def event_location_name(message: Message, state: FSMContext) -> None:
        await advance(message, state, "location_name", EventCreation.location_address, "آدرس محل را بفرست.")

    @router.message(EventCreation.location_address)
    async def event_location_address(message: Message, state: FSMContext) -> None:
        await advance(message, state, "location_address", EventCreation.latitude, "عرض جغرافیایی را بفرست، یا برای رد کردن این مرحله «-» بنویس.")

    @router.message(EventCreation.latitude)
    async def event_latitude(message: Message, state: FSMContext) -> None:
        value = (message.text or "").strip()
        if value == "-":
            await state.update_data(latitude=None, longitude=None)
            await state.set_state(EventCreation.message)
            await message.answer("پیام دعوت را بفرست.")
            return
        try: latitude = float(value)
        except ValueError:
            await message.answer("عرض جغرافیایی نامعتبر است؛ عدد بفرست یا «-» بنویس.")
            return
        if not -90 <= latitude <= 90:
            await message.answer("عرض جغرافیایی باید بین ۹۰- و ۹۰ باشد.")
            return
        await state.update_data(latitude=latitude)
        await state.set_state(EventCreation.longitude)
        await message.answer("طول جغرافیایی را بفرست.")

    @router.message(EventCreation.longitude)
    async def event_longitude(message: Message, state: FSMContext) -> None:
        try: longitude = float((message.text or "").strip())
        except ValueError:
            await message.answer("طول جغرافیایی نامعتبر است؛ یک عدد بفرست.")
            return
        if not -180 <= longitude <= 180:
            await message.answer("طول جغرافیایی باید بین ۱۸۰- و ۱۸۰ باشد.")
            return
        await state.update_data(longitude=longitude)
        await state.set_state(EventCreation.message)
        await message.answer("پیام دعوت را بفرست.")

    @router.message(EventCreation.message)
    async def event_message(message: Message, state: FSMContext) -> None:
        value = (message.text or "").strip()
        if not value:
            await message.answer("پیام دعوت نمی‌تواند خالی باشد.")
            return
        await state.update_data(message=value)
        event_id = await create_event(await state.get_data())
        await state.clear()
        await message.answer(f"✅ دورهمی با شناسه {event_id} ذخیره شد.")

    @router.message(Command("select_user"))
    async def select_user(message: Message) -> None:
        if not await require_admin(message): return
        parts = (message.text or "").split()
        if len(parts) != 3:
            await message.answer("استفاده: /select_user <user_id> <event_id>")
            return
        try: user_id, event_id = int(parts[1]), int(parts[2])
        except ValueError:
            await message.answer("user_id و event_id باید عدد باشند.")
            return
        if await add_event_member(event_id, user_id):
            await message.answer(f"✅ کاربر {user_id} به دورهمی {event_id} دعوت شد.")
        else:
            await message.answer("کاربر ثبت‌نام‌شده یا دورهمی با این شناسه پیدا نشد.")

    @router.message(Command("select"))
    async def select(message: Message) -> None:
        if not await require_admin(message):
            return
        parts = (message.text or "").split()
        if len(parts) != 3:
            await message.answer("استفاده: /select <user_number> <event_id>")
            return
        try:
            user_number, event_id = int(parts[1]), int(parts[2])
        except ValueError:
            await message.answer("user_number و event_id باید عدد باشند.")
            return
        users = await get_all_registrations()
        if not 1 <= user_number <= len(users):
            await message.answer("شماره کاربر نامعتبر است. ابتدا /users را اجرا کن.")
            return
        user = users[user_number - 1]
        if await add_event_member(event_id, user["telegram_user_id"]):
            await message.answer(f"✅ {user['first_name']} به دورهمی {event_id} دعوت شد.")
        else:
            await message.answer("دورهمی با این شناسه پیدا نشد.")

    @router.message(Command("preview_event"))
    async def preview_event(message: Message) -> None:
        if not await require_admin(message):
            return
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("Usage: /preview_event <event_id>")
            return
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.answer("event_id must be a number.")
            return
        event = await get_event(event_id)
        if not event:
            await message.answer("Event not found.")
            return
        invited_count = len(await get_invited_members(event_id))
        await message.answer(format_event_preview(event_id, event, invited_count))
        if event["latitude"] is not None and event["longitude"] is not None:
            await message.bot.send_location(message.chat.id, event["latitude"], event["longitude"])

    @router.message(Command("send_event"))
    async def send_event(message: Message) -> None:
        if not await require_admin(message): return
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("استفاده: /send_event <event_id>")
            return
        try: event_id = int(parts[1])
        except ValueError:
            await message.answer("event_id باید عدد باشد.")
            return
        event = await get_event(event_id)
        if not event:
            await message.answer("دورهمی با این شناسه پیدا نشد.")
            return
        invited_count = len(await get_invited_members(event_id))
        await message.answer(
            format_event_preview(event_id, event, invited_count),
            reply_markup=event_send_confirmation_keyboard(event_id),
        )
        return
        delivered = failed = 0
        for user_id in await get_invited_members(event_id):
            try:
                await message.bot.send_message(user_id, format_event_invitation_with_support(event), reply_markup=event_invitation_keyboard(event_id))
                if event["latitude"] is not None and event["longitude"] is not None:
                    await message.bot.send_location(user_id, event["latitude"], event["longitude"])
                delivered += 1
            except TelegramAPIError:
                failed += 1
        await message.answer(f"دعوت‌نامه برای {delivered} نفر ارسال شد. ناموفق: {failed}")

    @router.message(Command("event_members"))
    async def event_members(message: Message) -> None:
        if not await require_admin(message):
            return
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("استفاده: /event_members <event_id>")
            return
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.answer("event_id باید عدد باشد.")
            return
        if not await get_event(event_id):
            await message.answer("دورهمی با این شناسه پیدا نشد.")
            return
        members = await get_event_members(event_id)
        if not members:
            await message.answer(f"Event #{event_id}\n\nکاربری برای این دورهمی انتخاب نشده است.")
            return
        lines = [f"Event #{event_id}", ""]
        for index, member in enumerate(members, start=1):
            lines.extend([
                f"{index}. {member['first_name']}",
                f"Telegram ID: {member['user_id']}",
                f"Status: {member['status']}",
                "",
            ])
        await message.answer("\n".join(lines).rstrip())

    @router.message(Command("event_users"))
    async def event_users(message: Message) -> None:
        if not await require_admin(message):
            return
        parts = (message.text or "").split()
        if len(parts) != 2:
            await message.answer("استفاده: /event_users <event_id>")
            return
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.answer("event_id باید عدد باشد.")
            return
        if not await get_event(event_id):
            await message.answer("دورهمی با این شناسه پیدا نشد.")
            return
        members = await get_event_members(event_id)
        if not members:
            await message.answer(f"Event #{event_id}\n\nکاربری برای این دورهمی انتخاب نشده است.")
            return
        lines = [f"Event #{event_id}", ""]
        for index, member in enumerate(members, start=1):
            lines.extend([
                f"{index}. {member['first_name']}",
                f"Telegram ID: {member['user_id']}",
                f"Status: {member['status']}",
                "",
            ])
        await message.answer("\n".join(lines).rstrip())

    @router.callback_query(F.data.startswith("event_send:"))
    async def event_send_confirmation(callback: CallbackQuery) -> None:
        if callback.from_user.id not in settings.admin_ids:
            await callback.answer("Admin access required.", show_alert=True)
            return
        try:
            _, event_id_text, action = (callback.data or "").split(":")
            event_id = int(event_id_text)
        except (TypeError, ValueError):
            await callback.answer("Invalid action.", show_alert=True)
            return
        if action == "cancel":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("Sending cancelled.")
            return
        if action != "confirm":
            await callback.answer("Invalid action.", show_alert=True)
            return
        event = await get_event(event_id)
        if not event:
            await callback.answer("Event not found.", show_alert=True)
            return
        await callback.message.edit_reply_markup(reply_markup=None)
        delivered = failed = 0
        for user_id in await get_invited_members(event_id):
            try:
                await callback.message.bot.send_message(
                    user_id,
                    format_event_invitation_with_support(event),
                    reply_markup=event_invitation_keyboard(event_id),
                )
                if event["latitude"] is not None and event["longitude"] is not None:
                    await callback.message.bot.send_location(user_id, event["latitude"], event["longitude"])
                delivered += 1
            except TelegramAPIError:
                failed += 1
        await callback.answer("Invitations sent.")
        await callback.message.answer(f"Invitations sent: {delivered}. Failed: {failed}")

    @router.callback_query(F.data.startswith("event_response:"))
    async def event_response(callback: CallbackQuery) -> None:
        try:
            _, event_id_text, status = (callback.data or "").split(":")
            event_id = int(event_id_text)
        except (TypeError, ValueError):
            await callback.answer("دکمه نامعتبر است.", show_alert=True)
            return
        if status not in {"confirmed", "declined"} or not await update_event_member_status(event_id, callback.from_user.id, status):
            await callback.answer("این دعوت‌نامه برای شما نیست.", show_alert=True)
            return
        response = "✅ حضورت ثبت شد. می‌بینیمت!" if status == "confirmed" else "❌ عدم حضورت ثبت شد."
        await callback.answer(response)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(response)

    return router


async def advance(message: Message, state: FSMContext, field: str, next_state, prompt: str) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("این مورد نمی‌تواند خالی باشد.")
        return
    await state.update_data(**{field: value})
    await state.set_state(next_state)
    await message.answer(prompt)


def format_event_invitation(event: dict) -> str:
    return "سلام 👋\n\nبرای دورهمی این هفته انتخاب شدی 🎉\n\n" + f"📅 {event['date']}\n⏰ {event['time']}\n\n📍 {event['location_name']}\n{event['location_address']}\n\n{event['message']}"


SUPPORT_TEXT = (
    "اگر سوالی داشتی یا مشکلی پیش آمد، از طریق تلگرام پیام بده:\n"
    "https://t.me/amirmahq"
)


def format_event_invitation_with_support(event: dict) -> str:
    return (
        "سلام 👋\n\n"
        "برای دورهمی این هفته انتخاب شدی 🎉\n\n"
        f"📍 {event['location_name']}\n"
        f"📅 {event['date']}\n"
        f"⏰ {event['time']}\n\n"
        f"Address:\n{event['location_address']}\n\n"
        f"{event['message']}\n\n"
        f"{SUPPORT_TEXT}"
    )


def format_event_preview(event_id: int, event: dict, invited_count: int) -> str:
    coordinates = (
        f"{event['latitude']},{event['longitude']}"
        if event['latitude'] is not None and event['longitude'] is not None
        else "Not provided"
    )
    return (
        f"Preview Event #{event_id}\n\n"
        f"Title:\n{event['title']}\n\n"
        f"Date:\n{event['date']}\n\n"
        f"Time:\n{event['time']}\n\n"
        f"Location:\n{event['location_name']}\n\n"
        f"Address:\n{event['location_address']}\n\n"
        f"Coordinates:\n{coordinates}\n\n"
        f"Invited users:\n{invited_count}\n\n"
        f"Message:\n\n{format_event_invitation_with_support(event)}"
    )
