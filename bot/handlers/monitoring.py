import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from filters.roles import has_role
from services.monitoring_service import get_status, format_status
from services.services_service import get_all_statuses, restart_service, start_service, stop_service, SERVICES

router = Router()


def monitoring_menu(statuses: list) -> InlineKeyboardMarkup:
    buttons = []
    for s in statuses:
        icon = "🟢" if s["is_active"] else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {s['name']}",
            callback_data=f"svc_{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_monitoring")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def service_menu(service_id: str, is_active: bool, user: User) -> InlineKeyboardMarkup:
    buttons = []
    if is_active:
        buttons.append([InlineKeyboardButton(text="🔄 Рестарт", callback_data=f"svc_restart_{service_id}")])
        buttons.append([InlineKeyboardButton(text="⏹ Стоп", callback_data=f"svc_stop_{service_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="▶️ Старт", callback_data=f"svc_start_{service_id}")])

    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"svc_{service_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_monitoring")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "menu_monitoring")
async def cb_monitoring(callback: CallbackQuery):
    loop = asyncio.get_event_loop()
    status_data = await loop.run_in_executor(None, get_status)
    statuses = await loop.run_in_executor(None, get_all_statuses)
    text = f"📊 Мониторинг\n\n{format_status(status_data)}"
    try:
        await callback.message.edit_text(text, reply_markup=monitoring_menu(statuses))
    except Exception:
        await callback.message.answer(text, reply_markup=monitoring_menu(statuses))


@router.callback_query(F.data.startswith("svc_") & ~F.data.startswith("svc_restart_") & ~F.data.startswith("svc_stop_") & ~F.data.startswith("svc_start_") & ~F.data.startswith("svc_rescan_"))
async def cb_service(callback: CallbackQuery):
    service_id = callback.data.replace("svc_", "")
    if service_id not in SERVICES:
        await callback.answer("❌ Сервис не найден.")
        return
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, lambda: __import__('services.services_service', fromlist=['get_status']).get_status(service_id))
    is_active = status == "active"
    icon = "🟢" if is_active else "🔴"
    name = SERVICES[service_id]
    text = f"{name}\n\nСтатус: {icon} {status}"
    try:
        await callback.message.edit_text(text, reply_markup=service_menu(service_id, is_active, callback.from_user))
    except Exception:
        await callback.message.answer(text, reply_markup=service_menu(service_id, is_active, callback.from_user))


@router.callback_query(F.data.startswith("svc_restart_"))
async def cb_svc_restart(callback: CallbackQuery):
    service_id = callback.data.replace("svc_restart_", "")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: restart_service(service_id))
    await callback.answer("✅ Перезапущен." if result == "active" or result == "OK" else f"❌ {result}")
    callback.data = f"svc_{service_id}"
    await cb_service(callback)


@router.callback_query(F.data.startswith("svc_stop_"))
async def cb_svc_stop(callback: CallbackQuery):
    service_id = callback.data.replace("svc_stop_", "")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: stop_service(service_id))
    await callback.answer("✅ Остановлен." if result == "OK" else f"❌ {result}")
    callback.data = f"svc_{service_id}"
    await cb_service(callback)


@router.callback_query(F.data.startswith("svc_start_"))
async def cb_svc_start(callback: CallbackQuery):
    service_id = callback.data.replace("svc_start_", "")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: start_service(service_id))
    await callback.answer("✅ Запущен." if result == "OK" else f"❌ {result}")
    callback.data = f"svc_{service_id}"
    await cb_service(callback)


@router.callback_query(F.data == "svc_rescan_minidlna")
async def cb_rescan_minidlna(callback: CallbackQuery):
    import subprocess
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: subprocess.run(
            ["sudo", "systemctl", "kill", "-s", "SIGHUP", "minidlna"], timeout=5
        ))
        await callback.answer("✅ Пересканирование запущено.")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")
