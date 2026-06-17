from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User

router = Router()

ROLE_NAMES = {
    "guest": "👣 Гость",
    "user": "👤 Пользователь",
    "admin": "🔧 Администратор",
    "owner": "👑 Владелец",
}


def main_menu(user: User) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📝 Заметки", callback_data="menu_notes"),
            InlineKeyboardButton(text="🎬 Медиатека", callback_data="menu_media"),
        ],
        [
            InlineKeyboardButton(text="✅ Задачи", callback_data="menu_tasks"),
            InlineKeyboardButton(text="⏰ Напоминания", callback_data="menu_reminders"),
        ],
        [
            InlineKeyboardButton(text="📥 Скачать видео", callback_data="menu_youtube"),
        ],
    ]

    if user.role in ["admin", "owner"]:
        buttons.append([
            InlineKeyboardButton(text="📊 Мониторинг", callback_data="menu_monitoring"),
            InlineKeyboardButton(text="🌊 Торренты", callback_data="menu_torrents"),
        ])
        buttons.append([
            InlineKeyboardButton(text="🐳 Docker", callback_data="menu_docker"),
            InlineKeyboardButton(text="💾 Бэкап", callback_data="menu_backup"),
        ])
        buttons.append([
            InlineKeyboardButton(text="👥 Пользователи", callback_data="menu_users"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def start_text(user: User) -> str:
    role_name = ROLE_NAMES.get(user.role, user.role)
    username = f"@{user.username}" if user.username else "не указан"
    return (
        f"👋 Привет, {user.full_name}!\n\n"
        f"👤 {username}\n"
        f"🎭 {role_name}"
    )


@router.message(Command("start"))
async def cmd_start(message: Message, user: User):
    if user.role == "guest":
        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            f"⏳ Твой запрос отправлен администратору. Ожидай доступа."
        )
        return
    from redis.asyncio import Redis
    redis = Redis.from_url("redis://redis:6379")
    msg = await message.answer(start_text(user), reply_markup=main_menu(user))
    await redis.set(f"last_msg:{user.telegram_id}", msg.message_id)
    await redis.close()


@router.callback_query(F.data == "menu_main")
async def cb_main_menu(callback: CallbackQuery, user: User):
    from redis.asyncio import Redis
    redis = Redis.from_url("redis://redis:6379")
    try:
        await callback.message.edit_text(start_text(user), reply_markup=main_menu(user))
        await redis.set(f"last_msg:{user.telegram_id}", callback.message.message_id)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        msg = await callback.message.answer(start_text(user), reply_markup=main_menu(user))
        await redis.set(f"last_msg:{user.telegram_id}", msg.message_id)
    finally:
        await redis.close()
