import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from models.user import User
from services.backup_service import backup_configs, backup_database, get_backups, delete_old_backups
from config import settings

router = Router()

def is_owner(user: User) -> bool:
    return user.role == "owner"

def backup_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗄 Бэкап базы данных", callback_data="backup_db")],
        [InlineKeyboardButton(text="⚙️ Бэкап конфигов", callback_data="backup_configs")],
        [InlineKeyboardButton(text="🔄 Полный бэкап", callback_data="backup_full")],
        [InlineKeyboardButton(text="📋 Список бэкапов", callback_data="backup_list")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

@router.message(Command("backup"))
async def cmd_backup(message: Message, user: User):
    if not is_owner(user):
        await message.answer("⛔ Только для владельца.")
        return
    await message.answer("💾 Меню бэкапов:", reply_markup=backup_menu())

@router.callback_query(F.data == "backup_main")
async def cb_backup_main(callback: CallbackQuery, user: User):
    try:
        await callback.message.edit_text("💾 Меню бэкапов:", reply_markup=backup_menu())
    except Exception:
        await callback.message.answer("💾 Меню бэкапов:", reply_markup=backup_menu())

@router.callback_query(F.data == "backup_db")
async def cb_backup_db(callback: CallbackQuery, user: User):
    await callback.message.edit_text("⏳ Создаю бэкап базы данных...")
    try:
        loop = asyncio.get_event_loop()
        filename = await loop.run_in_executor(
            None,
            lambda: backup_database(
                settings.POSTGRES_USER,
                settings.POSTGRES_DB,
                settings.POSTGRES_PASSWORD
            )
        )
        file = FSInputFile(filename)
        await callback.message.delete()
        await callback.message.answer_document(
            file,
            caption="✅ Бэкап базы данных готов!",
            reply_markup=back_button("backup_main")
        )
        delete_old_backups()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=back_button("backup_main")
        )

@router.callback_query(F.data == "backup_configs")
async def cb_backup_configs(callback: CallbackQuery, user: User):
    await callback.message.edit_text("⏳ Создаю бэкап конфигов...")
    try:
        loop = asyncio.get_event_loop()
        filename = await loop.run_in_executor(None, backup_configs)
        file = FSInputFile(filename)
        await callback.message.delete()
        await callback.message.answer_document(
            file,
            caption="✅ Бэкап конфигов готов!",
            reply_markup=back_button("backup_main")
        )
        delete_old_backups()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=back_button("backup_main")
        )

@router.callback_query(F.data == "backup_full")
async def cb_backup_full(callback: CallbackQuery, user: User):
    await callback.message.edit_text("⏳ Создаю полный бэкап...")
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
        await callback.message.delete()
        await callback.message.answer_document(
            FSInputFile(db_file),
            caption="✅ База данных"
        )
        await callback.message.answer_document(
            FSInputFile(configs_file),
            caption="✅ Конфиги",
            reply_markup=back_button("backup_main")
        )
        delete_old_backups()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=back_button("backup_main")
        )

@router.callback_query(F.data == "backup_list")
async def cb_backup_list(callback: CallbackQuery, user: User):
    backups = get_backups()
    if not backups:
        await callback.message.edit_text(
            "📋 Бэкапов пока нет.",
            reply_markup=back_button("backup_main")
        )
        return
    text = "📋 Последние бэкапы:\n\n"
    for b in backups[:10]:
        text += f"📦 {b['name']}\n"
        text += f"   📅 {b['created']} | 💾 {b['size']} KB\n\n"
    await callback.message.edit_text(text, reply_markup=back_button("backup_main"))
