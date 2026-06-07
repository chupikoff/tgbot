from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

router = Router()

class AdminStates(StatesGroup):
    sending_message = State()

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
        buttons.append([InlineKeyboardButton(text="🧟 Выжить", callback_data="menu_zs")])
    if user.role in ["admin", "owner"]:
        buttons.append([InlineKeyboardButton(text="🖥 Состояние сервера", callback_data="menu_status")])
        buttons.append([InlineKeyboardButton(text="🐳 Docker", callback_data="menu_docker")])
        buttons.append([InlineKeyboardButton(text="🌊 Торренты", callback_data="menu_torrents")])
        buttons.append([InlineKeyboardButton(text="📺 MiniDLNA", callback_data="menu_minidlna")])
        buttons.append([InlineKeyboardButton(text="🗂 Samba", callback_data="menu_samba")])
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

def users_menu(user: User) -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_list")])
    if user.role == "owner":
        buttons.append([InlineKeyboardButton(text="🎭 Управление ролями", callback_data="users_roles")])
    buttons.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data="users_ban_list")])
    buttons.append([InlineKeyboardButton(text="✅ Разблокировать", callback_data="users_unban_list")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

def status_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_status")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

@router.callback_query(F.data == "menu_status")
async def cb_menu_status(callback: CallbackQuery, user: User):
    from services.monitoring import format_status_message
    status = format_status_message()
    try:
        await callback.message.edit_text(status, reply_markup=status_menu())
    except Exception:
        await callback.message.answer(status, reply_markup=status_menu())

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

@router.callback_query(F.data == "menu_samba")
async def cb_menu_samba(callback: CallbackQuery, user: User):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    from handlers.samba import show_samba
    await show_samba(callback, user)

@router.callback_query(F.data == "menu_minidlna")
async def cb_menu_minidlna(callback: CallbackQuery, user: User):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    from handlers.minidlna import show_minidlna
    await show_minidlna(callback, user)

@router.callback_query(F.data == "menu_zs")
async def cb_menu_zs(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    from services.zs_service import get_player, get_base
    from handlers.zs_game import format_status, main_menu, ZSStates
    player = await get_player(session, user.telegram_id)
    if not player:
        await callback.message.edit_text(
            "🧟 Добро пожаловать в зону заражения!\n\n"
            "Учёные из Великой Крокожии работают над вакциной.\n"
            "Твоя задача — выжить 30 дней.\n\n"
            "Введи имя своего персонажа:"
        )
        await state.set_state(ZSStates.entering_name)
        return
    if not player.is_alive:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await callback.message.edit_text(
            "💀 Твой персонаж погиб.\n\nХочешь начать заново?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Начать заново", callback_data="zs_restart")]
            ])
        )
        return
    base = await get_base(session, user.telegram_id)
    text = format_status(player)
    try:
        await callback.message.edit_text(text, reply_markup=main_menu(player, base))
    except Exception:
        await callback.message.answer(text, reply_markup=main_menu(player, base))

@router.callback_query(F.data == "menu_users")
async def cb_menu_users(callback: CallbackQuery, user: User):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    await callback.message.edit_text("👥 Управление пользователями:", reply_markup=users_menu(user))

@router.callback_query(F.data == "users_list")
async def cb_users_list(callback: CallbackQuery, user: User, session: AsyncSession):
    from services.user_service import get_all_users
    users = await get_all_users(session)
    if not users:
        await callback.message.edit_text("Пользователей пока нет.", reply_markup=back_button("menu_users"))
        return
    text = "👥 Список пользователей:\n\n"
    for u in users:
        status = "✅" if u.is_active else "❌"
        username = f"@{u.username}" if u.username else "не указан"
        role_name = ROLE_NAMES.get(u.role, u.role)
        text += f"{status} {u.full_name} ({username})\n"
        text += f"   ID: {u.telegram_id} | Роль: {role_name}\n\n"
    await callback.message.edit_text(text, reply_markup=back_button("menu_users"))

@router.callback_query(F.data == "users_roles")
async def cb_users_roles(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    from services.user_service import get_all_users
    users = await get_all_users(session)
    non_owner = [u for u in users if u.role != "owner"]
    if not non_owner:
        await callback.message.edit_text("Нет пользователей для управления.", reply_markup=back_button("menu_users"))
        return
    buttons = []
    for u in non_owner:
        username = f"@{u.username}" if u.username else "без username"
        role_name = ROLE_NAMES.get(u.role, u.role)
        status = "✅" if u.is_active else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {u.full_name} ({username}) — {role_name}",
            callback_data=f"user_manage_{u.telegram_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")])
    await callback.message.edit_text(
        "🎭 Выбери пользователя для управления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("user_manage_"))
async def cb_user_manage(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    target_id = int(callback.data.replace("user_manage_", ""))
    from services.user_service import get_user
    target = await get_user(session, target_id)
    if not target:
        await callback.answer("❌ Пользователь не найден.")
        return
    username = f"@{target.username}" if target.username else "без username"
    role_name = ROLE_NAMES.get(target.role, target.role)
    status = "✅ Активен" if target.is_active else "❌ Заблокирован"
    text = (
        f"👤 {target.full_name} ({username})\n"
        f"🆔 ID: {target.telegram_id}\n"
        f"🎭 Роль: {role_name}\n"
        f"Статус: {status}"
    )
    buttons = []
    for role_key, role_label in [("admin", "🔧 Админ"), ("user", "👤 Юзер"), ("guest", "👣 Гость")]:
        if target.role != role_key:
            buttons.append([InlineKeyboardButton(
                text=f"Назначить {role_label}",
                callback_data=f"user_setrole_{target_id}_{role_key}"
            )])
    buttons.append([InlineKeyboardButton(text="✉️ Написать сообщение", callback_data=f"user_message_{target_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="users_roles")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("user_setrole_"))
async def cb_user_setrole(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    parts = callback.data.replace("user_setrole_", "").split("_")
    target_id = int(parts[0])
    role = parts[1]
    from services.user_service import set_user_role
    updated = await set_user_role(session, target_id, role)
    if updated:
        role_name = ROLE_NAMES.get(role, role)
        await callback.answer(f"✅ Роль изменена на {role_name}")
    else:
        await callback.answer("❌ Пользователь не найден.")
    await cb_users_roles(callback, user, session)

@router.callback_query(F.data.startswith("user_message_"))
async def cb_user_message(callback: CallbackQuery, user: User, state: FSMContext):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    target_id = int(callback.data.replace("user_message_", ""))
    await state.update_data(target_id=target_id)
    await state.set_state(AdminStates.sending_message)
    await callback.message.edit_text(
        "✉️ Введи сообщение для отправки пользователю:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_users")]
        ])
    )

@router.message(AdminStates.sending_message)
async def process_send_message(message: Message, state: FSMContext, user: User):
    from aiogram import Bot
    data = await state.get_data()
    target_id = data.get("target_id")
    await state.clear()
    bot: Bot = message.bot
    try:
        await bot.send_message(
            target_id,
            f"✉️ Сообщение от администратора:\n\n{message.text}"
        )
        await message.answer("✅ Сообщение отправлено!", reply_markup=back_button("menu_users"))
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {str(e)}", reply_markup=back_button("menu_users"))

@router.callback_query(F.data == "users_ban_list")
async def cb_users_ban_list(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    from services.user_service import get_all_users
    users = await get_all_users(session)
    active_users = [u for u in users if u.is_active and u.role != "owner"]
    if user.role == "admin":
        active_users = [u for u in active_users if u.role not in ["admin", "owner"]]
    if not active_users:
        await callback.message.edit_text("Нет пользователей для блокировки.", reply_markup=back_button("menu_users"))
        return
    buttons = []
    for u in active_users:
        username = f"@{u.username}" if u.username else "без username"
        role_name = ROLE_NAMES.get(u.role, u.role)
        buttons.append([InlineKeyboardButton(
            text=f"{u.full_name} ({username}) — {role_name}",
            callback_data=f"user_ban_{u.telegram_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")])
    await callback.message.edit_text(
        "🚫 Выбери пользователя для блокировки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("user_ban_"))
async def cb_user_ban(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    target_id = int(callback.data.replace("user_ban_", ""))
    from services.user_service import get_user, set_user_active
    target = await get_user(session, target_id)
    if not target:
        await callback.answer("❌ Пользователь не найден.")
        return
    if target.role == "owner":
        await callback.answer("⛔ Нельзя заблокировать владельца.")
        return
    if target.role == "admin" and user.role != "owner":
        await callback.answer("⛔ Нельзя заблокировать администратора.")
        return
    await set_user_active(session, target_id, False)
    await callback.answer(f"✅ {target.full_name} заблокирован.")
    await cb_users_ban_list(callback, user, session)

@router.callback_query(F.data == "users_unban_list")
async def cb_users_unban_list(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    from services.user_service import get_all_users
    users = await get_all_users(session)
    blocked_users = [u for u in users if not u.is_active]
    if not blocked_users:
        await callback.message.edit_text("Нет заблокированных пользователей.", reply_markup=back_button("menu_users"))
        return
    buttons = []
    for u in blocked_users:
        username = f"@{u.username}" if u.username else "без username"
        role_name = ROLE_NAMES.get(u.role, u.role)
        buttons.append([InlineKeyboardButton(
            text=f"{u.full_name} ({username}) — {role_name}",
            callback_data=f"user_unban_{u.telegram_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")])
    await callback.message.edit_text(
        "✅ Выбери пользователя для разблокировки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("user_unban_"))
async def cb_user_unban(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Недостаточно прав.")
        return
    target_id = int(callback.data.replace("user_unban_", ""))
    from services.user_service import set_user_active, get_user
    target = await get_user(session, target_id)
    if not target:
        await callback.answer("❌ Пользователь не найден.")
        return
    await set_user_active(session, target_id, True)
    await callback.answer(f"✅ {target.full_name} разблокирован.")
    await cb_users_unban_list(callback, user, session)
