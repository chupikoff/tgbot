import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from filters.roles import has_role
from services.backup_service import backup_database, backup_configs, get_backups, delete_old_backups
from config import settings

router = Router()


def backup_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💾 Бэкап БД", callback_data="backup_db")],
        [InlineKeyboardButton(text="⚙️ Бэкап конфигов", callback_data="backup_configs")],
        [InlineKeyboardButton(text="📋 Список бэкапов", callback_data="backup_list")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_backup")
async def cb_backup(callback: CallbackQuery):
    try:
        await callback.message.edit_text("💾 Бэкапы:", reply_markup=backup_menu())
    except Exception:
        await callback.message.answer("💾 Бэкапы:", reply_markup=backup_menu())


@router.callback_query(F.data == "backup_db")
async def cb_backup_db(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Создаю бэкап БД...")
    try:
        loop = asyncio.get_event_loop()
        filename = await loop.run_in_executor(None, backup_database)
        delete_old_backups()
        file = FSInputFile(filename)
        await callback.message.answer_document(file, caption="🗄 Бэкап базы данных")
        await callback.message.edit_text("✅ Бэкап БД создан.", reply_markup=back_button("menu_backup"))
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=back_button("menu_backup"))


@router.callback_query(F.data == "backup_configs")
async def cb_backup_configs(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Создаю бэкап конфигов...")
    try:
        loop = asyncio.get_event_loop()
        filename = await loop.run_in_executor(None, backup_configs)
        delete_old_backups()
        file = FSInputFile(filename)
        await callback.message.answer_document(file, caption="⚙️ Бэкап конфигов")
        await callback.message.edit_text("✅ Бэкап конфигов создан.", reply_markup=back_button("menu_backup"))
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {e}", reply_markup=back_button("menu_backup"))


@router.callback_query(F.data == "backup_list")
async def cb_backup_list(callback: CallbackQuery):
    backups = get_backups()
    if not backups:
        await callback.message.edit_text("📋 Бэкапов нет.", reply_markup=back_button("menu_backup"))
        return
    text = "📋 Бэкапы:\n\n"
    for b in backups:
        text += f"📦 {b['name']}\n{b['created']} | {b['size']} KB\n\n"
    await callback.message.edit_text(text, reply_markup=back_button("menu_backup"))
