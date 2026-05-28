from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from models.user import User
from services.user_service import get_all_users, set_user_role, set_user_active, get_user
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

ALLOWED_ROLES = ["admin", "user", "guest"]
ROLE_NAMES = {
    "owner": "👑 Владелец",
    "admin": "🔧 Администратор",
    "user": "👤 Пользователь",
    "guest": "👣 Гость",
}

def is_owner(user: User) -> bool:
    return user.role == "owner"

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

@router.message(Command("users"))
async def cmd_users(message: Message, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await message.answer("⛔ Недостаточно прав.")
        return

    users = await get_all_users(session)
    if not users:
        await message.answer("Пользователей пока нет.")
        return

    text = "👥 Список пользователей:\n\n"
    for u in users:
        status = "✅" if u.is_active else "❌"
        username = f"@{u.username}" if u.username else "не указан"
        role_name = ROLE_NAMES.get(u.role, u.role)
        text += f"{status} {u.full_name} ({username})\n"
        text += f"   ID: {u.telegram_id} | Роль: {role_name}\n\n"

    await message.answer(text)

@router.message(Command("setrole"))
async def cmd_setrole(message: Message, user: User, session: AsyncSession):
    if not is_owner(user):
        await message.answer("⛔ Только владелец может менять роли.")
        return

    args = message.text.split()[1:]
    if len(args) != 2:
        await message.answer("Использование: /setrole [telegram_id] [роль]\nРоли: admin, user, guest")
        return

    try:
        target_id = int(args[0])
        role = args[1]
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: /setrole 123456789 admin")
        return

    if role not in ALLOWED_ROLES:
        await message.answer("❌ Неверная роль. Доступные: admin, user, guest")
        return

    updated = await set_user_role(session, target_id, role)
    if updated:
        role_name = ROLE_NAMES.get(role, role)
        await message.answer(f"✅ Роль пользователя {target_id} изменена на {role_name}")
    else:
        await message.answer("❌ Пользователь не найден.")

@router.message(Command("ban"))
async def cmd_ban(message: Message, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await message.answer("⛔ Недостаточно прав.")
        return

    args = message.text.split()[1:]
    if len(args) != 1:
        await message.answer("Использование: /ban [telegram_id]")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: /ban 123456789")
        return

    if target_id == message.from_user.id:
        await message.answer("❌ Нельзя заблокировать самого себя.")
        return

    target = await get_user(session, target_id)
    if not target:
        await message.answer("❌ Пользователь не найден.")
        return

    if target.role == "owner":
        await message.answer("⛔ Нельзя заблокировать владельца.")
        return

    if target.role == "admin" and user.role != "owner":
        await message.answer("⛔ Администратор не может банить другого администратора.")
        return

    await set_user_active(session, target_id, False)
    await message.answer(f"✅ Пользователь {target_id} заблокирован.")

@router.message(Command("unban"))
async def cmd_unban(message: Message, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await message.answer("⛔ Недостаточно прав.")
        return

    args = message.text.split()[1:]
    if len(args) != 1:
        await message.answer("Использование: /unban [telegram_id]")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: /unban 123456789")
        return

    updated = await set_user_active(session, target_id, True)
    if updated:
        await message.answer(f"✅ Пользователь {target_id} разблокирован.")
    else:
        await message.answer("❌ Пользователь не найден.")
