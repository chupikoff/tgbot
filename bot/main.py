import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from config import settings
from handlers import router
from middlewares.auth import AuthMiddleware
from db.database import init_db, async_session
from workers.backup_worker import schedule_backups
from workers.reminder_worker import check_reminders

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    storage = RedisStorage.from_url("redis://redis:6379")
    dp = Dispatcher(storage=storage)

    dp.message.middleware(AuthMiddleware(async_session))
    dp.callback_query.middleware(AuthMiddleware(async_session))

    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)

    async def on_startup():
        asyncio.create_task(schedule_backups(bot))
        asyncio.create_task(check_reminders(bot))
        logging.info("Workers started.")

    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
