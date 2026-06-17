import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters.roles import has_role
from services.docker_service import get_containers, get_container_info, container_action

router = Router()


class DockerStates(StatesGroup):
    confirm_remove = State()


def docker_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список контейнеров", callback_data="docker_list")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_docker")
async def cb_docker(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🐳 Docker:", reply_markup=docker_menu())
    except Exception:
        await callback.message.answer("🐳 Docker:", reply_markup=docker_menu())


@router.callback_query(F.data == "docker_list")
async def cb_docker_list(callback: CallbackQuery):
    try:
        loop = asyncio.get_event_loop()
        containers = await loop.run_in_executor(None, get_containers)
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка Docker: {e}", reply_markup=back_button("menu_docker"))
        return
    if not containers:
        await callback.message.edit_text("📋 Контейнеров нет.", reply_markup=back_button("menu_docker"))
        return
    buttons = []
    for c in containers:
        icon = "🟢" if c["status"] == "running" else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {c['name']}",
            callback_data=f"docker_view_{c['name']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="docker_list")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_docker")])
    await callback.message.edit_text("📋 Контейнеры:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("docker_view_"))
async def cb_docker_view(callback: CallbackQuery):
    name = callback.data.replace("docker_view_", "")
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: get_container_info(name))
    if not info:
        await callback.answer("❌ Контейнер не найден.")
        return
    icon = "🟢" if info["status"] == "running" else "🔴"
    text = (
        f"🐳 {info['name']}\n\n"
        f"Статус: {icon} {info['status']}\n"
        f"Образ: {info['image']}\n"
    )
    if info["status"] == "running":
        text += f"CPU: {info['cpu_percent']}%\nRAM: {info['mem_mb']} MB ({info['mem_percent']}%)"
    buttons = []
    if info["status"] == "running":
        buttons.append([InlineKeyboardButton(text="⏹ Стоп", callback_data=f"docker_stop_{name}")])
        buttons.append([InlineKeyboardButton(text="🔄 Рестарт", callback_data=f"docker_restart_{name}")])
    else:
        buttons.append([InlineKeyboardButton(text="▶️ Старт", callback_data=f"docker_start_{name}")])
    buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"docker_confirm_remove_{name}")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"docker_view_{name}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="docker_list")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("docker_stop_"))
async def cb_docker_stop(callback: CallbackQuery):
    name = callback.data.replace("docker_stop_", "")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: container_action(name, "stop"))
    await callback.answer("⏹ Остановлен.")
    callback.data = f"docker_view_{name}"
    await cb_docker_view(callback)


@router.callback_query(F.data.startswith("docker_start_"))
async def cb_docker_start(callback: CallbackQuery):
    name = callback.data.replace("docker_start_", "")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: container_action(name, "start"))
    await callback.answer("▶️ Запущен.")
    callback.data = f"docker_view_{name}"
    await cb_docker_view(callback)


@router.callback_query(F.data.startswith("docker_restart_"))
async def cb_docker_restart(callback: CallbackQuery):
    name = callback.data.replace("docker_restart_", "")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: container_action(name, "restart"))
    await callback.answer("🔄 Перезапущен.")
    callback.data = f"docker_view_{name}"
    await cb_docker_view(callback)


@router.callback_query(F.data.startswith("docker_confirm_remove_"))
async def cb_docker_confirm_remove(callback: CallbackQuery):
    name = callback.data.replace("docker_confirm_remove_", "")
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"docker_remove_{name}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"docker_view_{name}"),
        ]
    ])
    await callback.message.edit_text(f"⚠️ Удалить контейнер {name}?", reply_markup=buttons)


@router.callback_query(F.data.startswith("docker_remove_"))
async def cb_docker_remove(callback: CallbackQuery):
    name = callback.data.replace("docker_remove_", "")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: container_action(name, "remove"))
    await callback.message.edit_text(f"🗑 Контейнер {name} удалён.", reply_markup=back_button("docker_list"))
