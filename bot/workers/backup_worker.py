import asyncio
import logging
import time
from aiogram import Bot
from aiogram.types import FSInputFile
from services.backup_service import backup_database, backup_configs, delete_old_backups
from config import settings

logger = logging.getLogger(__name__)


async def run_backup(bot: Bot):
    logger.info("Starting scheduled backup...")
    try:
        loop = asyncio.get_event_loop()
        db_file = await loop.run_in_executor(None, backup_database)
        configs_file = await loop.run_in_executor(None, backup_configs)
        delete_old_backups()

        for filename, caption in [
            (db_file, "🗄 База данных"),
            (configs_file, "⚙️ Конфиги"),
        ]:
            file = FSInputFile(filename)
            await bot.send_document(settings.ADMIN_TG_ID, file, caption=f"🕐 Автобэкап — {caption}")

        logger.info("Scheduled backup completed.")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        await bot.send_message(settings.ADMIN_TG_ID, f"❌ Автобэкап не удался!\n{e}")


async def schedule_backups(bot: Bot):
    while True:
        current = time.localtime()
        seconds_until_3am = (
            ((3 - current.tm_hour) % 24) * 3600
            - current.tm_min * 60
            - current.tm_sec
        )
        if seconds_until_3am <= 0:
            seconds_until_3am += 86400
        logger.info(f"Next backup in {seconds_until_3am // 3600}h {(seconds_until_3am % 3600) // 60}m")
        await asyncio.sleep(seconds_until_3am)
        await run_backup(bot)
