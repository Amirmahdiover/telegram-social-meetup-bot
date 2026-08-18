import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import get_settings
from database import init_db
from handlers.admin import create_admin_router
from handlers.registration import router as registration_router


async def main() -> None:
    settings = get_settings()
    await init_db()
    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(create_admin_router(settings))
    dispatcher.include_router(registration_router)
    await bot.delete_webhook(drop_pending_updates=False)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
