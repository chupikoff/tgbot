import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from services.docker_service import get_containers, get_container_info

router = Router()

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

def docker_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список контейнеров", callback_data="docker_list")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
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
        await callback.message.edit_text(
            f"❌ Ошибка подключения к Docker.\n{str(e)}",
            reply_markup=back_button("docker_main")
        )
        return

    if not containers:
        await callback.message.edit_text(
            "📋 Контейнеров нет.",
            reply_markup=back_button("docker_main")
        )
        return

    buttons = []
    for c in containers:
        icon = "🟢" if c["status"] == "running" else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {c['name']}",
            callback_data=f"docker_view_{c['name']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="docker_main")])

    await callback.message.edit_text(
        "📋 Контейнеры:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("docker_view_"))
async def cb_docker_view(callback: CallbackQuery, user: User):
    container_name = callback.data.replace("docker_view_", "")
    await callback.message.edit_text(f"⏳ Получаю данные {container_name}...")

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: get_container_info(container_name))
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=back_button("docker_list")
        )
        return

    if not info:
        await callback.message.edit_text(
            "❌ Контейнер не найден.",
            reply_markup=back_button("docker_list")
        )
        return

    icon = "🟢" if info["status"] == "running" else "🔴"
    text = (
        f"🐳 {info['name']}\n\n"
        f"Статус: {icon} {info['status']}\n"
        f"ID: {info['id']}\n"
        f"Образ: {info['image']}\n"
    )

    if info["status"] == "running":
        text += (
            f"CPU: {info['cpu_percent']}%\n"
            f"RAM: {info['mem_mb']} MB ({info['mem_percent']}%)\n"
        )

    buttons = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"docker_view_{container_name}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="docker_list")],
    ]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
