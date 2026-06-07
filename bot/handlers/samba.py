import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from services.services_service import get_service_status, restart_service, start_service, stop_service

router = Router()

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

async def show_samba(callback: CallbackQuery, user: User):
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, lambda: get_service_status("smbd"))
    is_active = status == "active"
    icon = "🟢" if is_active else "🔴"

    text = (
        f"🗂 Samba\n\n"
        f"Статус: {icon} {status}\n"
        f"Шара: /home/chpk"
    )

    buttons = []
    if user.role == "owner":
        if is_active:
            buttons.append([InlineKeyboardButton(text="🔄 Перезапустить", callback_data="samba_restart")])
            buttons.append([InlineKeyboardButton(text="⏹ Остановить", callback_data="samba_stop")])
        else:
            buttons.append([InlineKeyboardButton(text="▶️ Запустить", callback_data="samba_start")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_samba")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "menu_samba")
async def cb_samba_main(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    await show_samba(callback, user)

@router.callback_query(F.data == "samba_restart")
async def cb_samba_restart(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: restart_service("smbd"))
    await callback.answer("✅ Перезапущена." if result == "OK" else f"❌ {result}")
    await show_samba(callback, user)

@router.callback_query(F.data == "samba_stop")
async def cb_samba_stop(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: stop_service("smbd"))
    await callback.answer("✅ Остановлена." if result == "OK" else f"❌ {result}")
    await show_samba(callback, user)

@router.callback_query(F.data == "samba_start")
async def cb_samba_start(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: start_service("smbd"))
    await callback.answer("✅ Запущена." if result == "OK" else f"❌ {result}")
    await show_samba(callback, user)
