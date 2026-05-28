import asyncio
import logging
from aiogram import Bot
from services.backup_service import backup_configs, backup_database, delete_old_backups
from config import settings

logger = logging.getLogger(__name__)

async def run_backup(bot: Bot):
    logger.info("Starting scheduled backup...")
    try:
        loop = asyncio.get_event_loop()

        db_file = await loop.run_in_executor(
            None,
            lambda: backup_database(
                settings.POSTGRES_USER,
                settings.POSTGRES_DB,
                settings.POSTGRES_PASSWORD
            )
        )

        configs_file = await loop.run_in_executor(None, backup_configs)

        from aiogram.types import FSInputFile
        for filename, caption in [
            (db_file, "🗄 База данных"),
            (configs_file, "⚙️ Конфиги"),
        ]:
            file = FSInputFile(filename)
            await bot.send_document(
                settings.ADMIN_TG_ID,
                file,
                caption=f"🕐 Автобэкап — {caption}"
            )

        delete_old_backups()
        logger.info("Scheduled backup completed successfully.")

    except Exception as e:
        logger.error(f"Scheduled backup failed: {e}", exc_info=True)
        await bot.send_message(
            settings.ADMIN_TG_ID,
            f"❌ Автобэкап не удался!\n{str(e)}"
        )

async def schedule_backups(bot: Bot):
    while True:
        now = asyncio.get_event_loop().time()
        import time
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
