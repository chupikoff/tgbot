from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from filters.roles import has_role
from services.user_service import get_all_users, get_user, set_role, set_active

router = Router()

ROLE_NAMES = {
    "guest": "👣 Гость",
    "user": "👤 Пользователь",
    "admin": "🔧 Админ",
    "owner": "👑 Владелец",
}


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_users")
async def cb_users(callback: CallbackQuery, session: AsyncSession):
    users = await get_all_users(session)
    if not users:
        await callback.message.edit_text("👥 Пользователей нет.", reply_markup=back_button("menu_main"))
        return
    buttons = []
    for u in users:
        status = "✅" if u.is_active else "❌"
        role = ROLE_NAMES.get(u.role, u.role)
        username = f"@{u.username}" if u.username else "без username"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {u.full_name} ({username}) — {role}",
            callback_data=f"user_manage_{u.telegram_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])
    await callback.message.edit_text("👥 Пользователи:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("user_manage_"))
async def cb_user_manage(callback: CallbackQuery, user: User, session: AsyncSession):
    target_id = int(callback.data.replace("user_manage_", ""))
    target = await get_user(session, target_id)
    if not target:
        await callback.answer("❌ Пользователь не найден.")
        return

    username = f"@{target.username}" if target.username else "без username"
    role = ROLE_NAMES.get(target.role, target.role)
    status = "✅ Активен" if target.is_active else "❌ Заблокирован"
    text = f"👤 {target.full_name} ({username})\nРоль: {role}\nСтатус: {status}"

    buttons = []

    # Кнопки ролей
    if user.role == "owner":
        available_roles = ["guest", "user", "admin"]
    else:
        available_roles = ["guest", "user"]

    role_buttons = []
    for r in available_roles:
        if r != target.role:
            role_buttons.append(InlineKeyboardButton(
                text=ROLE_NAMES[r],
                callback_data=f"user_role_{target_id}_{r}"
            ))
    if role_buttons:
        buttons.append(role_buttons)

    # Кнопка блокировки
    if target.role != "owner":
        if target.is_active:
            buttons.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"user_ban_{target_id}")])
        else:
            buttons.append([InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"user_unban_{target_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_users")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("user_role_"))
async def cb_user_role(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("user_role_", "").split("_")
    target_id = int(parts[0])
    new_role = parts[1]
    target = await get_user(session, target_id)
    if not target:
        await callback.answer("❌ Пользователь не найден.")
        return
    success = await set_role(session, target, new_role, user)
    if success:
        await callback.answer(f"✅ Роль изменена на {ROLE_NAMES.get(new_role, new_role)}")
    else:
        await callback.answer("⛔ Недостаточно прав.")
    callback.data = f"user_manage_{target_id}"
    await cb_user_manage(callback, user, session)


@router.callback_query(F.data.startswith("user_ban_"))
async def cb_user_ban(callback: CallbackQuery, user: User, session: AsyncSession):
    target_id = int(callback.data.replace("user_ban_", ""))
    target = await get_user(session, target_id)
    success = await set_active(session, target, False, user)
    if success:
        await callback.answer("✅ Пользователь заблокирован.")
    else:
        await callback.answer("⛔ Недостаточно прав.")
    callback.data = f"user_manage_{target_id}"
    await cb_user_manage(callback, user, session)


@router.callback_query(F.data.startswith("user_unban_"))
async def cb_user_unban(callback: CallbackQuery, user: User, session: AsyncSession):
    target_id = int(callback.data.replace("user_unban_", ""))
    target = await get_user(session, target_id)
    success = await set_active(session, target, True, user)
    if success:
        await callback.answer("✅ Пользователь разблокирован.")
    else:
        await callback.answer("⛔ Недостаточно прав.")
    callback.data = f"user_manage_{target_id}"
    await cb_user_manage(callback, user, session)
