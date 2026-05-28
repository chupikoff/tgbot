from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from models.user import User

router = Router()

ROLE_NAMES = {
    "owner": "👑 Владелец",
    "admin": "🔧 Администратор",
    "user": "👤 Пользователь",
    "guest": "👣 Гость",
}

COMMANDS_BY_ROLE = {
    "guest": [
        ("/start", "Информация о себе"),
    ],
    "user": [
        ("/start", "Информация о себе"),
        ("/notes", "Заметки"),
    ],
    "admin": [
        ("/start", "Информация о себе"),
        ("/notes", "Заметки"),
        ("/status", "Состояние сервера"),
        ("/torrents", "Управление торрентами"),
        ("/users", "Список пользователей"),
        ("/ban [id]", "Заблокировать пользователя"),
        ("/unban [id]", "Разблокировать пользователя"),
    ],
    "owner": [
        ("/start", "Информация о себе"),
        ("/notes", "Заметки"),
        ("/status", "Состояние сервера"),
        ("/torrents", "Управление торрентами"),
        ("/users", "Список пользователей"),
        ("/ban [id]", "Заблокировать пользователя"),
        ("/unban [id]", "Разблокировать пользователя"),
        ("/setrole [id] [роль]", "Сменить роль пользователя"),
    ],
}

@router.message(Command("start"))
async def cmd_start(message: Message, user: User):
    role_name = ROLE_NAMES.get(user.role, user.role)
    username = f"@{user.username}" if user.username else "не указан"

    commands = COMMANDS_BY_ROLE.get(user.role, COMMANDS_BY_ROLE["guest"])
    commands_text = ""
    for cmd, desc in commands:
        if cmd == "":
            commands_text += "\n"
        else:
            commands_text += f"{cmd} — {desc}\n"

    await message.answer(
        f"👋 Привет, {user.full_name}!\n\n"
        f"🆔 ID: {user.telegram_id}\n"
        f"👤 Username: {username}\n"
        f"🎭 Роль: {role_name}\n"
        f"📅 В системе с: {user.created_at.strftime('%d.%m.%Y')}\n\n"
        f"📋 Доступные команды:\n\n"
        f"{commands_text}"
    )
