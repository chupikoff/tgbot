from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
        buttons.append([InlineKeyboardButton(text="🌊 Торренты", callback_data="menu_torrents")])
        buttons.append([InlineKeyboardButton(text="👥 Пользователи", callback_data="menu_users")])

    if user.role == "owner":
        buttons.append([InlineKeyboardButton(text="💾 Бэкапы", callback_data="menu_backup")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def users_menu(user: User) -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_list")])
    if user.role == "owner":
        buttons.append([InlineKeyboardButton(text="🎭 Сменить роль", callback_data="users_setrole")])
    buttons.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data="users_ban")])
    buttons.append([InlineKeyboardButton(text="✅ Разблокировать", callback_data="users_unban")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")]
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
    await callback.message.edit_text("👥 Управление пользователями:", reply_markup=users_menu(user))

@router.callback_query(F.data == "users_list")
async def cb_users_list(callback: CallbackQuery, user: User, session):
    from services.user_service import get_all_users
    from handlers.admin import ROLE_NAMES as ADMIN_ROLE_NAMES
    users = await get_all_users(session)
    if not users:
        await callback.message.edit_text("Пользователей пока нет.", reply_markup=back_to_main())
        return
    text = "👥 Список пользователей:\n\n"
    for u in users:
        status = "✅" if u.is_active else "❌"
        username = f"@{u.username}" if u.username else "не указан"
        role_name = ADMIN_ROLE_NAMES.get(u.role, u.role)
        text += f"{status} {u.full_name} ({username})\n"
        text += f"   ID: {u.telegram_id} | Роль: {role_name}\n\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")]
    ]))

@router.callback_query(F.data == "users_ban")
async def cb_users_ban(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        "🚫 Введи команду для блокировки:\n/ban [telegram_id]",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")]
        ])
    )

@router.callback_query(F.data == "users_unban")
async def cb_users_unban(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        "✅ Введи команду для разблокировки:\n/unban [telegram_id]",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")]
        ])
    )

@router.callback_query(F.data == "users_setrole")
async def cb_users_setrole(callback: CallbackQuery, user: User):
    await callback.message.edit_text(
        "🎭 Введи команду для смены роли:\n/setrole [telegram_id] [роль]\n\nРоли: admin, user, guest",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")]
        ])
    )
