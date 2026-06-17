import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.database import async_session
from services.reminder_service import get_pending_reminders, mark_sent

logger = logging.getLogger(__name__)


async def check_reminders(bot: Bot):
    while True:
        try:
            async with async_session() as session:
                reminders = await get_pending_reminders(session)
                for reminder in reminders:
                    try:
                        # Удаляем предыдущее сообщение с главным меню
                        from redis.asyncio import Redis
                        redis = Redis.from_url("redis://redis:6379")
                        last_msg_id = await redis.get(f"last_msg:{reminder.owner_id}")
                        if last_msg_id:
                            try:
                                await bot.delete_message(reminder.owner_id, int(last_msg_id))
                            except Exception:
                                pass
                        await redis.close()

                        markup = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="📋 Главное меню", callback_data="menu_main")]
                        ])
                        await bot.send_message(
                            reminder.owner_id,
                            f"⏰ Напоминание:\n\n{reminder.text}",
                            reply_markup=markup
                        )
                        await mark_sent(session, reminder)
                    except Exception as e:
                        logger.error(f"Failed to send reminder {reminder.id}: {e}")
        except Exception as e:
            logger.error(f"Reminder worker error: {e}")
        await asyncio.sleep(60)
