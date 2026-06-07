import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from services.docker_service import get_containers, get_container_info, container_action
from services.services_service import get_service_status, restart_service, start_service, stop_service

router = Router()

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

def docker_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список контейнеров", callback_data="docker_list")],
        [InlineKeyboardButton(text="⚙️ Сервис Docker", callback_data="docker_service")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])

@router.message(Command("docker"))
async def cmd_docker(message: Message, user: User):
    if not is_admin_or_above(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    await message.answer("🐳 Docker контейнеры:", reply_markup=docker_menu())

@router.callback_query(F.data == "docker_main")
async def cb_docker_main(callback: CallbackQuery, user: User):
    await callback.message.edit_text("🐳 Docker контейнеры:", reply_markup=docker_menu())

@router.callback_query(F.data == "docker_list")
async def cb_docker_list(callback: CallbackQuery, user: User):
    await callback.message.edit_text("⏳ Получаю список контейнеров...")
    try:
        loop = asyncio.get_event_loop()
        containers = await loop.run_in_executor(None, get_containers)
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=back_button("docker_main"))
        return
    if not containers:
        await callback.message.edit_text("📋 Контейнеров нет.", reply_markup=back_button("docker_main"))
        return
    buttons = []
    for c in containers:
        icon = "🟢" if c["status"] == "running" else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{icon} {c['name']}", callback_data=f"docker_view_{c['name']}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="docker_main")])
    await callback.message.edit_text("📋 Контейнеры:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "docker_service")
async def cb_docker_service(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, lambda: get_service_status("docker"))
    is_active = status == "active"
    icon = "🟢" if is_active else "🔴"
    text = f"🐳 Сервис Docker\n\nСтатус: {icon} {status}"
    buttons = []
    if user.role == "owner":
        if is_active:
            buttons.append([InlineKeyboardButton(text="🔄 Перезапустить", callback_data="docker_svc_restart")])
            buttons.append([InlineKeyboardButton(text="⏹ Остановить", callback_data="docker_svc_stop")])
        else:
            buttons.append([InlineKeyboardButton(text="▶️ Запустить", callback_data="docker_svc_start")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="docker_service")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="docker_main")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "docker_svc_restart")
async def cb_docker_svc_restart(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: restart_service("docker"))
    await callback.answer("✅ Перезапущен." if result == "OK" else f"❌ {result}")
    await cb_docker_service(callback, user)

@router.callback_query(F.data == "docker_svc_stop")
async def cb_docker_svc_stop(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: stop_service("docker"))
    await callback.answer("✅ Остановлен." if result == "OK" else f"❌ {result}")
    await cb_docker_service(callback, user)

@router.callback_query(F.data == "docker_svc_start")
async def cb_docker_svc_start(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: start_service("docker"))
    await callback.answer("✅ Запущен." if result == "OK" else f"❌ {result}")
    await cb_docker_service(callback, user)

async def show_container_info(callback: CallbackQuery, user: User, name: str):
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: get_container_info(name))
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=back_button("docker_list"))
        return
    if not info:
        await callback.message.edit_text("❌ Контейнер не найден.", reply_markup=back_button("docker_list"))
        return
    icon = "🟢" if info["status"] == "running" else "🔴"
    text = f"🐳 {info['name']}\n\nСтатус: {icon} {info['status']}\nID: {info['id']}\nОбраз: {info['image']}\n"
    if info["status"] == "running":
        text += f"CPU: {info['cpu_percent']}%\nRAM: {info['mem_mb']} MB ({info['mem_percent']}%)\n"
    buttons = []
    if info["status"] == "running":
        buttons.append([InlineKeyboardButton(text="⏹ Остановить", callback_data=f"docker_stop_{name}")])
        buttons.append([InlineKeyboardButton(text="🔄 Перезапустить", callback_data=f"docker_restart_{name}")])
    else:
        buttons.append([InlineKeyboardButton(text="▶️ Запустить", callback_data=f"docker_start_{name}")])
    if user.role == "owner":
        buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"docker_remove_{name}")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"docker_view_{name}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="docker_list")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("docker_view_"))
async def cb_docker_view(callback: CallbackQuery, user: User):
    name = callback.data[len("docker_view_"):]
    await callback.message.edit_text(f"⏳ Получаю данные {name}...")
    await show_container_info(callback, user, name)

@router.callback_query(F.data.startswith("docker_stop_"))
async def cb_docker_stop(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    name = callback.data[len("docker_stop_"):]
    await callback.message.edit_text(f"⏳ Останавливаю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: container_action(name, "stop"))
    await callback.answer("✅ Остановлен." if result["success"] else f"❌ {result.get('error', '')}")
    await show_container_info(callback, user, name)

@router.callback_query(F.data.startswith("docker_start_"))
async def cb_docker_start(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    name = callback.data[len("docker_start_"):]
    await callback.message.edit_text(f"⏳ Запускаю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: container_action(name, "start"))
    await callback.answer("✅ Запущен." if result["success"] else f"❌ {result.get('error', '')}")
    await show_container_info(callback, user, name)

@router.callback_query(F.data.startswith("docker_restart_"))
async def cb_docker_restart(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    name = callback.data[len("docker_restart_"):]
    await callback.message.edit_text(f"⏳ Перезапускаю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: container_action(name, "restart"))
    await callback.answer("✅ Перезапущен." if result["success"] else f"❌ {result.get('error', '')}")
    await show_container_info(callback, user, name)

@router.callback_query(F.data.startswith("docker_remove_confirm_"))
async def cb_docker_remove_confirm(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    name = callback.data[len("docker_remove_confirm_"):]
    await callback.message.edit_text(f"⏳ Удаляю {name}...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: container_action(name, "remove"))
    if result["success"]:
        await callback.message.edit_text(f"✅ Контейнер {name} удалён.", reply_markup=back_button("docker_list"))
    else:
        await callback.message.edit_text(f"❌ Ошибка: {result.get('error', '')}", reply_markup=back_button("docker_list"))

@router.callback_query(F.data.startswith("docker_remove_"))
async def cb_docker_remove(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    name = callback.data[len("docker_remove_"):]
    buttons = [
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"docker_remove_confirm_{name}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"docker_view_{name}")],
    ]
    await callback.message.edit_text(
        f"⚠️ Удалить контейнер {name}?\n\nЭто действие необратимо!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
