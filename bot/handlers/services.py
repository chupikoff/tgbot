import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from services.services_service import get_all_statuses, restart_service, start_service, stop_service, SERVICES, SERVICE_NAMES

router = Router()

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

def is_owner(user: User) -> bool:
    return user.role == "owner"

def services_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Статус всех сервисов", callback_data="services_all")],
        *[[InlineKeyboardButton(
            text=f"⚙️ {SERVICE_NAMES.get(s, s)}",
            callback_data=f"service_view_{s}"
        )] for s in SERVICES],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

@router.message(Command("services"))
async def cmd_services(message: Message, user: User):
    if not is_admin_or_above(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    await message.answer("⚙️ Управление сервисами:", reply_markup=services_menu())

@router.callback_query(F.data == "services_main")
async def cb_services_main(callback: CallbackQuery, user: User):
    await callback.message.edit_text("⚙️ Управление сервисами:", reply_markup=services_menu())

@router.callback_query(F.data == "services_all")
async def cb_services_all(callback: CallbackQuery, user: User):
    await callback.message.edit_text("⏳ Получаю статусы...")
    loop = asyncio.get_event_loop()
    statuses = await loop.run_in_executor(None, get_all_statuses)

    text = "📋 Статус сервисов:\n\n"
    for s in statuses:
        icon = "🟢" if s["is_active"] else "🔴"
        text += f"{icon} {s['name']}: {s['status']}\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_button("services_main")
    )

@router.callback_query(F.data.startswith("service_view_"))
async def cb_service_view(callback: CallbackQuery, user: User):
    service = callback.data.replace("service_view_", "")
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, lambda: __import__('services.services_service', fromlist=['get_service_status']).get_service_status(service))

    is_active = status == "active"
    icon = "🟢" if is_active else "🔴"
    name = SERVICE_NAMES.get(service, service)

    text = f"{icon} {name}\nСтатус: {status}"

    buttons = []
    if is_owner(user):
        if is_active:
            buttons.append([
                InlineKeyboardButton(text="🔄 Перезапустить", callback_data=f"service_restart_{service}"),
                InlineKeyboardButton(text="⏹ Остановить", callback_data=f"service_stop_{service}"),
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="▶️ Запустить", callback_data=f"service_start_{service}"),
            ])

    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"service_view_{service}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="services_main")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("service_restart_"))
async def cb_service_restart(callback: CallbackQuery, user: User):
    if not is_owner(user):
        await callback.answer("⛔ Только для владельца.")
        return
    service = callback.data.replace("service_restart_", "")
    name = SERVICE_NAMES.get(service, service)
    await callback.message.edit_text(f"⏳ Перезапускаю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: restart_service(service))
    if result == "OK":
        await callback.message.edit_text(
            f"✅ {name} перезапущен.",
            reply_markup=back_button(f"service_view_{service}")
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка: {result}",
            reply_markup=back_button(f"service_view_{service}")
        )

@router.callback_query(F.data.startswith("service_stop_"))
async def cb_service_stop(callback: CallbackQuery, user: User):
    if not is_owner(user):
        await callback.answer("⛔ Только для владельца.")
        return
    service = callback.data.replace("service_stop_", "")
    name = SERVICE_NAMES.get(service, service)
    await callback.message.edit_text(f"⏳ Останавливаю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: stop_service(service))
    if result == "OK":
        await callback.message.edit_text(
            f"✅ {name} остановлен.",
            reply_markup=back_button(f"service_view_{service}")
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка: {result}",
            reply_markup=back_button(f"service_view_{service}")
        )

@router.callback_query(F.data.startswith("service_start_"))
async def cb_service_start(callback: CallbackQuery, user: User):
    if not is_owner(user):
        await callback.answer("⛔ Только для владельца.")
        return
    service = callback.data.replace("service_start_", "")
    name = SERVICE_NAMES.get(service, service)
    await callback.message.edit_text(f"⏳ Запускаю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: start_service(service))
    if result == "OK":
        await callback.message.edit_text(
            f"✅ {name} запущен.",
            reply_markup=back_button(f"service_view_{service}")
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка: {result}",
            reply_markup=back_button(f"service_view_{service}")
        )
