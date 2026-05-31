from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

router = Router()

ROLE_NAMES = {
    "owner": "👑 Владелец",
    "admin": "🔧 Администратор",
    "user": "👤 Пользователь",
    "guest": "👣 Гость",
}

def main_menu(user: User) -> InlineKeyboardMarkup:
    buttons = []
    if user.role in ["owner", "admin", "user"]:
        buttons.append([InlineKeyboardButton(text="📒 Заметки", callback_data="menu_notes")])
        buttons.append([InlineKeyboardButton(text="🎬 Медиатека", callback_data="menu_media")])
    if user.role in ["admin", "owner"]:
        buttons.append([InlineKeyboardButton(text="🖥 Состояние сервера", callback_data="menu_status")])
        buttons.append([InlineKeyboardButton(text="⚙️ Сервисы", callback_data="menu_services")])
        buttons.append([InlineKeyboardButton(text="🐳 Docker", callback_data="menu_docker")])
        buttons.append([InlineKeyboardButton(text="🌊 Торренты", callback_data="menu_torrents")])
        buttons.append([InlineKeyboardButton(text="👥 Пользователи", callback_data="menu_users")])
    if user.role == "owner":
        buttons.append([InlineKeyboardButton(text="💾 Бэкапы", callback_data="menu_backup")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")]
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message, user: User):
    role_name = ROLE_NAMES.get(user.role, user.role)
    username = f"@{user.username}" if user.username else "не указан"
    await message.answer(
        f"👋 Привет, {user.full_name}!\n\n"
        f"🆔 ID: {user.telegram_id}\n"
        f"👤 Username: {username}\n"
        f"🎭 Роль: {role_name}\n"
        f"📅 В системе с: {user.created_at.strftime('%d.%m.%Y')}",
        reply_markup=main_menu(user)
    )

@router.callback_query(F.data == "menu_main")
async def cb_main_menu(callback: CallbackQuery, user: User):
    role_name = ROLE_NAMES.get(user.role, user.role)
    username = f"@{user.username}" if user.username else "не указан"
    await callback.message.edit_text(
        f"👋 Привет, {user.full_name}!\n\n"
        f"🆔 ID: {user.telegram_id}\n"
        f"👤 Username: {username}\n"
        f"🎭 Роль: {role_name}\n"
        f"📅 В системе с: {user.created_at.strftime('%d.%m.%Y')}",
        reply_markup=main_menu(user)
    )

@router.callback_query(F.data == "menu_notes")
async def cb_menu_notes(callback: CallbackQuery, user: User):
    from handlers.notes import main_menu as notes_menu
    await callback.message.edit_text("📒 Меню заметок:", reply_markup=notes_menu())

@router.callback_query(F.data == "menu_media")
async def cb_menu_media(callback: CallbackQuery, user: User):
    from handlers.media import media_menu
    await callback.message.edit_text("🎬 Медиатека:", reply_markup=media_menu())

@router.callback_query(F.data == "menu_status")
async def cb_menu_status(callback: CallbackQuery, user: User):
    from services.monitoring import format_status_message
    status = format_status_message()
    await callback.message.edit_text(status, reply_markup=back_to_main())

@router.callback_query(F.data == "menu_services")
async def cb_menu_services(callback: CallbackQuery, user: User):
    from handlers.services import services_menu
    await callback.message.edit_text("⚙️ Управление сервисами:", reply_markup=services_menu())

@router.callback_query(F.data == "menu_docker")
async def cb_menu_docker(callback: CallbackQuery, user: User):
    from handlers.docker_containers import docker_menu
    await callback.message.edit_text("🐳 Docker контейнеры:", reply_markup=docker_menu())

@router.callback_query(F.data == "menu_torrents")
async def cb_menu_torrents(callback: CallbackQuery, user: User):
    from handlers.torrents import torrent_menu
    await callback.message.edit_text("🌊 Меню торрентов:", reply_markup=torrent_menu())

@router.callback_query(F.data == "menu_backup")
async def cb_menu_backup(callback: CallbackQuery, user: User):
    from handlers.backup import backup_menu
    await callback.message.edit_text("💾 Меню бэкапов:", reply_markup=backup_menu())

@router.callback_query(F.data == "menu_users")
async def cb_menu_users(callback: CallbackQuery, user: User):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    from handlers.admin import users_menu
    await callback.message.edit_text("👥 Управление пользователями:", reply_markup=users_menu(user))
